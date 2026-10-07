"""generate_constructor_python() with struct / enum / typedef / bitmask / bitset members (issue #43)."""
import unittest

from idl_parser import parser

IDL = '''
enum G { G1, G2 };
struct Top { G g; };
module M {
  enum E { E1, E2 };
  bitmask F { F1, F2 };
  bitset BS { bitfield<3> b; };
  struct A { long y; };
  typedef A AAlias;
  typedef sequence<double> DSeq;
  struct S { long x; A a; E e; F f; BS bs; AAlias aa; DSeq d; sequence<A> sa; long arr[2]; };
  struct Empty {};
};
'''


class GenerateConstructorPythonTest(unittest.TestCase):

    def setUp(self):
        self.p = parser.IDLParser()
        self.g = self.p.load(IDL)
        self.m = self.g.module_by_name('M')

    def test_struct_with_non_primitive_members(self):
        self.assertEqual(self.p.generate_constructor_python(self.m.struct_by_name('S')),
                         'M.S(0, M.A(0), M.E1, 0, 0, M.A(0), [], [], [0, 0])')

    def test_enum_at_global_scope(self):
        self.assertEqual(self.p.generate_constructor_python(self.g.struct_by_name('Top')),
                         'Top(G1)')

    def test_empty_struct(self):
        self.assertEqual(self.p.generate_constructor_python(self.m.struct_by_name('Empty')),
                         'M.Empty()')


if __name__ == '__main__':
    unittest.main()
