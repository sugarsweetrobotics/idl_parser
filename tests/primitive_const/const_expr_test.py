"""Constant expressions in array sizes, bounds and const values (issue #130)."""
import unittest
from idl_parser import parser, exception
from idl_parser import const_expr


def load(idl, **kwargs):
    return parser.IDLParser(**kwargs).load(idl)


def const_value(idl, name, module=None):
    g = load(idl)
    scope = g.module_by_name(module) if module else g
    return scope.const_by_name(name).value


class ConstValueTest(unittest.TestCase):
    """Category: Primitive types and constants / カテゴリ: 基本型・定数

    The values of integer consts are evaluated (issue #130).
    整数型の const の値が評価される(#130)。
    """

    def test_issue_example(self):
        """const long M = N*2; gives M.value == 6 when N is 3.

        N が 3 のとき const long M = N*2; の M.value は 6。
        """
        g = load('const long N = 3; const long M = N*2;')
        m = g.const_by_name('M')
        self.assertEqual(m.value, 6)
        self.assertEqual(m.int_value, 6)
        self.assertEqual(m.value_string, 'N*2')

    def test_operators_and_precedence(self):
        """All operators of const_expr with the precedence of IDL / C++.

        const_expr の全演算子が IDL / C++ の優先順位で評価される。
        """
        cases = [
            ('1 + 2 * 3', 7),
            ('(1 + 2) * 3', 9),
            ('10 - 4 - 3', 3),
            ('1 << 4 | 1', 17),
            ('6 & 3 ^ 1', 3),     # & binds tighter than ^
            ('1 | 6 ^ 3', 5),     # ^ binds tighter than |
            ('1 + 2 << 1', 6),    # + binds tighter than <<
            ('256 >> 2 >> 1', 32),
            ('-3 + 5', 2),
            ('- -3', 3),
            ('+4', 4),
            ('~0', -1),
            ('~0 & 0xFF', 255),
            ('17 % 5', 2),
            ('(((2)))', 2),
        ]
        for expr, expected in cases:
            with self.subTest(expr):
                self.assertEqual(const_value('const long long X = %s;' % expr, 'X'), expected)

    def test_division_rounds_toward_zero(self):
        """/ rounds toward zero and % has the sign of the left operand, as in C++.

        C++ と同じく / は 0 方向に丸め、% の符号は左オペランドと同じ。
        """
        for expr, expected in (('7 / 2', 3), ('-7 / 2', -3), ('7 / -2', -3),
                               ('-7 % 2', -1), ('7 % -2', 1)):
            with self.subTest(expr):
                self.assertEqual(const_value('const long X = %s;' % expr, 'X'), expected)

    def test_literals(self):
        """Decimal, octal and hexadecimal integer literals.

        10 進・8 進・16 進の整数リテラル。
        """
        for expr, expected in (('0', 0), ('010', 8), ('0x1F', 31), ('0XfF', 255), ('10', 10)):
            with self.subTest(expr):
                self.assertEqual(const_value('const unsigned long X = %s;' % expr, 'X'), expected)

    def test_scoped_names(self):
        """Constants named with a scope (M::N, ::M::N) and from enclosing scopes.

        スコープ付き名(M::N, ::M::N)や外側スコープの定数を参照できる。
        """
        idl = '''
        const long G = 1;
        module A {
          const long N = 2;
          module B {
            const long N = 10;
            const long X = N + A::N + ::A::N + G;
          };
          const long Y = B::N * 2;
        };
        '''
        g = load(idl)
        a = g.module_by_name('A')
        self.assertEqual(a.module_by_name('B').const_by_name('X').value, 15)
        self.assertEqual(a.const_by_name('Y').value, 20)

    def test_interface_const(self):
        """A const in an interface can use the consts before it and size an array there.

        インターフェース内の const は前の const を使え、そこで配列サイズにできる。
        """
        g = load('module M { interface I { const long N = 2; const long M2 = N * N;'
                 ' typedef long A[M2 + 1]; }; };')
        i = g.module_by_name('M').interface_by_name('I')
        self.assertEqual(i.const_by_name('M2').value, 4)
        self.assertEqual(i.typedef_by_name('A').type.size, 5)

    def test_integer_types_and_typedef(self):
        """Values of every integer type, and of a typedef of one, are evaluated.

        すべての整数型と、その typedef の const が評価される。
        """
        for typ in sorted(const_expr.integer_types):
            with self.subTest(typ):
                self.assertEqual(const_value('const %s X = 1 + 1;' % typ, 'X'), 2)
        g = load('typedef unsigned long Count; typedef Count Count2; const Count2 X = 2 * 2;')
        self.assertEqual(g.const_by_name('X').value, 4)

    def test_other_types_are_kept_as_written(self):
        """Consts of other types (float, string, boolean, char) keep the value as written.

        それ以外の型(float, string, boolean, char)の const は書いたまま。
        """
        g = load('const double D = 1.5 * 2; const string S = "a"; const boolean B = TRUE;'
                 " const char C = 'x';")
        self.assertEqual([(c.name, c.value, c.int_value) for c in g.consts],
                         [('D', '1.5 * 2', None), ('S', '"a"', None), ('B', 'TRUE', None),
                          ('C', "'x'", None)])

    def test_to_dic(self):
        """to_dic() and to_simple_dic() give the evaluated value.

        to_dic() と to_simple_dic() は評価済みの値を返す。
        """
        c = load('const long N = 3; const long M = N + 1;').const_by_name('M')
        self.assertEqual(c.to_dic()['value'], 4)
        self.assertEqual(c.to_simple_dic(), {'const M': {'type': 'long', 'value': 4}})
        self.assertEqual(c.to_simple_dic(quiet=True), 'const long M = 4')

    def test_macro(self):
        """An expression made by macro expansion is evaluated.

        マクロ展開で現れる式も評価される。
        """
        g = load('#define N 3\n#define TWICE (N * 2)\nconst long M = TWICE + 1;\n'
                 'struct S { long a[TWICE]; };\n')
        self.assertEqual(g.const_by_name('M').value, 7)
        self.assertEqual(g.struct_by_name('S').member_by_name('a').type.size, 6)

    def test_errors(self):
        """An undefined name, a non-integer const, a division by zero or bad syntax is an error.

        未定義名・整数でない const・0 除算・構文の誤りはエラー。
        """
        for idl in ('const long X = N + 1;',
                    'const double D = 1.5; const long X = D;',
                    'const string S = "a"; const long X = S;',
                    'const long X = 1 / 0;',
                    'const long X = 1 % 0;',
                    'const long X = 1 +;',
                    'const long X = (1 + 2;',
                    'const long X = 1 2;',
                    'const long X = 08;',
                    'const long X = 1 << 64;',
                    'const long X = 1.5;',
                    'const long X = X;'):
            with self.subTest(idl):
                with self.assertRaises(exception.InvalidConstExpressionError):
                    load(idl)

    def test_error_is_syntax_error_with_line(self):
        """The error is an InvalidIDLSyntaxError with the line of the const.

        エラーは InvalidIDLSyntaxError で、const の行番号を持つ。
        """
        with self.assertRaises(exception.InvalidIDLSyntaxError) as cm:
            load('const long A = 1;\nconst long X = A + B;\n')
        self.assertEqual(cm.exception.line_number, 2)
        self.assertIn('"B" is not defined', str(cm.exception))


class ArraySizeExpressionTest(unittest.TestCase):
    """Category: Sequences, arrays and typedefs / カテゴリ: sequence・array・typedef

    Array sizes can be constant expressions (issue #130).
    配列サイズに定数式を使える(#130)。
    """

    def member_type(self, idl, member, struct='S'):
        return load(idl).struct_by_name(struct).member_by_name(member).type

    def test_issue_example(self):
        """long a[N*2]; with N = 3 is an array of 6.

        N = 3 のとき long a[N*2]; は要素数 6 の配列。
        """
        t = self.member_type('const long N = 3; struct S { long a[N*2]; };', 'a')
        self.assertEqual(t.size, 6)
        self.assertEqual(str(t), 'long[6]')

    def test_spaces_and_parentheses(self):
        """Spaces and parentheses inside [ ], also across lines.

        [ ] 内の空白と括弧(改行をまたいでも)。
        """
        t = self.member_type('const long N = 3;\nstruct S { long a[ (N + 1)\n * 2 ]; };', 'a')
        self.assertEqual(t.size, 8)

    def test_literal_expression(self):
        """An expression of literals only: long a[2*3];.

        リテラルだけの式: long a[2*3];。
        """
        self.assertEqual(self.member_type('struct S { long a[2*3]; };', 'a').size, 6)

    def test_multi_dimension_and_declarators(self):
        """Expressions in each dimension and in each of several declarators.

        各次元と複数の宣言子それぞれに式を書ける。
        """
        s = load('const long N = 2; struct S { long a[N + 1][N * 2], b[1 << N]; };').struct_by_name('S')
        a = s.member_by_name('a').type
        self.assertEqual((a.size, a.inner_type.size), (3, 4))
        self.assertEqual(str(a), 'long[3][4]')
        self.assertEqual(s.member_by_name('b').type.size, 4)

    def test_typedef(self):
        """typedef long A[N+1];.

        typedef long A[N+1];。
        """
        g = load('const long N = 3; typedef long A[N+1];')
        self.assertEqual(g.typedef_by_name('A').type.size, 4)

    def test_const_of_expression(self):
        """const long M = N*2; then long a[M];.

        const long M = N*2; のあと long a[M];。
        """
        t = self.member_type('const long N = 3; const long M = N*2; struct S { long a[M]; };', 'a')
        self.assertEqual(t.size, 6)

    def test_scoped_name(self):
        """A scoped constant name in an array size.

        配列サイズにスコープ付きの定数名。
        """
        g = load('module X { const long N = 3; }; module Y { struct S { long a[X::N + 1];'
                 ' long b[::X::N]; }; };')
        s = g.module_by_name('Y').struct_by_name('S')
        self.assertEqual(s.member_by_name('a').type.size, 4)
        self.assertEqual(s.member_by_name('b').type.size, 3)

    def test_union_and_valuetype(self):
        """Array members of unions and value types.

        union と valuetype の配列メンバー。
        """
        g = load('const long N = 2; union U switch (long) { case 1: long a[N * 3]; };'
                 ' valuetype V { public long b[N + N]; };')
        self.assertEqual(g.union_by_name('U').member_by_name('a').type.size, 6)
        self.assertEqual(g.valuetype_by_name('V').state_member_by_name('b').type.size, 4)

    def test_errors(self):
        """A size that is not a positive integer is an error.

        正の整数でないサイズはエラー。
        """
        for size in ('0', 'N - 3', '-1', 'UNKNOWN', 'N / 0', 'D', 'N +'):
            with self.subTest(size):
                with self.assertRaises(exception.InvalidConstExpressionError) as cm:
                    load('const long N = 3; const double D = 1.0; struct S { long a[%s]; };' % size)
                # Also an InvalidDataTypeException, as before issue #130
                self.assertIsInstance(cm.exception, exception.InvalidDataTypeException)
                self.assertIsInstance(cm.exception, exception.InvalidIDLSyntaxError)


class BoundExpressionTest(unittest.TestCase):
    """Category: Sequences, arrays and typedefs / カテゴリ: sequence・array・typedef

    Bounds of strings, sequences and maps can be constant expressions (issue #130).
    string・sequence・map の上限に定数式を使える(#130)。
    """

    def setUp(self):
        self.s = load('''
        module M {
          const long N = 3;
          struct S {
            string<N*2> a;
            wstring< N + 1 > b;
            sequence<long, N * 2> c;
            sequence<string<N>, N + 1> d;
            map<long, string, N * 4> e;
            string<(1 << 3)> f;
            sequence<long, (N << 1) + 1> g;
            sequence<sequence<long, N>> h;
          };
        };
        ''').module_by_name('M').struct_by_name('S')

    def bound(self, member):
        return self.s.member_by_name(member).type.bound

    def test_strings(self):
        """string<N*2> and wstring< N + 1 >.

        string<N*2> と wstring< N + 1 >。
        """
        self.assertEqual(self.bound('a'), 6)
        self.assertEqual(self.bound('b'), 4)
        self.assertEqual(str(self.s.member_by_name('a').type), 'string')

    def test_sequences(self):
        """sequence<long, N * 2> and a bounded element type.

        sequence<long, N * 2> と上限付きの要素型。
        """
        self.assertEqual(self.bound('c'), 6)
        d = self.s.member_by_name('d').type
        self.assertEqual(d.bound, 4)
        self.assertEqual(d.inner_type.bound, 3)
        self.assertEqual(self.s.member_by_name('h').type.inner_type.bound, 3)

    def test_map(self):
        """map<long, string, N * 4>.

        map<long, string, N * 4>。
        """
        self.assertEqual(self.bound('e'), 12)

    def test_shift_in_parentheses(self):
        """<< and >> in a bound are written in parentheses: string<(1 << 3)>.

        上限の << と >> は括弧の中に書く: string<(1 << 3)>。
        """
        self.assertEqual(self.bound('f'), 8)
        self.assertEqual(self.bound('g'), 7)

    def test_const_type(self):
        """A const of a bounded string type with an expression bound.

        上限が式の bounded string 型の const。
        """
        c = load('module M { const long N = 2; const string<N * 4> S = "x"; };'
                 ).module_by_name('M').const_by_name('S')
        self.assertEqual(c.type.bound, 8)

    def test_errors(self):
        """A bound that is not a positive integer is an error.

        正の整数でない上限はエラー。
        """
        for typ in ('string<N - 3>', 'sequence<long, 0>', 'sequence<long, UNKNOWN>',
                    'map<long, long, -N>', 'wstring<N / 0>'):
            with self.subTest(typ):
                with self.assertRaises(exception.InvalidConstExpressionError):
                    load('const long N = 3; struct S { %s a; };' % typ)


if __name__ == '__main__':
    unittest.main()
