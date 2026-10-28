"""Tests for issue #133: a definition inside an interface can use the interface.

A struct or exception defined in an interface could not have a member of the
interface's own type ("interface NC { exception CP { NC cxt; }; };" raised
InvalidDataTypeException), because the interface is added to its module only
after its body has been read. The standard CosNaming.idl
(NamingContext::CannotProceed) could not be read. While the body is read, the
name of the interface now resolves to the interface, as if it were
forward-declared.
"""
import unittest
from idl_parser import parser


IDL = '''
module CosNaming {
  typedef string Istring;
  struct NameComponent { Istring id; Istring kind; };
  typedef sequence<NameComponent> Name;

  interface NamingContext {
    enum NotFoundReason { missing_node, not_context, not_object };
    exception NotFound { NotFoundReason why; Name rest_of_name; };
    exception CannotProceed {
      NamingContext cxt;
      Name rest_of_name;
    };
    struct Holder {
      ::CosNaming::NamingContext absolute;
      CosNaming::NamingContext scoped;
      sequence<NamingContext> many;
      NamingContext pair[2];
    };
    typedef sequence<NamingContext> Contexts;
    NamingContext new_context();
    void bind_context(in Name n, in NamingContext nc) raises (NotFound, CannotProceed);
  };

  interface NamingContextExt : NamingContext {
    struct Ext { NamingContextExt self_; NamingContext base; };
  };
};

valuetype V {
  struct S { V v; };
  public long x;
};
'''


class InterfaceSelfReferenceTest(unittest.TestCase):
    """Category: Interfaces, operations and inheritance / カテゴリ: interface・operation・継承

    A definition inside an interface can use the interface's own type (issue #133).
    interface の中の定義から、その interface 自身の型を使える(#133)。
    """

    @classmethod
    def setUpClass(cls):
        cls.g = parser.IDLParser().load(IDL)
        cls.m = cls.g.module_by_name('CosNaming')
        cls.nc = cls.m.interface_by_name('NamingContext')

    def test_exception_member(self):
        """An exception member of the interface type is the IDLInterface. / exception のメンバーの型が IDLInterface になる。"""
        cxt = self.nc.exception_by_name('CannotProceed').member_by_name('cxt')
        self.assertIs(cxt.type, self.nc)
        self.assertTrue(cxt.type.is_interface)
        self.assertEqual(str(cxt.type), 'NamingContext')

    def test_scoped_names(self):
        """Scoped and absolute names of the interface resolve too. / スコープ付き・絶対名でも解決できる。"""
        holder = self.nc.struct_by_name('Holder')
        self.assertIs(holder.member_by_name('absolute').type, self.nc)
        self.assertIs(holder.member_by_name('scoped').type, self.nc)

    def test_sequence_and_array_elements(self):
        """Sequence and array elements resolve to the interface. / sequence と配列の要素も interface に解決される。"""
        holder = self.nc.struct_by_name('Holder')
        self.assertIs(holder.member_by_name('many').type.inner_type, self.nc)
        pair = holder.member_by_name('pair').type
        self.assertEqual(pair.size, 2)
        self.assertIs(pair.inner_type, self.nc)

    def test_typedef(self):
        """A typedef in the interface can use the interface. / interface の中の typedef でも使える。"""
        self.assertIs(self.nc.typedef_by_name('Contexts').type.inner_type, self.nc)

    def test_rest_of_interface(self):
        """The rest of the interface is parsed. / interface の残りも読める。"""
        self.assertEqual([m.name for m in self.nc.methods], ['new_context', 'bind_context'])
        self.assertIs(self.nc.method_by_name('new_context').returns.obj, self.nc)
        self.assertEqual([x.name for x in self.nc.method_by_name('bind_context').exceptions],
                         ['NotFound', 'CannotProceed'])

    def test_derived_interface(self):
        """A derived interface can use itself and its base. / 派生 interface から自身と基底を使える。"""
        ext = self.m.interface_by_name('NamingContextExt')
        s = ext.struct_by_name('Ext')
        self.assertIs(s.member_by_name('self_').type, ext)
        self.assertIs(s.member_by_name('base').type, self.nc)

    def test_valuetype(self):
        """A definition inside a value type can use the value type. / valuetype の中の定義からも、その valuetype を使える。"""
        v = self.g.valuetypes[0]
        self.assertIs(v.struct_by_name('S').member_by_name('v').type, v)

    def test_not_visible_outside(self):
        """Outside the interface, an undefined name is still an error. / interface の外では、未定義の名前は従来どおりエラー。"""
        from idl_parser.exception import InvalidDataTypeException
        with self.assertRaises(InvalidDataTypeException):
            parser.IDLParser().load('interface A { struct S { B b; }; }; interface B { };')


if __name__ == '__main__':
    unittest.main()
