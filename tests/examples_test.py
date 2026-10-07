"""Keep every script in examples/ runnable.

Each example is run in two ways:
- as a script (``python examples/xxx.py``) from another directory, the way
  users run it, so the import of idl_parser from the checkout is covered;
- in-process through its ``main()``, checking key lines of the output.

Any new ``examples/*.py`` file is picked up by ``ExamplesRunAsScriptTest``
automatically.
"""
import contextlib
import glob
import importlib.util
import io
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXAMPLES_DIR = os.path.join(ROOT, 'examples')


def example_scripts():
    return sorted(p for p in glob.glob(os.path.join(EXAMPLES_DIR, '*.py'))
                  if not os.path.basename(p).startswith('_'))


def load_example(name):
    path = os.path.join(EXAMPLES_DIR, name + '.py')
    sys.path.insert(0, EXAMPLES_DIR)  # examples import their helper module "_path"
    try:
        spec = importlib.util.spec_from_file_location('examples_' + name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(EXAMPLES_DIR)
    return module


def run_main(name):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        load_example(name).main()
    return out.getvalue()


class ExamplesRunAsScriptTest(unittest.TestCase):

    def test_examples_exist(self):
        names = [os.path.basename(p) for p in example_scripts()]
        for name in ('example.py', 'union_example.py', 'annotation_example.py'):
            self.assertIn(name, names)

    def test_each_example_runs_as_script(self):
        env = dict(os.environ)
        env.pop('PYTHONPATH', None)  # must work without setting PYTHONPATH
        with tempfile.TemporaryDirectory() as cwd:  # not the repository root
            for path in example_scripts():
                with self.subTest(os.path.basename(path)):
                    result = subprocess.run([sys.executable, path], cwd=cwd, env=env,
                                            capture_output=True, text=True, timeout=60)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertTrue(result.stdout.strip(), 'no output')
                    self.assertNotIn('Traceback', result.stderr)


class ExampleTest(unittest.TestCase):

    def test_output(self):
        text = run_main('example')
        self.assertIn('DataGetter interface', text)
        self.assertIn('  name: getData', text)
        self.assertIn('    direction: out', text)
        self.assertRegex(text, r'typedef sequence ?< ?double ?> DoubleSeq')
        self.assertIn('descriminator kind: UNION_DESCRIMINATOR_KIND', text)
        self.assertIn('TimedDoubleSeq', text)


class UnionExampleTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.text = run_main('union_example')

    def test_lists_unions(self):
        self.assertIn("unions in module shapes: ['Shape', 'Value', 'OptionalDouble']", self.text)

    def test_discriminator_kinds(self):
        self.assertIn('union shapes::Shape switch (ShapeKind)', self.text)
        self.assertIn('union shapes::Value switch (long)', self.text)
        self.assertIn('union shapes::OptionalDouble switch (boolean)', self.text)

    def test_member_types(self):
        self.assertIn('case CIRCLE -> radius: primitive double', self.text)
        self.assertIn('case RECTANGLE -> rect: struct shapes::Rectangle (members: top_left, width, height)',
                      self.text)
        self.assertIn('case POLYGON -> vertices: typedef shapes::PointSeq = sequence of Point2D', self.text)
        self.assertIn('case 2 -> matrix: array double', self.text)

    def test_multiple_labels(self):
        self.assertIn('case -1, 0 -> error_message: primitive string', self.text)
        self.assertIn('Value with discriminator -1 holds: error_message', self.text)
        self.assertIn('Value with discriminator 1 holds: integer_value', self.text)

    def test_lookup_and_nesting(self):
        self.assertIn('Shape.rect full path: shapes::Shape::rect', self.text)
        self.assertIn('Shape.rect.top_left type: shapes::Point2D', self.text)
        self.assertIn("ShapeKind values: ['CIRCLE', 'RECTANGLE', 'POLYGON', 'POINT']", self.text)
        self.assertIn('ShapeMessage.shape: union shapes::Shape', self.text)

    def test_to_dic(self):
        self.assertIn('"descriminator_kind": "boolean"', self.text)


class AnnotationExampleTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.text = run_main('annotation_example')

    def assertLine(self, *parts):
        """Some line contains all parts (column padding varies)."""
        for line in self.text.splitlines():
            if all(p in line for p in parts):
                return
        self.fail('no line with %r in output:\n%s' % (parts, self.text))

    def test_definitions(self):
        self.assertLine('module robot', '@unit_system(name="SI")')
        self.assertLine('struct JointState', '@extensibility(APPENDABLE) @topic')
        self.assertLine('union Setpoint', '@extensibility(FINAL)')
        self.assertLine('typedef Percent', '@range(min=0, max=100)')
        self.assertLine('const MAX_JOINTS', '@verbatim(language="c++", text="constexpr")')
        self.assertLine('interface Controller', '@service(platform="DDS")')

    def test_members_values_and_arguments(self):
        # annotations do not leak into the type name
        self.assertLine('  long joint_id', '@key')
        self.assertLine('  double position', '@range(min=-180, max=180) @unit("deg")')
        self.assertLine('  long sequence_number', '(none)')
        self.assertLine('enum value ERROR', '@value(99) @deprecated')
        self.assertLine('case IDLE: hold_position', '@unit("deg")')
        self.assertLine('method setMode', '@oneway_hint')
        self.assertLine('arg joint_id', '@range(min=0, max=6)')

    def test_arguments(self):
        self.assertIn("params:  {'min': '-180', 'max': '180'}", self.text)
        self.assertIn('min/max: -180 180', self.text)
        self.assertIn('unit without quotes: deg', self.text)
        self.assertIn('IDLE value: 10', self.text)
        self.assertIn('ERROR deprecated? True', self.text)
        self.assertIn('effort optional? True', self.text)
        self.assertIn('sequence_number annotation: None', self.text)

    def test_keys(self):
        self.assertIn("JointState keys: ['joint_id', 'robot_name']", self.text)
        self.assertIn("Command keys: ['target_id', 'command_id']", self.text)

    def test_bitmask(self):
        self.assertIn('Status bit_bound: 8', self.text)
        self.assertIn("('FAULT', 7)", self.text)

    def test_to_dic(self):
        self.assertIn('"name": "extensibility"', self.text)
        self.assertIn('"APPENDABLE"', self.text)


if __name__ == '__main__':
    unittest.main()
