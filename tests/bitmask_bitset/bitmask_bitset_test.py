"""IDL 4.2 bitmask / bitset support (issue #39)."""
import unittest
from idl_parser import parser
from idl_parser.exception import InvalidIDLSyntaxError, IDLCanNotFindException


def load(idl):
    return parser.IDLParser().load(idl)


IDL = '''
module M {
  const long WIDTH = 5;

  bitmask Plain { A, B, C };
  @bit_bound(8) bitmask Flags { F0, @position(4) F4, F5, @position(0x7) F7 };

  bitset Base { bitfield<3> kind; };
  bitset Header : Base {
    bitfield<1> a, b;
    bitfield<4>;
    bitfield< 8 , unsigned short > level;
    bitfield<WIDTH> width;
  };

  struct S {
    Flags flags;
    Header header;
    sequence<Plain> plains;
  };
};

module N {
  bitset Ext : M::Header { bitfield<2> extra; };
  struct T { M::Flags f; };
};
'''


class BitmaskTest(unittest.TestCase):

    def setUp(self):
        self.m = load(IDL).module_by_name('M')

    def test_default_positions_and_bound(self):
        b = self.m.bitmask_by_name('Plain')
        self.assertTrue(b.is_bitmask)
        self.assertEqual(b.full_path, 'M::Plain')
        self.assertEqual(b.bit_bound, 32)
        self.assertEqual([(v.name, v.position, v.value) for v in b.values],
                         [('A', 0, 1), ('B', 1, 2), ('C', 2, 4)])

    def test_bit_bound_and_position_annotations(self):
        b = self.m.bitmask_by_name('Flags')
        self.assertEqual(b.bit_bound, 8)
        self.assertEqual([(v.name, v.position) for v in b.values],
                         [('F0', 0), ('F4', 4), ('F5', 5), ('F7', 7)])
        self.assertEqual(b.value_by_name('F7').value, 0x80)

    def test_to_dic(self):
        d = self.m.bitmask_by_name('Flags').to_dic()
        self.assertEqual(d['bit_bound'], 8)
        self.assertEqual(d['values'][1], {'name': 'F4', 'classname': 'IDLBitValue', 'position': 4, 'value': 16,
                                          'annotations': [{'name': 'position', 'args': ['4'], 'params': {}}]})
        self.assertIn('bitmask Plain', self.m.to_simple_dic()['module M'][1])

    def test_errors(self):
        cases = {
            'position out of bit_bound': '@bit_bound(4) bitmask F { A, @position(4) B };',
            'implicit position out of bit_bound': '@bit_bound(2) bitmask F { A, B, C };',
            'duplicate position': 'bitmask F { A, @position(0) B };',
            'bit_bound too large': '@bit_bound(65) bitmask F { A };',
            'no semicolon': 'bitmask F { A, B } struct S { long x; };',
            'no closing brace': 'bitmask F { A, B ;',
        }
        for label, idl in cases.items():
            with self.subTest(label):
                with self.assertRaises(InvalidIDLSyntaxError):
                    load(idl)


class BitsetTest(unittest.TestCase):

    def setUp(self):
        self.g = load(IDL)
        self.m = self.g.module_by_name('M')

    def test_layout(self):
        h = self.m.bitset_by_name('Header')
        self.assertTrue(h.is_bitset)
        self.assertIs(h.base, self.m.bitset_by_name('Base'))
        # 3 (base) + 1 + 1 + 4 (unnamed) + 8 + 5
        self.assertEqual(h.bit_size, 22)
        self.assertEqual([(b.name, b.bits, b.type, b.position) for b in h.members],
                         [('kind', 3, 'octet', 0),
                          ('a', 1, 'boolean', 3),
                          ('b', 1, 'boolean', 4),
                          ('level', 8, 'unsigned short', 9),
                          ('width', 5, 'octet', 17)])
        self.assertEqual(h.bitfield_by_name('level').mask, 0xff << 9)
        # bitfields: own fields only, including the unnamed one
        self.assertEqual([b.name for b in h.bitfields], ['a', 'b', None, 'level', 'width'])

    def test_scoped_base_in_other_module(self):
        e = self.g.module_by_name('N').bitset_by_name('Ext')
        self.assertEqual(e.base.full_path, 'M::Header')
        self.assertEqual(e.bitfield_by_name('extra').position, 22)
        self.assertEqual(e.bit_size, 24)

    def test_to_dic(self):
        d = self.m.bitset_by_name('Header').to_dic()
        self.assertEqual(d['base'], 'M::Base')
        self.assertEqual(d['bit_size'], 22)
        self.assertEqual(len(d['bitfields']), 5)

    def test_errors(self):
        cases = {
            'more than 64 bits': 'bitset B { bitfield<60> a; bitfield<5> b; };',
            'size 0': 'bitset B { bitfield<0> a; };',
            'unknown size constant': 'bitset B { bitfield<UNKNOWN> a; };',
            'not a bitfield': 'bitset B { long a; };',
            'no semicolon after bitfield': 'bitset B { bitfield<1> a };',
            'no closing brace': 'bitset B { bitfield<1> a;',
        }
        for label, idl in cases.items():
            with self.subTest(label):
                with self.assertRaises(InvalidIDLSyntaxError):
                    load(idl)
        with self.assertRaises(IDLCanNotFindException):
            load('bitset B : Missing { bitfield<1> a; };')


class TypeResolutionTest(unittest.TestCase):

    def setUp(self):
        self.g = load(IDL)

    def test_struct_members(self):
        s = self.g.module_by_name('M').struct_by_name('S')
        self.assertTrue(s.member_by_name('flags').type.is_bitmask)
        self.assertEqual(s.member_by_name('flags').type.full_path, 'M::Flags')
        self.assertTrue(s.member_by_name('header').type.is_bitset)
        self.assertEqual(s.member_by_name('plains').type.inner_type.obj.full_path, 'M::Plain')

    def test_scoped_name_from_other_module(self):
        t = self.g.module_by_name('N').struct_by_name('T')
        self.assertEqual(t.member_by_name('f').type.full_path, 'M::Flags')

    def test_find_types(self):
        self.assertTrue(self.g.find_types('M::Header')[0].is_bitset)
        self.assertTrue(self.g.find_types('Flags')[0].is_bitmask)


if __name__ == '__main__':
    unittest.main()
