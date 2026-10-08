"""Regression tests for issue #45.

IDLMethod.parse_blocks read every token after the "(" of the argument list
and did not stop at the ")" that closes it, so the exception names in a
following "raises (...)" (and the names in "context (...)") were parsed as
arguments. The arguments now end at the matching ")", and the names are
available as IDLMethod.raises and IDLMethod.contexts.
"""
import unittest
from idl_parser import parser
from idl_parser.exception import InvalidIDLSyntaxError


IDL = '''
module M {
  exception E { string s; };
  exception F { long x; };
  module N { exception G { long y; }; };
  interface I {
    long f(in long a) raises (E);
    long g(in long a, out string b) raises (E, F);
    void h() raises (E);
    void i(in long a)raises(N::G);
    oneway void j(in long a);
    long k(in long a);
    long l(in long a) raises (E) context ("x", "y");
    long m(in long a) context ("x");
    @range(min=0, max=9) long n(@range(min=0, max=9) in long a) raises (E);
  };
};
'''


def method(g, name):
    return g.module_by_name('M').interface_by_name('I').method_by_name(name)


def arguments(m):
    return [(a.direction, str(a.type), a.name) for a in m.arguments]


class RaisesTest(unittest.TestCase):
    """Category: Interfaces, operations and inheritance / カテゴリ: interface・operation・継承

    raises and context of operations (issue #45).
    オペレーションの raises と context(#45)。
    """

    @classmethod
    def setUpClass(cls):
        cls.g = parser.IDLParser().load(IDL)

    def test_issue_example(self):
        """The example from issue #45: exception names in raises do not become arguments.

        issue #45 の例: raises の例外名が引数に混入しない。
        """
        f = method(self.g, 'f')
        self.assertEqual([(a.name, str(a.type)) for a in f.arguments], [('a', 'long')])
        self.assertEqual(f.raises, ['E'])

    def test_multiple_exceptions(self):
        """raises (E, F) with several arguments.

        raises (E, F) と複数引数。
        """
        m = method(self.g, 'g')
        self.assertEqual(arguments(m), [('in', 'long', 'a'), ('out', 'string', 'b')])
        self.assertEqual(m.raises, ['E', 'F'])

    def test_no_arguments(self):
        """raises on a method without arguments.

        引数なしメソッドの raises。
        """
        m = method(self.g, 'h')
        self.assertEqual(m.arguments, [])
        self.assertEqual(m.raises, ['E'])

    def test_scoped_name_without_spaces(self):
        """A scoped exception name without spaces, as in raises(N::G).

        raises(N::G) のように空白なしのスコープ付き例外名。
        """
        m = method(self.g, 'i')
        self.assertEqual(arguments(m), [('in', 'long', 'a')])
        self.assertEqual(m.raises, ['N::G'])

    def test_oneway(self):
        """Detection of oneway methods.

        oneway メソッドの判定。
        """
        m = method(self.g, 'j')
        self.assertTrue(m.oneway)
        self.assertEqual(arguments(m), [('in', 'long', 'a')])
        self.assertEqual(m.raises, [])
        self.assertFalse(method(self.g, 'k').oneway)

    def test_without_raises(self):
        """Without raises, raises and contexts are empty.

        raises なしなら raises/contexts が空。
        """
        m = method(self.g, 'k')
        self.assertEqual(arguments(m), [('in', 'long', 'a')])
        self.assertEqual(m.raises, [])
        self.assertEqual(m.contexts, [])

    def test_context(self):
        """context ("x", "y") is parsed, with and without raises.

        context ("x", "y") の解析(raises との併用あり/なし)。
        """
        m = method(self.g, 'l')
        self.assertEqual(arguments(m), [('in', 'long', 'a')])
        self.assertEqual(m.raises, ['E'])
        self.assertEqual(m.contexts, ['x', 'y'])
        m = method(self.g, 'm')
        self.assertEqual(arguments(m), [('in', 'long', 'a')])
        self.assertEqual(m.raises, [])
        self.assertEqual(m.contexts, ['x'])

    def test_with_annotations(self):
        """raises on a method and arguments with annotations.

        アノテーション付きのメソッド・引数と raises。
        """
        m = method(self.g, 'n')
        self.assertEqual(arguments(m), [('in', 'long', 'a')])
        self.assertEqual(m.raises, ['E'])
        self.assertTrue(m.has_annotation('range'))
        self.assertTrue(m.arguments[0].has_annotation('range'))

    def test_to_dic(self):
        """to_dic() contains raises / context, and leaves the keys out when there are none.

        to_dic() に raises/context が出て、無いときはキーが出ない。
        """
        self.assertEqual(method(self.g, 'g').to_dic()['raises'], ['E', 'F'])
        self.assertEqual(method(self.g, 'l').to_dic()['context'], ['x', 'y'])
        d = method(self.g, 'k').to_dic()
        self.assertNotIn('raises', d)
        self.assertNotIn('context', d)

    def test_simple_dic_params(self):
        """params in to_simple_dic() do not include raises.

        to_simple_dic() の params に raises が混ざらない。
        """
        self.assertEqual(method(self.g, 'g').to_simple_dic(),
                         {'g': {'returns': 'long', 'params': ['in long a', 'out string b']}})


class InvalidRaisesTest(unittest.TestCase):
    """Category: Interfaces, operations and inheritance / カテゴリ: interface・operation・継承

    Malformed raises and argument lists are errors.
    不正な raises や引数リストはエラーになる。
    """

    def load(self, op):
        return parser.IDLParser().load('module M { interface I { %s }; };' % op)

    def test_raises_without_paren(self):
        """raises without parentheses is an error.

        raises の後に括弧がないとエラー。
        """
        with self.assertRaises(InvalidIDLSyntaxError):
            self.load('void f() raises E;')

    def test_unclosed_raises(self):
        """Unclosed parentheses after raises are an error.

        raises の括弧が閉じていないとエラー。
        """
        with self.assertRaises(InvalidIDLSyntaxError):
            self.load('void f() raises (E;')

    def test_empty_raises(self):
        """An empty raises () is an error.

        raises () が空だとエラー。
        """
        with self.assertRaises(InvalidIDLSyntaxError):
            self.load('void f() raises ();')

    def test_unexpected_token(self):
        """An unexpected keyword such as throws is an error.

        throws など想定外のキーワードでエラー。
        """
        with self.assertRaises(InvalidIDLSyntaxError):
            self.load('void f() throws (E);')

    def test_unclosed_arguments(self):
        """An unclosed argument list is an error.

        引数リストの括弧が閉じていないとエラー。
        """
        with self.assertRaises(InvalidIDLSyntaxError):
            self.load('void f(in long a;')


if __name__ == '__main__':
    unittest.main()
