"""@value(n) sets the value of an enumerator (issue #122)."""
import unittest
from idl_parser import parser
from idl_parser.exception import InvalidIDLSyntaxError


def load(idl):
    return parser.IDLParser().load(idl)


def values(enum):
    return [(v.name, v.value) for v in enum.values]


class EnumValueTest(unittest.TestCase):
    """Category: Structs, enums and unions / カテゴリ: struct・enum・union

    @value(n) on enumerators (issue #122).
    列挙子に付けた @value(n)(#122)。
    """

    def test_issue_example(self):
        """@value(3) A, B gives A = 3 and B = 4.

        @value(3) A, B で A = 3、B = 4 になる。
        """
        g = load('enum E { @value(3) A, B };')
        self.assertEqual(values(g.enums[0]), [('A', 3), ('B', 4)])

    def test_without_value(self):
        """Without @value the values are 0, 1, 2, ... in declaration order.

        @value が無ければ書いた順に 0, 1, 2, … になる。
        """
        g = load('enum E { A, B, C };')
        self.assertEqual(values(g.enums[0]), [('A', 0), ('B', 1), ('C', 2)])

    def test_following_value(self):
        """An enumerator without @value takes the previous value plus 1.

        @value の無い列挙子は直前の値 + 1 になる。
        """
        g = load('enum E { A, @value(10) B, C, @value(5) D, E2 };')
        self.assertEqual(values(g.enums[0]),
                         [('A', 0), ('B', 10), ('C', 11), ('D', 5), ('E2', 6)])

    def test_literals(self):
        """Hex, octal, negative and value= forms are read as integers.

        16進・8進・負の数・value= の形も整数として読める。
        """
        g = load('enum E { @value(0x10) A, @value(010) B, @value(-2) C, D, @value(value=7) F };')
        self.assertEqual(values(g.enums[0]),
                         [('A', 16), ('B', 8), ('C', -2), ('D', -1), ('F', 7)])

    def test_const(self):
        """@value can name a const, relative or absolute.

        @value に const の名前(相対・絶対)を書ける。
        """
        g = load('''
const long TOP = 50;
module M {
  const long BASE = 100;
  module N { const long OFFSET = 7; enum E { @value(BASE) A, B, @value(::TOP) C, @value(M::N::OFFSET) D }; };
};
''')
        e = g.module_by_name('M').module_by_name('N').enum_by_name('E')
        self.assertEqual(values(e), [('A', 100), ('B', 101), ('C', 50), ('D', 7)])

    def test_const_in_scope(self):
        """A const in an enclosing module is found by its scoped name.

        外側のモジュールの const をスコープ付きの名前で参照できる。
        """
        g = load('module M { const long X = 3; }; enum E { @value(M::X) A, B };')
        self.assertEqual(values(g.enums[0]), [('A', 3), ('B', 4)])

    def test_annotation_kept(self):
        """The @value annotation itself is still kept on the enumerator.

        @value アノテーション自体も列挙子に残る。
        """
        v = load('enum E { @value(3) A };').enums[0].values[0]
        self.assertEqual(v.annotation_by_name('value').value, '3')

    def test_output(self):
        """to_dic() and to_simple_dic() show the @value values.

        to_dic() と to_simple_dic() に @value の値が出る。
        """
        e = load('enum E { @value(3) A, B };').enums[0]
        self.assertEqual(e.to_simple_dic(), {'enum E': [{'A': 3}, {'B': 4}]})
        self.assertEqual([d['value'] for d in e.to_dic()['values']], [3, 4])

    def test_in_interface(self):
        """@value works for an enum inside an interface too.

        interface の中の enum でも @value が使える。
        """
        g = load('interface I { enum E { @value(7) A, B }; };')
        self.assertEqual(values(g.interfaces[0].enums[0]), [('A', 7), ('B', 8)])

    def test_duplicate_is_error(self):
        """A value used twice is an InvalidIDLSyntaxError, also when it is implicit.

        同じ値が二度使われると(暗黙の値でも)InvalidIDLSyntaxError になる。
        """
        with self.assertRaisesRegex(InvalidIDLSyntaxError, 'already used by "A"'):
            load('enum E { @value(1) A, @value(1) B };')
        with self.assertRaisesRegex(InvalidIDLSyntaxError, 'already used by "B"'):
            load('enum E { A, B, @value(1) C };')
        with self.assertRaisesRegex(InvalidIDLSyntaxError, 'already used by "B"'):
            load('enum E { @value(1) A, @value(5) B, @value(4) C, D };')

    def test_invalid_value_is_error(self):
        """A @value that is not an integer or a known const is an InvalidIDLSyntaxError.

        整数でも既知の const でもない @value は InvalidIDLSyntaxError になる。
        """
        for idl in ('enum E { @value(UNKNOWN) A };',
                    'enum E { @value("1") A };',
                    'enum E { @value A };',
                    'enum E { @value(1, 2) A };'):
            with self.subTest(idl=idl):
                with self.assertRaisesRegex(InvalidIDLSyntaxError, 'Invalid @value'):
                    load(idl)

    def test_out_of_range_is_error(self):
        """A value outside 32-bit signed integers is an InvalidIDLSyntaxError.

        32ビット符号付き整数の範囲外の値は InvalidIDLSyntaxError になる。
        """
        load('enum E { @value(-2147483648) A, @value(2147483647) B };')
        with self.assertRaisesRegex(InvalidIDLSyntaxError, 'out of range'):
            load('enum E { @value(2147483648) A };')
        with self.assertRaisesRegex(InvalidIDLSyntaxError, 'out of range'):
            load('enum E { @value(2147483647) A, B };')

    def test_error_line_number(self):
        """The error tells the line of the enumerator.

        エラーには列挙子の行番号が入る。
        """
        with self.assertRaisesRegex(InvalidIDLSyntaxError, 'line 3'):
            load('enum E {\n  @value(1) A,\n  @value(1) B\n};')


if __name__ == '__main__':
    unittest.main()
