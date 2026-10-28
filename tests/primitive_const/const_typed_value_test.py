"""Tests for issue #137: the values of constants of every type are typed.

Only the value of an integer constant was evaluated; the others were the
text as written ('3.14', '1.0/3', '"a" "b"', "'x'", 'TRUE', 'A::Y'), and
the type of "const fixed F = 1.25d;" raised IndexError. Now the value is
evaluated with the type of the constant: float, decimal.Decimal, str, bool
or IDLEnumValue, and a value out of the range of its type is an error.
"""
import decimal
import unittest

from idl_parser import parser
from idl_parser.exception import InvalidConstExpressionError, InvalidIDLSyntaxError


IDL = r'''
const double PI = 3.14;
const float F = 1.0/3;
const double E = 1e3;
const double D2 = PI * 2 + 1;
const long double LD = -.5;
const string S = "a" "b";
const string S2 = "a\"b\n\x41";
const string S3 = S "c";
const string<3> SB = "abc";
const char C = 'x';
const char C2 = '\'';
const char C3 = C;
const wchar WC = L'w';
const wstring WS = L"w" L"z";
const boolean B = TRUE;
const boolean B2 = FALSE;
const boolean B3 = B;
const fixed FX = 1.25d;
const fixed FX2 = FX * 2;
const fixed FX3 = 3;
const octet O = 255;
typedef double Real;
typedef Real Real2;
const Real2 R = 2.5;
typedef string Name;
const Name N = "n";
module A { enum E { X, Y }; };
module B {
  const A::E C = A::Y;
  const A::E C2 = C;
  const A::E C3 = ::A::X;
};
'''


class ConstTypedValueTest(unittest.TestCase):
    """Category: Primitive types and constants / カテゴリ: プリミティブ型・const

    Values of constants of every type are typed (issue #137).
    どの型の定数の値も型付きで評価される(#137)。
    """

    @classmethod
    def setUpClass(cls):
        cls.g = parser.IDLParser().load(IDL)

    def value(self, name, scope=None):
        return (scope or self.g).const_by_name(name).value

    def test_floating_point(self):
        """Floating-point values are floats, expressions and constants included. / 浮動小数点は float(式と定数を含む)。"""
        self.assertEqual(self.value('PI'), 3.14)
        self.assertAlmostEqual(self.value('F'), 1.0 / 3)
        self.assertEqual(self.value('E'), 1000.0)
        self.assertAlmostEqual(self.value('D2'), 7.28)
        self.assertEqual(self.value('LD'), -0.5)
        self.assertIsInstance(self.value('E'), float)
        self.assertEqual(self.value('R'), 2.5)

    def test_string(self):
        """Strings lose their quotes, escapes are replaced and literals are joined. / 文字列は引用符を外し、エスケープを解釈し、連結する。"""
        self.assertEqual(self.value('S'), 'ab')
        self.assertEqual(self.value('S2'), 'a"b\nA')
        self.assertEqual(self.value('S3'), 'abc')
        self.assertEqual(self.value('SB'), 'abc')
        self.assertEqual(self.value('WS'), 'wz')
        self.assertEqual(self.value('N'), 'n')
        self.assertEqual(self.g.const_by_name('S').value_string, '"a" "b"')

    def test_char(self):
        """Characters are strings of one character. / 文字は 1 文字の str。"""
        self.assertEqual(self.value('C'), 'x')
        self.assertEqual(self.value('C2'), "'")
        self.assertEqual(self.value('C3'), 'x')
        self.assertEqual(self.value('WC'), 'w')

    def test_boolean(self):
        """Booleans are bools. / boolean は bool。"""
        self.assertIs(self.value('B'), True)
        self.assertIs(self.value('B2'), False)
        self.assertIs(self.value('B3'), True)

    def test_fixed(self):
        """Fixed-point values are Decimals, and the type is an IDLFixed. / fixed は Decimal で、type は IDLFixed。"""
        self.assertEqual(self.value('FX'), decimal.Decimal('1.25'))
        self.assertEqual(self.value('FX2'), decimal.Decimal('2.50'))
        self.assertEqual(self.value('FX3'), decimal.Decimal(3))
        t = self.g.const_by_name('FX').type
        self.assertTrue(t.is_fixed)
        self.assertEqual((t.digits, t.scale), (3, 2))
        self.assertEqual(self.g.const_by_name('FX').to_dic()['value'], '1.25')

    def test_enum(self):
        """Enum values are the IDLEnumValue nodes. / enum の値は IDLEnumValue。"""
        e = self.g.module_by_name('A').enum_by_name('E')
        b = self.g.module_by_name('B')
        self.assertIs(self.value('C', b), e.value_by_name('Y'))
        self.assertIs(self.value('C2', b), e.value_by_name('Y'))
        self.assertIs(self.value('C3', b), e.value_by_name('X'))
        self.assertEqual(b.const_by_name('C').to_dic()['value'], 'A::Y')

    def test_integer_unchanged(self):
        """Integer values are ints as before. / 整数はこれまでどおり int。"""
        self.assertEqual(self.value('O'), 255)
        self.assertTrue(self.g.const_by_name('O').is_integer)
        self.assertFalse(self.g.const_by_name('PI').is_integer)
        self.assertIsNone(self.g.const_by_name('PI').int_value)

    def test_simple_dic(self):
        """to_simple_dic(quiet=True) keeps the quotes of literals. / to_simple_dic(quiet=True) はリテラルの引用符を残す。"""
        self.assertEqual(self.g.const_by_name('S').to_simple_dic(quiet=True), 'const string S = "a" "b"')
        self.assertEqual(self.g.const_by_name('PI').to_simple_dic(), {'const PI': {'type': 'double', 'value': 3.14}})


class ConstValueErrorTest(unittest.TestCase):
    """Category: Primitive types and constants / カテゴリ: プリミティブ型・const

    Values that are not of the type or out of its range are errors (issue #137).
    型に合わない値や範囲外の値はエラー(#137)。
    """

    def assertError(self, idl):
        with self.assertRaises(InvalidConstExpressionError) as cm:
            parser.IDLParser().load(idl)
        self.assertIsInstance(cm.exception, InvalidIDLSyntaxError)

    def test_integer_out_of_range(self):
        """Integers out of the range of their type. / 型の範囲外の整数。"""
        self.assertError('const octet O = 300;')
        self.assertError('const short S = 32768;')
        self.assertError('const unsigned long U = -1;')
        self.assertError('const int8 I = 128;')
        self.assertError('const long long L = 9223372036854775808;')

    def test_float_errors(self):
        """Floating-point values out of range, or with integer-only operators. / 範囲外の浮動小数点、整数専用の演算子。"""
        self.assertError('const float F = 1e39;')
        self.assertError('const double D = 1 << 2;')
        self.assertError('const double D = 1.0 / 0;')
        self.assertError('const double D = "a";')
        self.assertError('const long L = 1.5;')

    def test_fixed_errors(self):
        """More than 31 digits. / 31 桁を超える。"""
        self.assertError('const fixed F = 12345678901234567890123456789012d;')

    def test_other_errors(self):
        """Strings, chars, booleans and enums that are not of the type. / 型に合わない文字列・文字・boolean・enum。"""
        self.assertError('const string S = 1;')
        self.assertError('const string<2> S = "abc";')
        self.assertError("const char C = 'ab';")
        self.assertError('const char C = "a";')
        self.assertError('const boolean B = 1;')
        self.assertError('enum E { X }; enum F { Y }; const E C = Y;')
        self.assertError('enum E { X }; const E C = Z;')


if __name__ == '__main__':
    unittest.main()
