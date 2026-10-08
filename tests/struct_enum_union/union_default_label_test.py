"""Regression tests for issue #48.

IDLUnionMember.parse_blocks only removed leading "case <value> :" labels, so a
"default :" label was left in front of the member type. With a primitive type
the type name silently became "default : double"; with a user defined type the
load failed with InvalidDataTypeException. "default:" is now accepted (alone or
combined with "case" labels), the member is marked with IDLUnionMember.is_default
and the union exposes it as IDLUnion.default_member.
"""
import unittest
from idl_parser import parser
from idl_parser.exception import InvalidIDLSyntaxError


IDL = '''
module M {
  struct P { double x; };
  typedef sequence<P> PSeq;
  enum K { A, B, C };

  union Primitive switch (K) { case A: long a; default: double d; };
  union UserType switch (K) { case A: long a; default: PSeq ps; };
  union CaseAndDefault switch (K) { case A: long a; case B: default: PSeq ps; };
  union DefaultFirst switch (K) { default: case C: P p; case A: long a; };
  union DefaultOnly switch (long) { default: string s; };
  union NoDefault switch (K) { case A: long a; case B: double b; };
  union Annotated switch (long) { case 1: long a; @key default: @range(min=0, max=9) long d; };
  union Spaced switch (long) {
    case 1 :
      long a;
    default
      :
      long d;
  };
  union Bounded switch (long) { case 1: long a; default: string<8> s; };
  union Array switch (long) { case 1: long a; default: double m[3]; };
};
'''


def load(text):
    return parser.IDLParser().load(text)


class UnionDefaultTest(unittest.TestCase):
    """Category: Structs, enums and unions / カテゴリ: struct・enum・union

    Union members with a "default:" label (issue #48).
    "default:" ラベルを持つ union メンバー(#48)。
    """

    @classmethod
    def setUpClass(cls):
        cls.m = load(IDL).module_by_name('M')

    def union(self, name):
        return self.m.union_by_name(name)

    def test_primitive_type(self):
        """Union default: "default :" does not leak into the type name of a primitive member.

        union の default: プリミティブ型メンバーの型名に "default :" が混入しない。
        """
        d = self.union('Primitive').member_by_name('d')
        self.assertEqual(d.type.name, 'double')
        self.assertTrue(d.type.is_primitive)
        self.assertTrue(d.is_default)
        self.assertEqual(d.descriminator_value_associations, [])

    def test_user_defined_type(self):
        """Union default: a member of a user-defined type is resolved.

        union の default: ユーザー定義型メンバーが解決される。
        """
        ps = self.union('UserType').member_by_name('ps')
        self.assertTrue(ps.type.is_typedef)
        self.assertEqual(ps.type.full_path, 'M::PSeq')
        self.assertTrue(ps.is_default)

    def test_case_members_are_not_default(self):
        """Members with case labels have is_default false.

        case ラベルのメンバーは is_default が偽。
        """
        a = self.union('Primitive').member_by_name('a')
        self.assertFalse(a.is_default)
        self.assertEqual(a.descriminator_value_associations, ['A'])

    def test_case_and_default(self):
        """A member with both "case B:" and "default:".

        case B: と default: の両方を持つメンバー。
        """
        ps = self.union('CaseAndDefault').member_by_name('ps')
        self.assertEqual(ps.descriminator_value_associations, ['B'])
        self.assertTrue(ps.is_default)
        self.assertEqual(ps.type.full_path, 'M::PSeq')

    def test_default_before_case(self):
        """A member with "default:" written before its case label.

        default: を case より先に書いたメンバー。
        """
        u = self.union('DefaultFirst')
        p = u.member_by_name('p')
        self.assertEqual(p.descriminator_value_associations, ['C'])
        self.assertTrue(p.is_default)
        self.assertTrue(p.type.is_struct)
        self.assertEqual([m.name for m in u.members], ['p', 'a'])

    def test_default_only(self):
        """A union with only a default member.

        default メンバーだけの union。
        """
        s = self.union('DefaultOnly').member_by_name('s')
        self.assertTrue(s.is_default)
        self.assertEqual(s.type.name, 'string')

    def test_default_member(self):
        """The default_member property (None when there is none).

        default_member プロパティ(なければ None)。
        """
        self.assertEqual(self.union('Primitive').default_member.name, 'd')
        self.assertEqual(self.union('CaseAndDefault').default_member.name, 'ps')
        self.assertIsNone(self.union('NoDefault').default_member)

    def test_annotations(self):
        """A default member with annotations.

        アノテーション付きの default メンバー。
        """
        d = self.union('Annotated').member_by_name('d')
        self.assertTrue(d.is_default)
        self.assertEqual(d.type.name, 'long')
        self.assertIsNotNone(d.annotation_by_name('key'))
        self.assertIsNotNone(d.annotation_by_name('range'))

    def test_whitespace(self):
        """Spacing variants of "default :".

        default : の空白の違い。
        """
        d = self.union('Spaced').member_by_name('d')
        self.assertTrue(d.is_default)
        self.assertEqual(d.type.name, 'long')

    def test_bounded_string_and_array(self):
        """Default members that are a bounded string or an array.

        default メンバーが上限付き string や配列。
        """
        self.assertTrue(self.union('Bounded').member_by_name('s').is_default)
        m = self.union('Array').member_by_name('m')
        self.assertTrue(m.is_default)
        self.assertTrue(m.type.is_array)

    def test_to_dic(self):
        """is_default and case labels in to_dic().

        to_dic() の is_default と case ラベル。
        """
        dic = self.union('CaseAndDefault').to_dic()
        a, ps = dic['members']
        self.assertEqual((a['name'], a['is_default']), ('a', False))
        self.assertEqual(ps['descriminator_value_associations'], ['B'])
        self.assertTrue(ps['is_default'])
        self.assertEqual(ps['type'], 'PSeq')

    def test_to_simple_dic(self):
        """The type name of the default member in to_simple_dic().

        to_simple_dic() で default メンバーの型名。
        """
        self.assertEqual(self.union('Primitive').to_simple_dic(),
                         {'union Primitive': [{'a': 'long'}, {'d': 'double'}]})


class UnionLabelErrorTest(unittest.TestCase):
    """Category: Structs, enums and unions / カテゴリ: struct・enum・union

    Malformed union labels are errors (issue #48).
    不正な union ラベルはエラーになる(#48)。
    """

    def test_two_default_members(self):
        """Two default members are an error.

        default メンバーが2つあるとエラー。
        """
        with self.assertRaises(InvalidIDLSyntaxError):
            load('module M { union U switch (long) { default: long a; default: long b; }; };')

    def test_default_without_colon(self):
        """default without ":" is an error.

        default の後に : がないとエラー。
        """
        with self.assertRaises(InvalidIDLSyntaxError):
            load('module M { union U switch (long) { default long a; }; };')

    def test_case_without_colon(self):
        """A case value without ":" is an error.

        case 値の後に : がないとエラー。
        """
        with self.assertRaises(InvalidIDLSyntaxError):
            load('module M { union U switch (long) { case 1 long a; }; };')


if __name__ == '__main__':
    unittest.main()
