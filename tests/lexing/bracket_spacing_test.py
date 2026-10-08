"""Regression tests for issue #53.

load() removed the spaces just inside "[ ]" and "< >" from the whole input
with regular expressions, before comments and literals were found, so the
spaces in a literal such as "[ x ]" were lost. parse() did not do this at
all, so "long a[ 5 ]" could be loaded from a string but not from a file.
The joining is now done on tokens, outside literals, for both.
"""
import os
import tempfile
import unittest
from idl_parser import parser
from idl_parser.exception import InvalidIDLSyntaxError
from idl_parser.token_buffer import join_brackets


def load(idl):
    return parser.IDLParser().load(idl)


def parse(idl):
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, 'c.idl')
        with open(path, 'w') as f:
            f.write(idl)
        p = parser.IDLParser()
        p.parse(idls=[path])
        return p.global_module


def consts(g, module='M'):
    return [(c.name, c.value) for c in g.module_by_name(module).consts]


def members(g, struct='S', module='M'):
    s = g.module_by_name(module).struct_by_name(struct)
    return [(m.name, str(m.type)) for m in s.members]


def join(*tokens):
    return [t for _, _, t in join_brackets([(1, None, t) for t in tokens])]


class JoinBracketsTest(unittest.TestCase):
    """Category: Lexing, preprocessing and error line numbers / カテゴリ: 字句解析・前処理・エラー行番号

    join_brackets() joins the tokens inside [ ] and < > (issue #53).
    join_brackets() による [ ] と < > の中のトークンの結合(#53)。
    """

    def test_array(self):
        """join_brackets(): "a[ 5 ]" is joined into "a[5]".

        join_brackets(): a[ 5 ] を a[5] に結合。
        """
        self.assertEqual(join('long', 'a[', '5', ']', ';'), ['long', 'a[5]', ';'])

    def test_template(self):
        """join_brackets(): "string< 8 >" is joined.

        join_brackets(): string< 8 > を結合。
        """
        self.assertEqual(join('string<', '8', '>', 's'), ['string<8>', 's'])

    def test_nested(self):
        """join_brackets(): nested "<" ">" are joined.

        join_brackets(): 入れ子の < > を結合。
        """
        self.assertEqual(join('sequence<', 'string<', '8', '>', '>'),
                         ['sequence<string<8>>'])

    def test_literal_not_joined(self):
        """join_brackets(): "[ ]" inside a literal is not joined.

        join_brackets(): リテラル内の [ ] は結合しない。
        """
        self.assertEqual(join('A', '=', '"[ x ]"', ';'), ['A', '=', '"[ x ]"', ';'])
        self.assertEqual(join('a[', '"x"', ']'), ['a[', '"x"', ']'])

    def test_keeps_first_line_number(self):
        """join_brackets(): a joined token keeps the line number of its first part.

        join_brackets(): 結合したトークンが最初の行番号を保つ。
        """
        tokens = [(1, 'f', 'a['), (2, 'f', '5'), (3, 'f', ']')]
        self.assertEqual(join_brackets(tokens), [(1, 'f', 'a[5]')])


class LiteralKeepsSpacesTest(unittest.TestCase):
    """Category: Lexing, preprocessing and error line numbers / カテゴリ: 字句解析・前処理・エラー行番号

    Spaces inside literals are not removed (issue #53).
    リテラル内の空白が削除されない(#53)。
    """

    IDL = 'module M { const string A = "[ x ]"; const string B = "< y >"; };'
    EXPECTED = [('A', '"[ x ]"'), ('B', '"< y >"')]

    def test_load(self):
        """load(): spaces in literals such as "[ x ]" are not lost.

        load(): リテラル "[ x ]" などの空白が失われない。
        """
        self.assertEqual(consts(load(self.IDL)), self.EXPECTED)

    def test_parse(self):
        """parse(): spaces in literals are not lost.

        parse(): リテラルの空白が失われない。
        """
        self.assertEqual(consts(parse(self.IDL)), self.EXPECTED)

    def test_char_literal(self):
        """Char literals '[' and '>'.

        '[' や '>' の文字リテラル。
        """
        g = load("module M { const char C = '['; const char D = '>'; };")
        self.assertEqual(consts(g), [('C', "'['"), ('D', "'>'")])

    def test_annotations(self):
        """Spaces around [ ] < > in string arguments of annotations are kept.

        アノテーション引数の文字列中の [ ] < > の空白が保持される。
        """
        g = load('module M { struct X { @unit("[ m ]") double v; '
                 '@doc("a  <  b") long w; }; };')
        s = g.module_by_name('M').struct_by_name('X')
        self.assertEqual([m.annotations[0].args for m in s.members],
                         [['"[ m ]"'], ['"a  <  b"']])


class SpacesInsideBracketsTest(unittest.TestCase):
    """Category: Lexing, preprocessing and error line numbers / カテゴリ: 字句解析・前処理・エラー行番号

    Spaces and comments inside [ ] and < > are accepted (issue #53).
    [ ] と < > の中の空白・コメントを受け付ける(#53)。
    """

    IDL = ('module M { struct S { long a[ 5 ]; string< 8 > s; long b[\n'
           '  3 ]; sequence< long > q; }; };\n')

    def check(self, g):
        self.assertEqual(members(g), [('a', 'long[5]'), ('s', 'string'),
                                      ('b', 'long[3]'), ('q', 'sequence<long>')])
        s = g.module_by_name('M').struct_by_name('S')
        self.assertEqual(s.member_by_name('s').type.bound, 8)

    def test_load(self):
        """load(): spaces inside brackets, as in "long a[ 5 ]", are accepted.

        load(): long a[ 5 ] のような括弧内の空白を許容。
        """
        self.check(load(self.IDL))

    def test_parse(self):
        """parse(): spaces inside brackets are accepted (same result as load()).

        parse(): 括弧内の空白を許容(load と同じ結果)。
        """
        # This raised InvalidDataTypeException before issue #53.
        self.check(parse(self.IDL))

    def test_comment_inside_brackets(self):
        """A comment inside brackets, as in "a[ /* size */ 5 ]".

        a[ /* size */ 5 ] のように括弧内のコメント。
        """
        g = load('module M { struct S { long a[ /* size */ 5 ]; }; };')
        self.assertEqual(members(g), [('a', 'long[5]')])

    def test_line_numbers_kept(self):
        """Error line numbers do not shift after brackets are joined.

        括弧の結合後もエラー行番号がずれない。
        """
        # load() used to remove the newline inside "[ ]", so later lines
        # were reported one line too early.
        idl = 'module M {\n  struct S {\n    long a[\n 5 ];\n  };\n  const long X;\n};\n'
        with self.assertRaises(InvalidIDLSyntaxError) as cm:
            load(idl)
        self.assertEqual(cm.exception.line_number, 6)


class PrepareInputDeprecatedTest(unittest.TestCase):
    """Category: Lexing, preprocessing and error line numbers / カテゴリ: 字句解析・前処理・エラー行番号

    The old prepare_input() is deprecated but still works.
    旧 prepare_input() は非推奨だが動作する。
    """

    def test_warns_and_still_works(self):
        """prepare_input() still works and issues a DeprecationWarning.

        prepare_input() が DeprecationWarning を出しつつ動く。
        """
        with self.assertWarns(DeprecationWarning):
            out = parser.IDLParser().prepare_input('long a[ 5 ];')
        self.assertEqual(out, 'long a[5];')

    def test_load_does_not_warn(self):
        """load() does not issue a DeprecationWarning.

        load() は DeprecationWarning を出さない。
        """
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter('error', DeprecationWarning)
            load('module M { struct S { long a[ 5 ]; }; };')


if __name__ == '__main__':
    unittest.main()
