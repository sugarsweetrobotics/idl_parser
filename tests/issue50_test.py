"""Regression tests for issue #50.

"//" and "/*" inside a string literal were taken as comments, so the rest of
the line was dropped. Depending on the IDL this silently lost a const, made
load() never return, or raised a syntax error for an annotation.
"""
import os
import subprocess
import sys
import tempfile
import unittest
from idl_parser import parser
from idl_parser.exception import InvalidIDLSyntaxError


def load(idl):
    return parser.IDLParser().load(idl)


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CHILD = '''
import sys
from idl_parser import parser
try:
    parser.IDLParser().load(sys.argv[1])
except Exception:
    pass
'''


def load_with_timeout(idl, seconds=20):
    """load(), but fail instead of hanging the whole test run.

    The hang in issue #50 also kept growing a list, so it is first tried
    in a child process that can be killed.
    """
    env = dict(os.environ)
    env['PYTHONPATH'] = ROOT + os.pathsep + env.get('PYTHONPATH', '')
    try:
        subprocess.run([sys.executable, '-c', CHILD, idl], cwd=ROOT, env=env,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       timeout=seconds)
    except subprocess.TimeoutExpired:
        raise AssertionError('load() did not return: %r' % idl)
    return load(idl)


def consts(g, module='M'):
    return [(c.name, c.value) for c in g.module_by_name(module).consts]


class Issue50Test(unittest.TestCase):

    def test_url_const_is_kept(self):
        g = load('''module M {
  const string URL = "http://example.com";
  const long N = 1;
};''')
        self.assertEqual(consts(g), [('URL', '"http://example.com"'), ('N', '1')])

    def test_one_line_idl_does_not_hang(self):
        cases = {
            'module M { const string S = "http://x"; };': '"http://x"',
            'module M { const string S = "a/*b*/c"; };': '"a/*b*/c"',
            'module M { const string S = "a/*b"; };': '"a/*b"',
            "module M { const char C = '/'; };": "'/'",
        }
        for idl, value in cases.items():
            with self.subTest(idl):
                g = load_with_timeout(idl)
                self.assertEqual(consts(g), [(consts(g)[0][0], value)])

    def test_escaped_quote_in_string(self):
        g = load_with_timeout(r'module M { const string S = "a\"//b"; const long N = 1; };')
        self.assertEqual(consts(g), [('S', r'"a\"//b"'), ('N', '1')])

    def test_punctuation_in_string_is_untouched(self):
        g = load_with_timeout('module M { const string S = "a,b;c=d(e){f}:g"; };')
        self.assertEqual(consts(g), [('S', '"a,b;c=d(e){f}:g"')])

    def test_annotation_arguments(self):
        g = load('module M { @verbatim(language="c++", text="// x") const long C = 3; };')
        a = g.module_by_name('M').const_by_name('C').annotation_by_name('verbatim')
        self.assertEqual(a.params, {'language': '"c++"', 'text': '"// x"'})

        g = load('module M { struct S { @unit("m//s") double v; }; };')
        v = g.module_by_name('M').struct_by_name('S').members[0]
        self.assertEqual(v.annotation_by_name('unit').args, ['"m//s"'])

    def test_comments_are_still_removed(self):
        g = load('''module M {
  // const long A = 1;
  const string S = "x"; // "trailing" comment
  /* const long B = 2; "*/ const long C = 3; /* multi
     line "comment" */ const long D = 4;
};''')
        self.assertEqual(consts(g), [('S', '"x"'), ('C', '3'), ('D', '4')])

    def test_string_literal_in_included_file(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, 'inc.idl'), 'w') as f:
                f.write('module I { const string U = "http://example.com"; };\n')
            g = parser.IDLParser(idl_dirs=[d]).load(
                '#include "inc.idl"\nmodule M { const long N = 1; };')
        self.assertEqual(consts(g, 'I'), [('U', '"http://example.com"')])

    def test_unterminated_input_raises(self):
        for idl in ['module M { const string S = "x"',
                    'module M { const string S = "x',
                    'module M { const long N = 1']:
            with self.subTest(idl):
                with self.assertRaises(InvalidIDLSyntaxError):
                    load_with_timeout(idl)


if __name__ == '__main__':
    unittest.main()
