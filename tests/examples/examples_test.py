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
from tests import support

ROOT = support.ROOT
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
    """Category: Examples / カテゴリ: サンプル(examples)

    Every script in examples/ runs the way users run it.
    examples/ の各スクリプトがユーザーと同じ方法で実行できる。
    """

    def test_examples_exist(self):
        """The fifteen example scripts exist in examples/.

        examples/ に15個のサンプルスクリプトが存在する。
        """
        names = [os.path.basename(p) for p in example_scripts()]
        for name in ('example.py', 'argument_direction_example.py', 'struct_example.py',
                     'enum_example.py', 'enum_value_example.py', 'union_example.py',
                     'annotation_example.py', 'scoped_name_example.py',
                     'valuetype_example.py', 'include_dirs_example.py',
                     'struct_inheritance_map_example.py', 'any_fixed_example.py',
                     'preprocessor_example.py', 'typedef_template_module_example.py',
                     'conditional_include_example.py'):
            self.assertIn(name, names)

    def test_each_example_runs_as_script(self):
        """Each example runs as a script from another directory without PYTHONPATH and exits normally.

        各サンプルを別ディレクトリから PYTHONPATH なしで実行して正常終了する。
        """
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
    """Category: Examples / カテゴリ: サンプル(examples)

    Output of examples/example.py.
    examples/example.py の出力。
    """

    def test_output(self):
        """The output of example.py lists the interface and its methods.

        example.py の出力に interface とそのメソッドが含まれる。
        """
        text = run_main('example')
        self.assertIn('interface my_module::Calculator', text)
        self.assertIn('  long add(in long a, in long b)', text)
        self.assertIn('  void reset()', text)
        self.assertIn('  boolean divide(in double a, in double b, out double result)', text)


class ArgumentDirectionExampleTest(unittest.TestCase):
    """Category: Examples / カテゴリ: サンプル(examples)

    Output of examples/argument_direction_example.py.
    examples/argument_direction_example.py の出力。
    """

    @classmethod
    def setUpClass(cls):
        cls.text = run_main('argument_direction_example')

    def test_directions(self):
        """argument_direction_example: the direction (in / out / inout) of each argument.

        argument_direction_example: 各引数の方向(in/out/inout)が出力される。
        """
        for line in ('set value in long', 'get value out long', 'increment value inout long',
                     'divide quotient out double', 'divide count inout long'):
            self.assertIn(line.split(), [l.split() for l in self.text.splitlines()])

    def test_sends_and_receives(self):
        """argument_direction_example: what the caller sends and receives, and the signatures.

        argument_direction_example: 呼び出し側が渡す値・受け取る値とシグネチャ。
        """
        self.assertRegex(self.text, r'divide +sends: a, b, count +receives: \(return boolean\), quotient, count')
        self.assertIn('  set(value)', self.text)
        self.assertIn('  value = get()', self.text)
        self.assertIn('  value = increment(value)', self.text)
        self.assertIn('  result, quotient, count = divide(a, b, count)', self.text)


class StructExampleTest(unittest.TestCase):
    """Category: Examples / カテゴリ: サンプル(examples)

    Output of examples/struct_example.py.
    examples/struct_example.py の出力。
    """

    def test_output(self):
        """struct_example: structs and member types (primitive, struct, array, sequence).

        struct_example: struct 一覧とメンバー型(プリミティブ/struct/array/sequence)。
        """
        text = run_main('struct_example')
        self.assertIn("structs in my_module: ['Time', 'Pose', 'Odometry']", text)
        self.assertIn('struct my_module::Odometry', text)
        self.assertRegex(text, r'stamp +struct my_module::Time')
        self.assertRegex(text, r'frame_id +string')
        self.assertRegex(text, r'position +array double')
        self.assertRegex(text, r'covariance +sequence of double')
        self.assertIn("Odometry.stamp members: [('sec', 'long'), ('nsec', 'long')]", text)


class StructInheritanceMapExampleTest(unittest.TestCase):
    """Category: Examples / カテゴリ: サンプル(examples)

    Output of examples/struct_inheritance_map_example.py (issue #118).
    examples/struct_inheritance_map_example.py の出力(#118)。
    """

    @classmethod
    def setUpClass(cls):
        cls.text = run_main('struct_inheritance_map_example')

    def test_inheritance(self):
        """struct_inheritance_map_example: base structs, own and inherited members.

        struct_inheritance_map_example: 基底 struct、自身のメンバーと継承したメンバー。
        """
        self.assertIn('struct robot::JointState (base: robot::Header)', self.text)
        self.assertIn("  all members: ['frame_id', 'stamp', 'joints', 'max_effort']", self.text)
        self.assertIn('LimitedJointState inherits: Header -> JointState -> LimitedJointState', self.text)
        self.assertIn("keys of LimitedJointState: ['frame_id']", self.text)

    def test_maps(self):
        """struct_inheritance_map_example: key and value types and bounds of maps.

        struct_inheritance_map_example: map のキー・値の型と上限。
        """
        self.assertRegex(self.text, r'joints +map from string to struct robot::Joint')
        self.assertRegex(self.text, r'max_effort +map from string to double \(at most 16 entries\)')
        self.assertIn('typedef IdNames: map from long to string', self.text)

    def test_to_dic(self):
        """struct_inheritance_map_example: to_dic() has the base and the map type.

        struct_inheritance_map_example: to_dic() に基底と map 型が出る。
        """
        self.assertIn("'base': 'robot::JointState'", self.text)
        self.assertIn("'type': 'map<string, double>'", self.text)


class AnyFixedExampleTest(unittest.TestCase):
    """Category: Examples / カテゴリ: サンプル(examples)

    Output of examples/any_fixed_example.py (issue #119).
    examples/any_fixed_example.py の出力(#119)。
    """

    @classmethod
    def setUpClass(cls):
        cls.text = run_main('any_fixed_example')

    def test_members(self):
        """any_fixed_example: any, Object, ValueBase and fixed<d, s> members.

        any_fixed_example: any・Object・ValueBase・fixed<d, s> のメンバー。
        """
        self.assertRegex(self.text, r'price +typedef Price of fixed-point, 9 digits, 2 after the point')
        self.assertRegex(self.text, r'tax_rate +fixed-point, 5 digits, 4 after the point')
        self.assertRegex(self.text, r'extra +primitive any')
        self.assertRegex(self.text, r'properties +map from primitive string to primitive any')
        self.assertRegex(self.text, r'customer +primitive Object')
        self.assertRegex(self.text, r'note +primitive ValueBase')

    def test_operations(self):
        """any_fixed_example: arguments and return values of operations.

        any_fixed_example: オペレーションの引数と戻り値。
        """
        self.assertIn('total(order: struct shop::Order) -> typedef Price of fixed-point, 9 digits, 2 after the point', self.text)
        self.assertIn('query(key: primitive string) -> primitive any', self.text)

    def test_names_and_defaults(self):
        """any_fixed_example: the fixed type name, to_dic() and default values.

        any_fixed_example: fixed 型の名前、to_dic() とデフォルト値。
        """
        self.assertIn('tax_rate type name: fixed<5, 4>', self.text)
        self.assertIn("'digits': 5, 'scale': 4", self.text)
        self.assertIn('default Item: shop.Item(0, 0, 0, None)', self.text)
        self.assertIn('default Order: shop.Order([], {}, None, None)', self.text)


class TypedefTemplateModuleExampleTest(unittest.TestCase):
    """Category: Examples / カテゴリ: サンプル(examples)

    Output of examples/typedef_template_module_example.py (issue #121).
    examples/typedef_template_module_example.py の出力(#121)。
    """

    @classmethod
    def setUpClass(cls):
        cls.text = run_main('typedef_template_module_example')

    def test_template_module_skipped(self):
        """typedef_template_module_example: template modules are skipped with a warning.

        typedef_template_module_example: テンプレートモジュールは警告を出して読み飛ばされる。
        """
        self.assertIn('unsupported template module "module Buffer <typename T> { ... }" is skipped.', self.text)
        self.assertIn('unsupported template module "module LongBuffer = Buffer<long>" is skipped.', self.text)
        self.assertIn("modules: ['robot']", self.text)

    def test_typedef_constr_types(self):
        """typedef_template_module_example: the types declared in typedefs and the typedefs.

        typedef_template_module_example: typedef の中で宣言した型と typedef。
        """
        self.assertIn("structs:  ['Point', 'Status']", self.text)
        self.assertIn("typedefs: ['typedef Mode ModeT', 'typedef Point PointT', 'typedef Point[4] Polygon', 'typedef Flags FlagsT']", self.text)
        self.assertRegex(self.text, r'mode +typedef ModeT of enum robot::Mode')
        self.assertRegex(self.text, r'area +typedef Polygon of array\[4\] of struct robot::Point')
        self.assertIn('ModeT is Mode: True', self.text)


class PreprocessorExampleTest(unittest.TestCase):
    """Category: Examples / カテゴリ: サンプル(examples)

    Output of examples/preprocessor_example.py (issue #120).
    examples/preprocessor_example.py の出力(#120)。
    """

    @classmethod
    def setUpClass(cls):
        cls.text = run_main('preprocessor_example')

    def test_default(self):
        """preprocessor_example: without defines, #if VERSION >= 2 and MAX_POINTS 16 are used.

        preprocessor_example: defines なしでは #if VERSION >= 2 と MAX_POINTS 16 が使われる。
        """
        first = self.text.split('\n\n')[0]
        self.assertIn('struct Point { double x, double y, double z }', first)
        self.assertIn('Point [16] points', first)
        self.assertIn('intensities bound: 16', first)
        self.assertNotIn('StampedScan', first)

    def test_legacy(self):
        """preprocessor_example: LEGACY selects the #else branch.

        preprocessor_example: LEGACY で #else の分岐が選ばれる。
        """
        second = self.text.split('\n\n')[1]
        self.assertIn("defines={'LEGACY': ''}", second)
        self.assertIn('struct Point { double x, double y }', second)

    def test_timestamp(self):
        """preprocessor_example: USE_TIMESTAMP adds StampedScan and MAX_POINTS 4 overrides the default.

        preprocessor_example: USE_TIMESTAMP で StampedScan が増え、MAX_POINTS 4 が既定値に優先する。
        """
        third = self.text.split('\n\n')[2]
        self.assertIn('struct StampedScan { unsigned long long stamp, Scan scan }', third)
        self.assertIn('Point [4] points', third)
        self.assertIn('intensities bound: 4', third)


class ConditionalIncludeExampleTest(unittest.TestCase):
    """Category: Examples / カテゴリ: サンプル(examples)

    Output of examples/conditional_include_example.py (issue #127).
    examples/conditional_include_example.py の出力(#127)。
    """

    @classmethod
    def setUpClass(cls):
        cls.parts = run_main('conditional_include_example').split('\n\n')

    def test_default(self):
        """conditional_include_example: without defines, the #else file is included.

        conditional_include_example: defines なしでは #else のファイルが include される。
        """
        self.assertIn('Handle is unsigned long (platform_default.idl)', self.parts[0])
        self.assertIn('robot structs: Command\n', self.parts[0] + '\n')

    def test_platform_a(self):
        """conditional_include_example: PLATFORM_A includes platform_a.idl, whose HAS_LIDAR adds LidarScan.

        conditional_include_example: PLATFORM_A で platform_a.idl が読まれ、その HAS_LIDAR で LidarScan が増える。
        """
        self.assertIn("defines={'PLATFORM_A': ''}", self.parts[1])
        self.assertIn('Handle is long (platform_a.idl)', self.parts[1])
        self.assertIn('robot structs: Command, LidarScan', self.parts[1])

    def test_platform_b(self):
        """conditional_include_example: PLATFORM_B includes platform_b.idl.

        conditional_include_example: PLATFORM_B で platform_b.idl が読まれる。
        """
        self.assertIn('Handle is string (platform_b.idl)', self.parts[2])
        self.assertNotIn('LidarScan', self.parts[2])


class EnumExampleTest(unittest.TestCase):
    """Category: Examples / カテゴリ: サンプル(examples)

    Output of examples/enum_example.py.
    examples/enum_example.py の出力。
    """

    def test_output(self):
        """enum_example: enums, enumerator ordinals and enums used as types.

        enum_example: enum 一覧・列挙子の値・型として使われる enum。
        """
        text = run_main('enum_example')
        self.assertIn("enums in my_module: ['Color', 'ReturnCode']", text)
        self.assertIn('enum my_module::Color', text)
        self.assertIn('  RED = 0', text)
        self.assertIn('BLUE is 2', text)
        self.assertIn('Light.color is enum? True (my_module::Color)', text)
        self.assertIn('setColor returns ReturnCode', text)


class EnumValueExampleTest(unittest.TestCase):
    """Category: Examples / カテゴリ: サンプル(examples)

    Output of examples/enum_value_example.py (issue #122).
    examples/enum_value_example.py の出力(#122)。
    """

    def test_output(self):
        """enum_value_example: values set with @value(n) and the values after them.

        enum_value_example: @value(n) で決めた値とそれに続く値。
        """
        text = run_main('enum_value_example')
        self.assertIn('enum robot::Mode', text)
        self.assertRegex(text, r'IDLE +?= 10')
        self.assertRegex(text, r'RUNNING += 11')
        self.assertRegex(text, r'PAUSED += 32')
        self.assertRegex(text, r'UNKNOWN += -1')
        self.assertRegex(text, r'ERROR += 100')
        self.assertIn('FATAL is 101', text)
        self.assertIn("{'IDLE': 10}, {'RUNNING': 11}", text)
        self.assertIn('duplicate value: line 1', text)
        self.assertIn('Value 1 of "B" is already used by "A" in enum "E"', text)


class UnionExampleTest(unittest.TestCase):
    """Category: Examples / カテゴリ: サンプル(examples)

    Output of examples/union_example.py.
    examples/union_example.py の出力。
    """

    @classmethod
    def setUpClass(cls):
        cls.text = run_main('union_example')

    def test_lists_unions(self):
        """union_example: the unions in the module are listed.

        union_example: モジュール内の union 一覧が出力される。
        """
        self.assertIn("unions in module shapes: ['Shape', 'Value', 'Reading', 'OptionalDouble']", self.text)

    def test_discriminator_kinds(self):
        """union_example: discriminator types (enum / long / boolean) are printed.

        union_example: 判別子の型(enum/long/boolean)が出力される。
        """
        self.assertIn('union shapes::Shape switch (ShapeKind)', self.text)
        self.assertIn('union shapes::Value switch (long)', self.text)
        self.assertIn('union shapes::OptionalDouble switch (boolean)', self.text)

    def test_member_types(self):
        """union_example: member types of each case (primitive / struct / typedef / array).

        union_example: 各 case のメンバー型(プリミティブ/struct/typedef/array)。
        """
        self.assertIn('case CIRCLE -> radius: primitive double', self.text)
        self.assertIn('case RECTANGLE -> rect: struct shapes::Rectangle (members: top_left, width, height)',
                      self.text)
        self.assertIn('case POLYGON -> vertices: typedef shapes::PointSeq = sequence of Point2D', self.text)
        self.assertIn('case 2 -> matrix: array double', self.text)

    def test_multiple_labels(self):
        """union_example: cases with several labels, and member lookup by discriminator value.

        union_example: 複数ラベルの case と判別子からのメンバー検索。
        """
        self.assertIn('case -1, 0 -> error_message: primitive string', self.text)
        self.assertIn('Value with discriminator -1 holds: error_message', self.text)
        self.assertIn('Value with discriminator 1 holds: integer_value', self.text)

    def test_default_label(self):
        """union_example: the default label and the default member.

        union_example: default ラベルと default メンバーの表示。
        """
        self.assertIn('default -> raw_points: typedef shapes::PointSeq = sequence of Point2D', self.text)
        self.assertIn('case POINT / default -> position: struct shapes::Point2D (members: x, y)', self.text)
        self.assertIn('Value with any other discriminator holds: raw_points', self.text)
        self.assertIn('Shape default member: None', self.text)
        self.assertIn('"is_default": false', self.text)

    def test_lookup_and_nesting(self):
        """union_example: member full paths, nested structs, enum values and a struct holding a union.

        union_example: メンバーのフルパス・入れ子 struct・enum 値・union を含む struct。
        """
        self.assertIn('Shape.rect full path: shapes::Shape::rect', self.text)
        self.assertIn('Shape.rect.top_left type: shapes::Point2D', self.text)
        self.assertIn("ShapeKind values: ['CIRCLE', 'RECTANGLE', 'POLYGON', 'POINT']", self.text)
        self.assertIn('ShapeMessage.shape: union shapes::Shape', self.text)

    def test_to_dic(self):
        """union_example: JSON output of to_dic().

        union_example: to_dic() の JSON 出力。
        """
        self.assertIn('"descriminator_kind": "boolean"', self.text)


class AnnotationExampleTest(unittest.TestCase):
    """Category: Examples / カテゴリ: サンプル(examples)

    Output of examples/annotation_example.py.
    examples/annotation_example.py の出力。
    """

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
        """annotation_example: annotations of each definition are printed.

        annotation_example: 各定義のアノテーション表示。
        """
        self.assertLine('module robot', '@unit_system(name="SI")')
        self.assertLine('struct JointState', '@extensibility(APPENDABLE) @topic')
        self.assertLine('union Setpoint', '@extensibility(FINAL)')
        self.assertLine('typedef Percent', '@range(min=0, max=100)')
        self.assertLine('const MAX_JOINTS', '@verbatim(language="c++", text="constexpr")')
        self.assertLine('interface Controller', '@service(platform="DDS")')

    def test_members_values_and_arguments(self):
        """annotation_example: annotations of members, enum values, cases, methods and arguments.

        annotation_example: メンバー・enum 値・case・メソッド・引数のアノテーション表示。
        """
        # annotations do not leak into the type name
        self.assertLine('  long joint_id', '@key')
        self.assertLine('  double position', '@range(min=-180, max=180) @unit("deg")')
        self.assertLine('  long sequence_number', '(none)')
        self.assertLine('enum value ERROR', '@value(99) @deprecated')
        self.assertLine('case IDLE: hold_position', '@unit("deg")')
        self.assertLine('method setMode', '@oneway_hint')
        self.assertLine('arg joint_id', '@range(min=0, max=6)')

    def test_arguments(self):
        """annotation_example: output of the ways to read annotation arguments.

        annotation_example: アノテーション引数の取り出し方の出力。
        """
        self.assertIn("params:  {'min': '-180', 'max': '180'}", self.text)
        self.assertIn('min/max: -180 180', self.text)
        self.assertIn('unit without quotes: deg', self.text)
        self.assertIn('IDLE value: 10', self.text)
        self.assertIn('ERROR deprecated? True', self.text)
        self.assertIn('effort optional? True', self.text)
        self.assertIn('sequence_number annotation: None', self.text)

    def test_keys(self):
        """annotation_example: keys from @key and keylist are printed.

        annotation_example: @key/keylist によるキーの出力。
        """
        self.assertIn("JointState keys: ['joint_id', 'robot_name']", self.text)
        self.assertIn("Command keys: ['target_id', 'command_id']", self.text)

    def test_bitmask(self):
        """annotation_example: bit_bound and positions of a bitmask are printed.

        annotation_example: bitmask の bit_bound と位置の出力。
        """
        self.assertIn('Status bit_bound: 8', self.text)
        self.assertIn("('FAULT', 7)", self.text)

    def test_to_dic(self):
        """annotation_example: annotations in the to_dic() output.

        annotation_example: to_dic() のアノテーション出力。
        """
        self.assertIn('"name": "extensibility"', self.text)
        self.assertIn('"APPENDABLE"', self.text)


class ScopedNameExampleTest(unittest.TestCase):
    """Category: Examples / カテゴリ: サンプル(examples)

    Output of examples/scoped_name_example.py.
    examples/scoped_name_example.py の出力。
    """

    @classmethod
    def setUpClass(cls):
        cls.text = run_main('scoped_name_example')

    def assertResolved(self, label, written, definition):
        for line in self.text.splitlines():
            if line.split() == [*label.split(), written, '->', definition]:
                return
        self.fail('no line for %s %s -> %s in output:\n%s' % (label, written, definition, self.text))

    def test_relative_names(self):
        """scoped_name_example: how relative type names are resolved.

        scoped_name_example: 相対名の型解決結果。
        """
        self.assertResolved('current() returns', 'Point', 'robot::arm::Point')
        self.assertResolved('move_joint(p)', 'robot::Point', 'robot::Point')
        self.assertResolved('move_to(p)', 'geometry::Point', 'geometry::Point')
        self.assertResolved('move_to_3d(p)', 'geometry::d3::Point', 'geometry::d3::Point')

    def test_absolute_names(self):
        """scoped_name_example: how absolute names starting with :: are resolved.

        scoped_name_example: :: で始まる絶対名の型解決結果。
        """
        self.assertResolved('mark(p)', '::Point', '::Point')
        self.assertResolved('move_arm(p)', '::robot::arm::Point', 'robot::arm::Point')

    def test_struct_members(self):
        """scoped_name_example: how struct member types are resolved.

        scoped_name_example: struct メンバーの型解決結果。
        """
        self.assertIn('  joint                  -> robot::Point', self.text)
        self.assertIn('  arm                    -> robot::arm::Point', self.text)
        self.assertIn('  path                   -> sequence of geometry::Point', self.text)
        self.assertIn('  marker                 -> ::Point', self.text)

    def test_typedef_and_names(self):
        """scoped_name_example: typedefs and the difference between name, ref_name and full_path.

        scoped_name_example: typedef と name/ref_name/full_path の違い。
        """
        self.assertIn('typedef geometry::Origin -> geometry::Point', self.text)
        self.assertIn('name: Point, ref_name: geometry::Point, full path: geometry::Point', self.text)

    def test_find_types(self):
        """scoped_name_example: find_types() with and without scope.

        scoped_name_example: scope 指定あり/なしの find_types()。
        """
        self.assertIn("scope=robot::arm): ['robot::arm::Point']", self.text)
        self.assertIn("scope=robot):      ['robot::Point']", self.text)
        self.assertIn("(no scope):        ['::Point', 'geometry::Point', 'geometry::d3::Point', "
                      "'robot::Point', 'robot::arm::Point']", self.text)


class ValueTypeExampleTest(unittest.TestCase):
    """Category: Examples / カテゴリ: サンプル(examples)

    Output of examples/valuetype_example.py (issue #99).
    examples/valuetype_example.py の出力(#99)。
    """

    @classmethod
    def setUpClass(cls):
        cls.text = run_main('valuetype_example')

    def test_lists_valuetypes_and_eventtypes(self):
        """valuetype_example: the value types and event types in the module are listed.

        valuetype_example: モジュール内の valuetype / eventtype 一覧が出力される。
        """
        self.assertIn("valuetypes in module sensors: ['Describable', 'Reading', 'RangedReading', "
                      "'Calibration', 'ReadingNode', 'OptionalName', 'OptionalValues']", self.text)
        self.assertIn("eventtypes in module sensors: ['Alarm', 'CriticalAlarm']", self.text)

    def test_body(self):
        """valuetype_example: state members, factories, operations and attributes.

        valuetype_example: 状態メンバー・factory・operation・attribute。
        """
        self.assertIn('  private long long raw', self.text)
        self.assertIn("  factory create(in double value, in string unit) raises ['InvalidRange']", self.text)
        self.assertIn('  operation double scaled(in double factor)', self.text)
        self.assertIn('  readonly attribute boolean valid', self.text)

    def test_header(self):
        """valuetype_example: modifiers, inheritance, supports and boxed value types.

        valuetype_example: 修飾子・継承・supports・boxed value。
        """
        self.assertIn('abstract valuetype sensors::Describable', self.text)
        self.assertIn('custom valuetype sensors::Calibration', self.text)
        self.assertIn('  inherits: truncatable sensors::Reading', self.text)
        self.assertIn('  supports: sensors::Resettable', self.text)
        self.assertIn('  boxed type: string', self.text)
        self.assertIn('eventtype sensors::CriticalAlarm\n  inherits: sensors::Alarm', self.text)

    def test_used_as_types(self):
        """valuetype_example: value types and event types used as member, return and argument types.

        valuetype_example: メンバー・戻り値・引数の型としての valuetype / eventtype。
        """
        self.assertIn("Reading.create raises: ['sensors::InvalidRange']", self.text)
        self.assertIn('ReadingNode.next type is ReadingNode: True', self.text)
        self.assertIn('Snapshot.label: IDLValueType sensors::OptionalName', self.text)
        self.assertIn('Monitor.read returns: sensors::Reading', self.text)
        self.assertIn('Monitor.notify(alarm) is an eventtype: True', self.text)
        self.assertIn('"truncatable": true', self.text)


class IncludeDirsExampleTest(unittest.TestCase):
    """Category: Examples / カテゴリ: サンプル(examples)

    Output of examples/include_dirs_example.py.
    examples/include_dirs_example.py の出力。
    """

    @classmethod
    def setUpClass(cls):
        cls.text = run_main('include_dirs_example')

    def test_includes(self):
        """include_dirs_example: includes() and the include tree across directories.

        include_dirs_example: ディレクトリをまたぐ includes() と include ツリー。
        """
        self.assertIn("geometry/path.idl -> ['geometry/geometry.idl', 'common/time.idl']", self.text)
        self.assertIn('    geometry/path.idl\n      geometry/geometry.idl\n        common/time.idl\n'
                      '      common/time.idl (already shown)', self.text)

    def test_transitive_parse(self):
        """include_dirs_example: parsing one file reads the files it includes, through other files too.

        include_dirs_example: 1ファイルの parse で、間接的に include されたファイルも読まれる。
        """
        self.assertRegex(self.text, r'module common +Time\n')
        self.assertRegex(self.text, r'module geometry +Point, Pose, Path, PoseList\n')
        self.assertRegex(self.text, r'module navigation +Navigator\n')
        self.assertIn('Pose.stamp type: common::Time', self.text)
        self.assertIn("Navigator.plan(geometry::Pose) returns geometry::Path "
                      "raises ['navigation::Unreachable']", self.text)
        self.assertIn('load() defines the same modules: True', self.text)
        self.assertIn("parse_dirs() parsed 4 files: ['common/time.idl', 'geometry/geometry.idl', "
                      "'geometry/path.idl', 'navigation/navigator.idl']", self.text)
        self.assertIn('without common/: IDLCanNotFindException', self.text)


if __name__ == '__main__':
    unittest.main()
