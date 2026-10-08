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
    """Category: Primitive types and constants / カテゴリ: 基本型・定数

    String consts with spaces keep their name and value (issue #52).
    空白を含む文字列 const の名前と値が正しい(#52)。
    """

    def test_issue_example(self):
        """A string const with spaces gets the right name and value, and the next const is not dropped.

        空白を含む文字列 const の名前・値が正しく、後続の const も落ちない。
        """
        g = load('module M { const string S = "hello world"; '
                 'const string T = "a  b"; const long N = 1; };')
        self.assertEqual(consts(g), [('string', 'S', '"hello world"'),
                                     ('string', 'T', '"a  b"'),
                                     ('long', 'N', '1')])

    def test_tab_and_leading_trailing_spaces(self):
        """A string const with a tab and leading / trailing spaces.

        タブ・前後の空白を含む文字列 const。
        """
        g = load('module M { const string S = " a\tb "; };')
        self.assertEqual(consts(g), [('string', 'S', '" a\tb "')])

    def test_char_space(self):
        """A char const ' '.

        ' ' の char const。
        """
        g = load("module M { const char C = ' '; };")
        self.assertEqual(consts(g), [('char', 'C', "' '")])

    def test_wide_string(self):
        """A wstring const L"x y".

        L"x y" の wstring const。
        """
        g = load('module M { const wstring W = L"x y"; };')
        self.assertEqual(consts(g), [('wstring', 'W', 'L"x y"')])

    def test_semicolon_and_equal_in_literal(self):
        """A const whose string contains ";" and "=".

        文字列中に ; や = を含む const。
        """
        g = load('module M { const string S = "a = b; c"; const long N = 2; };')
        self.assertEqual(consts(g), [('string', 'S', '"a = b; c"'),
                                     ('long', 'N', '2')])

    def test_from_file(self):
        """String consts with spaces are also right when parse()d from a file.

        ファイルから parse() しても空白入り文字列 const が正しい。
        """
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
    """Category: Primitive types and constants / カテゴリ: 基本型・定数

    Consts are split at "=", and malformed consts are errors (issue #52).
    const を "=" で分割し、不正な const はエラーにする(#52)。
    """

    def test_multi_word_type(self):
        """A const of a multi-word type such as unsigned long long.

        unsigned long long のような複数語の型の const。
        """
        g = load('module M { const unsigned long long U = 5; };')
        self.assertEqual(consts(g), [('unsigned long long', 'U', '5')])

    def test_expression_value(self):
        """An expression value such as 1 + 2 is kept as written.

        1 + 2 のような式の値が書いたまま保持される。
        """
        g = load('module M { const long X = 1 + 2; };')
        self.assertEqual(consts(g), [('long', 'X', '1 + 2')])

    def test_no_equal(self):
        """A const without "=" is an error.

        = がない const でエラー。
        """
        with self.assertRaises(InvalidIDLSyntaxError):
            load('module M { const long X 1; };')

    def test_no_name(self):
        """A const without a name is an error.

        名前がない const でエラー。
        """
        with self.assertRaises(InvalidIDLSyntaxError):
            load('module M { const long = 1; };')

    def test_no_value(self):
        """A const without a value is an error.

        値がない const でエラー。
        """
        with self.assertRaises(InvalidIDLSyntaxError):
            load('module M { const long X = ; };')


if __name__ == '__main__':
    unittest.main()
