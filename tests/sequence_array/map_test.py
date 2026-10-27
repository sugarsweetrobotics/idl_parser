"""map<K, V> and map<K, V, N> (issue #118)."""
import unittest
from idl_parser import parser, exception


IDL = '''
module M {
  struct P { long x; };
  const long MAX = 5;
  typedef map<long, string, 10> LongStringMap;
  typedef map<string, P, MAX> PMap;
  struct S {
    map<string, long> m;
    map<long, sequence<P>> ms;
    sequence<map<long, LongStringMap>> sm;
    map<long, long> arr[2];
  };
};
'''


class MapTest(unittest.TestCase):
    """Category: Sequences, arrays and typedefs / カテゴリ: sequence・array・typedef

    Map types (issue #118).
    map 型(#118)。
    """

    def setUp(self):
        self.m = parser.IDLParser().load(IDL)
        self.s = self.m.find_types('M::S')[0]

    def test_member(self):
        """A map member gives its key and value types.

        map のメンバーからキーと値の型が得られる。
        """
        t = self.s.member_by_name('m').type
        self.assertTrue(t.is_map)
        self.assertFalse(t.is_sequence)
        self.assertEqual(t.key_type.name, 'string')
        self.assertTrue(t.value_type.is_primitive)
        self.assertIsNone(t.bound)
        self.assertFalse(t.is_bounded_map)
        self.assertEqual(str(t), 'map<string, long>')

    def test_bounded(self):
        """The bound is a number or a constant name (evaluated, issue #130), not part of the type name.

        上限は数値または定数名(評価される、#130)で、型名には含まれない。
        """
        t = self.m.find_types('M::LongStringMap')[0].type
        self.assertEqual(t.bound, 10)
        self.assertTrue(t.is_bounded_map)
        self.assertEqual(str(t), 'map<long, string>')
        self.assertEqual(self.m.find_types('M::PMap')[0].type.bound, 5)

    def test_named_types(self):
        """Named key and value types are resolved to their definitions.

        名前で書いたキーと値の型は定義に解決される。
        """
        t = self.m.find_types('M::PMap')[0].type
        self.assertTrue(t.value_type.is_struct)
        self.assertEqual(t.value_type.full_path, 'M::P')
        ms = self.s.member_by_name('ms').type
        self.assertTrue(ms.value_type.is_sequence)
        self.assertTrue(ms.value_type.inner_type.is_struct)

    def test_nested(self):
        """Maps inside sequences and arrays.

        sequence や配列の中の map。
        """
        sm = self.s.member_by_name('sm').type
        self.assertTrue(sm.inner_type.is_map)
        self.assertTrue(sm.inner_type.value_type.is_typedef)
        self.assertEqual(str(sm), 'sequence<map<long, LongStringMap>>')
        arr = self.s.member_by_name('arr').type
        self.assertTrue(arr.inner_type.is_map)
        self.assertEqual(str(arr), 'map<long, long>[2]')

    def test_to_dic(self):
        """to_dic() of a member writes the map type.

        メンバーの to_dic() は map 型を書く。
        """
        self.assertEqual(self.s.member_by_name('m').to_dic()['type'], 'map<string, long>')

    def test_constructor(self):
        """generate_constructor_python() gives {} for a map.

        generate_constructor_python() は map に {} を返す。
        """
        self.assertEqual(parser.IDLParser().generate_constructor_python(self.s),
                         'M.S({}, {}, [], [{}, {}])')

    def test_unknown_types(self):
        """An undefined key or value type is an error, also when nested.

        定義されていないキー・値の型は、入れ子でもエラー。
        """
        for idl in ('struct S { map<X, long> m; };',
                    'struct S { map<long, X> m; };',
                    'struct S { sequence<map<long, X>> m; };',
                    'typedef map<long, sequence<X>> T;'):
            with self.assertRaises(exception.InvalidDataTypeException, msg=idl):
                parser.IDLParser().load(idl)

    def test_invalid(self):
        """A map needs a key and a value type.

        map にはキーと値の型が必要。
        """
        for idl in ('struct S { map<long> m; };',
                    'struct S { map<long, long, 3, 4> m; };'):
            with self.assertRaises(exception.InvalidIDLSyntaxError, msg=idl):
                parser.IDLParser().load(idl)


if __name__ == '__main__':
    unittest.main()
