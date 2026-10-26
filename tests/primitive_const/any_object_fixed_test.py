"""any, Object, ValueBase and fixed<d, s> (issue #119).

These types could be used only in operation signatures (as names that were
not resolved); as the type of a member or a typedef they failed with
"Can not find Data Type". any, Object and ValueBase are now primitive types
(IDLPrimitive), and fixed<d, s> is an IDLFixed with digits and scale.
"""
import unittest
from idl_parser import parser, exception


IDL = '''
module M {
  const long D = 8;
  typedef any AnyT;
  typedef fixed<5, 1> Money;
  struct S {
    any a;
    Object o;
    ValueBase v;
    fixed<10,2> f;
    fixed<D, 3> g;
    fixed<4, 2> arr[2];
    sequence<fixed<4, 2> > sq;
    map<string, any> props;
    Money price;
    AnyT x;
  };
  union U switch (long) { case 1: any a; case 2: fixed<6, 2> f; };
  interface I {
    attribute ValueBase vb;
    any op(in Object o, in fixed<3, 1> f);
  };
  valuetype V { public any data; public fixed<8, 4> rate; };
};
'''


class AnyObjectFixedTest(unittest.TestCase):
    """Category: Primitive types and constants / カテゴリ: 基本型・定数

    any, Object, ValueBase and fixed<d, s> (issue #119).
    any・Object・ValueBase・fixed<d, s>(#119)。
    """

    @classmethod
    def setUpClass(cls):
        cls.parser = parser.IDLParser()
        cls.g = cls.parser.load(IDL)
        cls.m = cls.g.module_by_name('M')
        cls.s = cls.m.struct_by_name('S')

    def member_type(self, name):
        return self.s.member_by_name(name).type

    def test_any_object_valuebase_members(self):
        """any, Object and ValueBase members are primitive types.

        any・Object・ValueBase のメンバーは基本型になる。
        """
        for name, typename in (('a', 'any'), ('o', 'Object'), ('v', 'ValueBase')):
            t = self.member_type(name)
            self.assertTrue(t.is_primitive, name)
            self.assertEqual(t.classname, 'IDLPrimitive')
            self.assertEqual(str(t), typename)

    def test_fixed_member(self):
        """A fixed<d, s> member gives its digits and scale.

        fixed<d, s> のメンバーから桁数とスケールが得られる。
        """
        t = self.member_type('f')
        self.assertTrue(t.is_fixed)
        self.assertFalse(t.is_primitive)
        self.assertEqual(t.digits, 10)
        self.assertEqual(t.scale, 2)
        self.assertEqual(str(t), 'fixed<10, 2>')
        self.assertEqual(t.name, 'fixed<10, 2>')

    def test_fixed_with_constant(self):
        """A constant name in fixed<d, s> is kept as written.

        fixed<d, s> の定数名は書かれたまま得られる。
        """
        t = self.member_type('g')
        self.assertEqual(t.digits, 'D')
        self.assertEqual(t.scale, 3)

    def test_fixed_elements(self):
        """fixed<d, s> can be an array, sequence element or map value.

        fixed<d, s> を配列・sequence の要素型や map の値型にできる。
        """
        arr = self.member_type('arr')
        self.assertEqual(str(arr), 'fixed<4, 2>[2]')
        self.assertTrue(arr.inner_type.is_fixed)
        sq = self.member_type('sq')
        self.assertEqual(str(sq), 'sequence<fixed<4, 2>>')
        self.assertEqual(sq.inner_type.digits, 4)
        props = self.member_type('props')
        self.assertEqual(str(props.value_type), 'any')

    def test_typedefs(self):
        """typedef of any and fixed<d, s>, and members of those typedefs.

        any と fixed<d, s> の typedef と、それを型とするメンバー。
        """
        money = self.m.typedef_by_name('Money')
        self.assertTrue(money.type.is_fixed)
        self.assertEqual((money.type.digits, money.type.scale), (5, 1))
        self.assertEqual(str(self.m.typedef_by_name('AnyT').type), 'any')
        self.assertIs(self.member_type('price'), money)
        self.assertEqual(self.s.member_by_name('price').type.type.digits, 5)

    def test_union_member(self):
        """Union members of type any and fixed<d, s>.

        union のメンバーに any と fixed<d, s> を使える。
        """
        u = self.g.find_types('M::U')[0]
        types = [str(m.type) for m in u.members]
        self.assertEqual(types, ['any', 'fixed<6, 2>'])

    def test_interface(self):
        """Attributes, return values and arguments of these types.

        属性・戻り値・引数にこれらの型を使える。
        """
        i = self.m.interface_by_name('I')
        self.assertEqual(str(i.attributes[0].type), 'ValueBase')
        op = i.method_by_name('op')
        self.assertEqual(str(op.returns), 'any')
        self.assertTrue(op.returns.is_primitive)
        self.assertEqual([str(a.type) for a in op.arguments], ['Object', 'fixed<3, 1>'])
        self.assertTrue(op.arguments[1].type.is_fixed)

    def test_valuetype_state_members(self):
        """State members of a value type of type any and fixed<d, s>.

        valuetype の状態メンバーに any と fixed<d, s> を使える。
        """
        v = self.g.find_types('M::V')[0]
        self.assertEqual([str(m.type) for m in v.state_members], ['any', 'fixed<8, 4>'])

    def test_to_dic(self):
        """to_dic() writes the type names, and a fixed type its digits and scale.

        to_dic() には型名が、fixed 型には桁数とスケールが入る。
        """
        types = [m['type'] for m in self.s.to_dic()['members']]
        self.assertEqual(types[:4], ['any', 'Object', 'ValueBase', 'fixed<10, 2>'])
        self.assertEqual(self.member_type('f').to_dic(),
                         {'name': 'fixed<10, 2>', 'classname': 'IDLFixed',
                          'digits': 10, 'scale': 2})

    def test_generate_constructor_python(self):
        """None for any, Object and ValueBase, and 0 for fixed<d, s>.

        any・Object・ValueBase は None、fixed<d, s> は 0 になる。
        """
        self.assertEqual(self.parser.generate_constructor_python(self.s),
                         'M.S(None, None, None, 0, 0, [0, 0], [], {}, 0, None)')

    def test_invalid_fixed(self):
        """Digits outside 1 to 31, or a scale larger than the digits, is an error.

        桁数が1〜31でない、またはスケールが桁数より大きいとエラーになる。
        """
        for idl in ('struct X { fixed<32, 2> f; };',
                    'struct X { fixed<0, 0> f; };',
                    'struct X { fixed<3, 4> f; };',
                    'typedef fixed<3, 4> F;'):
            with self.assertRaises(exception.InvalidIDLSyntaxError, msg=idl):
                parser.IDLParser().load(idl)


if __name__ == '__main__':
    unittest.main()
