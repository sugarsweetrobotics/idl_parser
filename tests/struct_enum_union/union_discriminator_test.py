"""Tests for issue #136: the discriminator type and the label values of a union.

The discriminator was kept as the name written in "switch ( )"
(descriminator_kind), and the case labels as the text written (["N+1"],
["T::RED"], ["'a'"], ["TRUE"]), so a generator could not know the size of
the discriminator or the value of each label. A discriminator of several
words ("unsigned long") was a syntax error. Now:

- IDLUnion.discriminator_type is the type node (IDLPrimitive or IDLEnum,
  typedefs followed), and several words are accepted;
- IDLUnionMember.labels are the values evaluated with that type: int,
  one-character str, bool or IDLEnumValue;
- a label used twice, a label that is not a value of the discriminator
  type, and a discriminator that can not be switched on are errors.
"""
import unittest

from idl_parser import parser
from idl_parser.exception import (InvalidIDLSyntaxError, InvalidDataTypeException,
                                  InvalidConstExpressionError)


IDL = r'''
module T {
  enum Color { RED, GREEN, BLUE };
  const long N = 3;
  const char CA = 'z';
  const boolean YES = TRUE;
  typedef Color CT;
  typedef CT CT2;
  typedef long LT;
  union U1 switch (long) { case 1: long a; case -2: case 0x10: short b; default: double c; };
  union U2 switch (char) { case 'a': long x; case '\n': case CA: short z; default: double y; };
  union U3 switch (boolean) { case TRUE: long t; case FALSE: short f; };
  union U4 switch (long) { case N: long t; case N+1: short s; case N * 2 - (1 << 2): octet o; };
  union U5 switch (CT) { case T::RED: long t; case GREEN: short g; case ::T::BLUE: octet b; };
  union U6 switch (Color) { case Color::RED: long t; };
  union U7 switch (LT) { case 5: long t; };
  union U8 switch (CT2) { case BLUE: long t; };
  union U9 switch (wchar) { case L'w': long t; case 'v': short v; };
  union U10 switch (boolean) { case YES: long t; };
};
module Multi {
  union UL switch (unsigned long) { case 4294967295: long a; };
  union LL switch (long long) { case -9223372036854775808: long a; };
  union US switch (unsigned short) { case 1: long a; };
  union ULL switch (unsigned long long) { case 18446744073709551615: long a; };
  union S switch (short) { case 1: long a; };
  union O switch (octet) { case 255: long a; };
  union I8 switch (int8) { case -128: long a; };
  union U32 switch (uint32) { case 1: long a; };
};
'''


class UnionDiscriminatorTest(unittest.TestCase):
    """Category: Structs, enums and unions / カテゴリ: struct・enum・union

    The discriminator type and label values of a union (issue #136).
    union の判別子の型と case ラベルの値(#136)。
    """

    @classmethod
    def setUpClass(cls):
        cls.g = parser.IDLParser().load(IDL)
        cls.t = cls.g.module_by_name('T')
        cls.multi = cls.g.module_by_name('Multi')

    def union(self, name):
        return self.t.union_by_name(name)

    def labels(self, union):
        return [m.labels for m in union.members]

    def test_integer_labels(self):
        """Integer labels are ints; default has none. / 整数のラベルは int、default はラベルを持たない。"""
        u = self.union('U1')
        self.assertEqual(self.labels(u), [[1], [-2, 16], []])
        self.assertTrue(u.member_by_name('c').is_default)
        self.assertEqual(u.member_by_name('b').descriminator_value_associations, ['-2', '0x10'])

    def test_constant_expression_labels(self):
        """Labels may be constant expressions. / ラベルは定数式でもよい。"""
        u = self.union('U4')
        self.assertEqual(self.labels(u), [[3], [4], [2]])
        self.assertEqual(u.member_by_name('s').descriminator_value_associations, ['N+1'])

    def test_char_labels(self):
        """char labels are one-character strings, escapes and constants included. / char のラベルは 1 文字の str(エスケープと定数を含む)。"""
        self.assertEqual(self.labels(self.union('U2')), [['a'], ['\n', 'z'], []])
        self.assertEqual(self.labels(self.union('U9')), [['w'], ['v']])

    def test_boolean_labels(self):
        """boolean labels are bools, constants included. / boolean のラベルは bool(定数を含む)。"""
        self.assertEqual(self.labels(self.union('U3')), [[True], [False]])
        self.assertEqual(self.labels(self.union('U10')), [[True]])

    def test_enum_labels(self):
        """enum labels are IDLEnumValue nodes, however they are scoped. / enum のラベルはスコープの書き方によらず IDLEnumValue。"""
        color = self.t.enum_by_name('Color')
        self.assertEqual(self.labels(self.union('U5')), [[v] for v in color.values])
        self.assertIs(self.union('U5').members[0].labels[0], color.value_by_name('RED'))
        self.assertIs(self.union('U6').members[0].labels[0], color.value_by_name('RED'))
        self.assertIs(self.union('U8').members[0].labels[0], color.value_by_name('BLUE'))

    def test_discriminator_type(self):
        """The discriminator type is resolved, typedefs followed. / 判別子の型は typedef をたどって解決される。"""
        color = self.t.enum_by_name('Color')
        self.assertIs(self.union('U5').discriminator_type, color)
        self.assertIs(self.union('U8').discriminator_type, color)
        self.assertEqual(self.union('U5').descriminator_kind, 'CT')
        long_ = self.union('U7').discriminator_type
        self.assertTrue(long_.is_primitive)
        self.assertEqual(long_.name, 'long')
        self.assertEqual(self.union('U2').discriminator_type.name, 'char')
        self.assertEqual(self.union('U3').discriminator_type.name, 'boolean')

    def test_multi_word_discriminator(self):
        """Discriminators of several words are read. / 複数語の判別子が読める。"""
        expected = {'UL': ('unsigned long', 4294967295),
                    'LL': ('long long', -9223372036854775808),
                    'US': ('unsigned short', 1),
                    'ULL': ('unsigned long long', 18446744073709551615),
                    'S': ('short', 1), 'O': ('octet', 255),
                    'I8': ('int8', -128), 'U32': ('uint32', 1)}
        for name, (kind, label) in expected.items():
            with self.subTest(name):
                u = self.multi.union_by_name(name)
                self.assertEqual(u.descriminator_kind, kind)
                self.assertEqual(u.discriminator_type.name, kind)
                self.assertEqual(u.members[0].labels, [label])


class UnionLabelErrorTest(unittest.TestCase):
    """Category: Structs, enums and unions / カテゴリ: struct・enum・union

    Invalid discriminators and labels are errors (issue #136).
    不正な判別子とラベルはエラー(#136)。
    """

    def assertError(self, idl, error=InvalidIDLSyntaxError):
        with self.assertRaises(error):
            parser.IDLParser().load(idl)

    def test_duplicate_labels(self):
        """A label used twice. / 同じラベルを 2 回使う。"""
        self.assertError('union U switch (long) { case 1: long a; case 1: short b; };')
        self.assertError('union U switch (long) { case 1: case 1: long a; };')
        self.assertError('const long N = 2; union U switch (long) { case 2: long a; case N: short b; };')
        self.assertError("union U switch (char) { case 'a': long a; case 'a': short b; };")
        self.assertError('enum E { A, B }; union U switch (E) { case A: long a; case E::A: short b; };')
        self.assertError('union U switch (boolean) { case TRUE: long a; case TRUE: short b; };')

    def test_label_not_of_discriminator_type(self):
        """A label that is not a value of the discriminator type. / 判別子の型の値でないラベル。"""
        self.assertError('enum E { A }; union U switch (E) { case X: long a; };', InvalidConstExpressionError)
        self.assertError('enum E { A }; enum F { X }; union U switch (E) { case X: long a; };')
        self.assertError("union U switch (long) { case 'a': long a; };")
        self.assertError('union U switch (char) { case 1: long a; };')
        self.assertError("union U switch (char) { case 'ab': long a; };")
        self.assertError('union U switch (boolean) { case 1: long a; };')
        self.assertError('union U switch (long) { case UNKNOWN: long a; };')

    def test_label_out_of_range(self):
        """An integer label out of the range of the discriminator type. / 判別子の型の範囲外の整数ラベル。"""
        self.assertError('union U switch (octet) { case 256: long a; };')
        self.assertError('union U switch (unsigned long) { case -1: long a; };')
        self.assertError('union U switch (short) { case 32768: long a; };')

    def test_invalid_discriminator(self):
        """A discriminator that can not be switched on, or is not defined. / switch できない型、未定義の判別子。"""
        self.assertError('union U switch (string) { case 1: long a; };')
        self.assertError('union U switch (double) { case 1: long a; };')
        self.assertError('struct S { long a; }; union U switch (S) { case 1: long a; };')
        self.assertError('union U switch (Unknown) { case 1: long a; };', InvalidDataTypeException)
        self.assertError('union U switch () { case 1: long a; };')

    def test_same_value_in_different_types_is_not_duplicate(self):
        """Different unions may use the same labels. / 別の union では同じラベルを使える。"""
        g = parser.IDLParser().load('union A switch (long) { case 1: long a; };\n'
                                    'union B switch (long) { case 1: long b; };')
        self.assertEqual([u.members[0].labels for u in g.unions], [[1], [1]])


if __name__ == '__main__':
    unittest.main()
