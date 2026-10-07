"""Cover to_simple_dic(member_only=True)."""
import unittest

from idl_parser import parser


class SimpleDicMemberOnlyTest(unittest.TestCase):

    def setUp(self):
        idl = '''
module M {
  enum K { A, B };
  struct S { long x; double y; };
  union U switch (K) { case A: long a; case B: double b; };
};
'''
        self.m = parser.IDLParser().load(idl).module_by_name('M')

    def test_struct_member_only(self):
        s = self.m.struct_by_name('S')
        self.assertEqual(list(s.to_simple_dic(member_only=True)),
                         [{'x': 'long'}, {'y': 'double'}])

    def test_union_member_only(self):
        u = self.m.union_by_name('U')
        # Must not raise TypeError ('dict_values' object is not subscriptable)
        self.assertEqual(len(list(u.to_simple_dic(member_only=True))), 2)


if __name__ == '__main__':
    unittest.main()
