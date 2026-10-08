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
    """Category: Bitmasks and bitsets / カテゴリ: bitmask・bitset

    IDL 4.2 bitmask: bit positions, bit_bound, output and errors.
    IDL 4.2 の bitmask: ビット位置・bit_bound・出力・エラー。
    """

    def setUp(self):
        self.m = load(IDL).module_by_name('M')

    def test_default_positions_and_bound(self):
        """Bitmask values get default positions 0, 1, 2…, matching values, and bit_bound 32.

        bitmask の既定ビット位置(0,1,2…)・値・bit_bound=32。
        """
        b = self.m.bitmask_by_name('Plain')
        self.assertTrue(b.is_bitmask)
        self.assertEqual(b.full_path, 'M::Plain')
        self.assertEqual(b.bit_bound, 32)
        self.assertEqual([(v.name, v.position, v.value) for v in b.values],
                         [('A', 0, 1), ('B', 1, 2), ('C', 2, 4)])

    def test_bit_bound_and_position_annotations(self):
        """@bit_bound and @position change the bit positions and values.

        @bit_bound と @position で位置・値が変わる。
        """
        b = self.m.bitmask_by_name('Flags')
        self.assertEqual(b.bit_bound, 8)
        self.assertEqual([(v.name, v.position) for v in b.values],
                         [('F0', 0), ('F4', 4), ('F5', 5), ('F7', 7)])
        self.assertEqual(b.value_by_name('F7').value, 0x80)

    def test_to_dic(self):
        """to_dic() / to_simple_dic() output of a bitmask.

        bitmask の to_dic()/to_simple_dic() 出力。
        """
        d = self.m.bitmask_by_name('Flags').to_dic()
        self.assertEqual(d['bit_bound'], 8)
        self.assertEqual(d['values'][1], {'name': 'F4', 'classname': 'IDLBitValue', 'position': 4, 'value': 16,
                                          'annotations': [{'name': 'position', 'args': ['4'], 'params': {}}]})
        self.assertIn('bitmask Plain', self.m.to_simple_dic()['module M'][1])

    def test_errors(self):
        """Errors: position beyond bit_bound, duplicate position, bit_bound over 64, missing ";" or "}".

        位置が bit_bound 超過・位置重複・bit_bound>64・; や } 欠落でエラー。
        """
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
    """Category: Bitmasks and bitsets / カテゴリ: bitmask・bitset

    IDL 4.2 bitset: bitfield layout, inheritance, output and errors.
    IDL 4.2 の bitset: bitfield の配置・継承・出力・エラー。
    """

    def setUp(self):
        self.g = load(IDL)
        self.m = self.g.module_by_name('M')

    def test_layout(self):
        """Bitset base, bitfield sizes / types / positions and the total bit size.

        bitset の継承元・bitfield のビット数/型/位置・合計ビット数。
        """
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
        """A bitset can inherit a bitset in another module by scoped name, and positions continue after the base.

        別モジュールの bitset をスコープ付き名で継承し、位置が続きから振られる。
        """
        e = self.g.module_by_name('N').bitset_by_name('Ext')
        self.assertEqual(e.base.full_path, 'M::Header')
        self.assertEqual(e.bitfield_by_name('extra').position, 22)
        self.assertEqual(e.bit_size, 24)

    def test_to_dic(self):
        """to_dic() of a bitset contains base, bit_size and bitfields.

        bitset の to_dic() に base・bit_size・bitfields が出る。
        """
        d = self.m.bitset_by_name('Header').to_dic()
        self.assertEqual(d['base'], 'M::Base')
        self.assertEqual(d['bit_size'], 22)
        self.assertEqual(len(d['bitfields']), 5)

    def test_errors(self):
        """Errors: more than 64 bits, size 0, unknown size constant, non-bitfield member, missing ";" or "}".

        64ビット超過・サイズ0・未知の定数・bitfield 以外・; や } 欠落でエラー。
        """
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
    """Category: Bitmasks and bitsets / カテゴリ: bitmask・bitset

    Bitmasks and bitsets used as types and found by name.
    型として使われる bitmask/bitset と、名前による検索。
    """

    def setUp(self):
        self.g = load(IDL)

    def test_struct_members(self):
        """Bitmasks and bitsets are resolved as struct member types.

        struct メンバーの型として bitmask/bitset が解決される。
        """
        s = self.g.module_by_name('M').struct_by_name('S')
        self.assertTrue(s.member_by_name('flags').type.is_bitmask)
        self.assertEqual(s.member_by_name('flags').type.full_path, 'M::Flags')
        self.assertTrue(s.member_by_name('header').type.is_bitset)
        self.assertEqual(s.member_by_name('plains').type.inner_type.obj.full_path, 'M::Plain')

    def test_scoped_name_from_other_module(self):
        """A bitmask can be referenced from another module as M::Flags.

        別モジュールから M::Flags で bitmask を参照できる。
        """
        t = self.g.module_by_name('N').struct_by_name('T')
        self.assertEqual(t.member_by_name('f').type.full_path, 'M::Flags')

    def test_find_types(self):
        """find_types() finds bitmasks and bitsets.

        find_types() で bitmask/bitset が見つかる。
        """
        self.assertTrue(self.g.find_types('M::Header')[0].is_bitset)
        self.assertTrue(self.g.find_types('Flags')[0].is_bitmask)


if __name__ == '__main__':
    unittest.main()
