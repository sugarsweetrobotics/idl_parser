"""const definitions: string literals with spaces, multi-word types, expressions
and malformed consts (issue #52).
"""
import os
import tempfile
import unittest
from idl_parser import parser
from idl_parser.exception import InvalidIDLSyntaxError


def load(idl):
    return parser.IDLParser().load(idl)


def consts(g, module='M'):
    return [(c.typename, c.name, c.value) for c in g.module_by_name(module).consts]


class ConstStringWithSpacesTest(unittest.TestCase):

    def test_issue_example(self):
        g = load('module M { const string S = "hello world"; '
                 'const string T = "a  b"; const long N = 1; };')
        self.assertEqual(consts(g), [('string', 'S', '"hello world"'),
                                     ('string', 'T', '"a  b"'),
                                     ('long', 'N', '1')])

    def test_tab_and_leading_trailing_spaces(self):
        g = load('module M { const string S = " a\tb "; };')
        self.assertEqual(consts(g), [('string', 'S', '" a\tb "')])

    def test_char_space(self):
        g = load("module M { const char C = ' '; };")
        self.assertEqual(consts(g), [('char', 'C', "' '")])

    def test_wide_string(self):
        g = load('module M { const wstring W = L"x y"; };')
        self.assertEqual(consts(g), [('wstring', 'W', 'L"x y"')])

    def test_semicolon_and_equal_in_literal(self):
        g = load('module M { const string S = "a = b; c"; const long N = 2; };')
        self.assertEqual(consts(g), [('string', 'S', '"a = b; c"'),
                                     ('long', 'N', '2')])

    def test_from_file(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, 'c.idl')
            with open(path, 'w') as f:
                f.write('module M {\n  const string S = "hello world";\n'
                        '  const string T = "a  b";\n};\n')
            p = parser.IDLParser()
            p.parse(idls=[path])
            self.assertEqual(consts(p.global_module),
                             [('string', 'S', '"hello world"'),
                              ('string', 'T', '"a  b"')])


class ConstSplitAtEqualTest(unittest.TestCase):

    def test_multi_word_type(self):
        g = load('module M { const unsigned long long U = 5; };')
        self.assertEqual(consts(g), [('unsigned long long', 'U', '5')])

    def test_expression_value(self):
        g = load('module M { const long X = 1 + 2; };')
        self.assertEqual(consts(g), [('long', 'X', '1 + 2')])

    def test_no_equal(self):
        with self.assertRaises(InvalidIDLSyntaxError):
            load('module M { const long X 1; };')

    def test_no_name(self):
        with self.assertRaises(InvalidIDLSyntaxError):
            load('module M { const long = 1; };')

    def test_no_value(self):
        with self.assertRaises(InvalidIDLSyntaxError):
            load('module M { const long X = ; };')


if __name__ == '__main__':
    unittest.main()
