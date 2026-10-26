"""Tests for issue #117: several declarators in one declaration.

"struct S { long a, b, c[2]; };" and "typedef long A, B[3];" were read as
one member / typedef named after the last declarator, with the others mixed
into its type name ('long a , b ,[2]'). Each declarator now becomes its own
member or typedef. A union member can have only one declarator, so
"case 1: long a, b;" is an error.
"""
import unittest
from idl_parser import parser
from idl_parser.exception import InvalidIDLSyntaxError


IDL = '''
module M {
  struct S { long a, b, c[2]; };
  struct T { @key string k1, k2; sequence<long, 10> s1, s2; long g [ 2 ] [3], h; };
  typedef long A, B[3];
  exception E { string m1, m2; };
  valuetype V { public long x, y[2]; };
};
'''


def members(s):
    return [(m.name, m.type.name) for m in s.members]


class MultipleDeclaratorsTest(unittest.TestCase):
    """Category: Structs, enums and unions / カテゴリ: struct・enum・union

    Several declarators in one declaration (issue #117).
    1 つの宣言に並べた複数の宣言子(#117)。
    """

    @classmethod
    def setUpClass(cls):
        cls.m = parser.IDLParser().load(IDL).module_by_name('M')

    def test_struct_members(self):
        """Every name of "long a, b, c[2];" is a member, each of type long.
        "long a, b, c[2];" の名前がそれぞれ long 型のメンバーになる。"""
        self.assertEqual(members(self.m.struct_by_name('S')),
                         [('a', 'long'), ('b', 'long'), ('c', 'long [2]')])

    def test_annotations_template_and_spaced_arrays(self):
        """Annotations apply to every declarator, a "," in "< >" does not split,
        and spaced array sizes are kept.
        アノテーションは全宣言子に付き、"< >" 内の "," では分割せず、空白入りの配列サイズも保たれる。"""
        t = self.m.struct_by_name('T')
        self.assertEqual([m.name for m in t.members], ['k1', 'k2', 's1', 's2', 'g', 'h'])
        self.assertEqual(t.keys, ['k1', 'k2'])
        self.assertTrue(t.member_by_name('s2').type.is_sequence)
        self.assertEqual(t.member_by_name('g').type.name, 'long [2][3]')
        self.assertEqual(t.member_by_name('h').type.name, 'long')

    def test_typedefs(self):
        """"typedef long A, B[3];" defines A and B.
        "typedef long A, B[3];" で A と B が定義される。"""
        self.assertEqual([(t.name, t.type.name) for t in self.m.typedefs],
                         [('A', 'long'), ('B', 'long [3]')])

    def test_exception_members(self):
        """Exception members are split like struct members.
        exception のメンバーも struct と同じく分かれる。"""
        self.assertEqual(members(self.m.exception_by_name('E')),
                         [('m1', 'string'), ('m2', 'string')])

    def test_state_members(self):
        """Value type state members are split as well.
        valuetype の state member も分かれる。"""
        v = self.m.valuetype_by_name('V')
        self.assertEqual([(s.name, s.type.name) for s in v.state_members],
                         [('x', 'long'), ('y', 'long [2]')])

    def test_union_member_with_two_names_is_an_error(self):
        """A union member can have only one name.
        union のメンバーには名前を 1 つしか書けない。"""
        with self.assertRaises(InvalidIDLSyntaxError):
            parser.IDLParser().load('union U switch (long) { case 1: long a, b; };')

    def test_invalid_declarators(self):
        """A missing name or type is an error, not a broken member.
        名前や型が欠けていれば、壊れたメンバーではなくエラーになる。"""
        for idl in ['struct S { long a, ; };',
                    'struct S { long a, long b; };',
                    'typedef long , A;',
                    'typedef A;']:
            with self.subTest(idl=idl):
                with self.assertRaises(InvalidIDLSyntaxError):
                    parser.IDLParser().load(idl)


if __name__ == '__main__':
    unittest.main()
