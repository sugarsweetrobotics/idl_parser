"""Tests for issue #138: built-in types of module CORBA (CORBA::TypeCode, ...).

OpenRTM-aist's SDOPackage.idl uses CORBA::TypeCode through
"#define TypeCode CORBA::TypeCode" without defining it, as an ORB knows it
from its orb.idl, so SDOPackage.idl (and RTC.idl, Manager.idl, OpenRTM.idl
that include it) failed with "Can not find Data Type (CORBA::TypeCode)".
CORBA::TypeCode, CORBA::Principal and CORBA::AbstractBase are now built-in
primitive types, used when the IDL does not define them, and an
"#include <orb.idl>" that can not be found is skipped.
"""
import os
import tempfile
import unittest

from idl_parser import parser
from idl_parser.exception import InvalidDataTypeException, IDLCanNotFindException


# The part of OpenRTM-aist's SDOPackage.idl that uses CORBA::TypeCode
SDO_IDL = '''
#ifndef ORBIT2_IDL
#define TypeCode CORBA::TypeCode
#endif
module SDOPackage {
  struct NameValue { string name; any value; };
  typedef sequence<string> StringList;
  struct Parameter {
    string name;
    TypeCode allowed_type;
    any allowed_values;
  };
  typedef sequence<Parameter> ParameterList;
  interface Configuration {
    TypeCode type_of(in string name);
    void set(in TypeCode tc);
  };
};
'''


class BuiltinCorbaTypeTest(unittest.TestCase):
    """Category: Primitive types and constants / カテゴリ: プリミティブ型・const

    CORBA::TypeCode and the other built-in CORBA types (issue #138).
    CORBA::TypeCode などの組み込みの CORBA 型(#138)。
    """

    @classmethod
    def setUpClass(cls):
        cls.p = parser.IDLParser()
        cls.g = cls.p.load(SDO_IDL)
        cls.sdo = cls.g.module_by_name('SDOPackage')

    def test_member(self):
        """A member of type CORBA::TypeCode is a built-in IDLPrimitive. / CORBA::TypeCode 型のメンバーは組み込みの IDLPrimitive。"""
        t = self.sdo.struct_by_name('Parameter').member_by_name('allowed_type').type
        self.assertTrue(t.is_primitive)
        self.assertTrue(t.is_builtin_corba_type)
        self.assertEqual(t.name, 'TypeCode')
        self.assertEqual(str(t), 'TypeCode')

    def test_other_primitives_are_not_builtin_corba_types(self):
        """Ordinary primitive types are not built-in CORBA types. / 通常のプリミティブ型は組み込みの CORBA 型ではない。"""
        t = self.sdo.struct_by_name('Parameter').member_by_name('name').type
        self.assertFalse(t.is_builtin_corba_type)

    def test_operation(self):
        """Operations can use it. / オペレーションでも使える。"""
        conf = self.sdo.interface_by_name('Configuration')
        self.assertEqual(str(conf.method_by_name('type_of').returns.obj), 'TypeCode')
        self.assertEqual(conf.method_by_name('set').arguments[0].type.obj.name, 'TypeCode')

    def test_all_builtin_types(self):
        """TypeCode, Principal and AbstractBase, in sequences and typedefs too. / TypeCode・Principal・AbstractBase(sequence や typedef の中でも)。"""
        g = parser.IDLParser().load(
            'struct S { CORBA::TypeCode a; CORBA::Principal b; CORBA::AbstractBase c;'
            ' sequence<CORBA::TypeCode> d; };\ntypedef ::CORBA::TypeCode TC;')
        s = g.struct_by_name('S')
        self.assertEqual([m.type.name for m in s.members[:3]], ['TypeCode', 'Principal', 'AbstractBase'])
        self.assertTrue(s.member_by_name('d').type.inner_type.is_builtin_corba_type)
        self.assertEqual(g.typedef_by_name('TC').type.name, 'TypeCode')

    def test_inside_module_corba(self):
        """Inside module CORBA, TypeCode alone names it. / module CORBA の中では TypeCode だけで指せる。"""
        g = parser.IDLParser().load('module CORBA { struct X { TypeCode t; }; };')
        self.assertTrue(g.module_by_name('CORBA').struct_by_name('X').members[0].type.is_builtin_corba_type)

    def test_not_outside_module_corba(self):
        """Outside module CORBA, TypeCode alone is not defined. / module CORBA の外では TypeCode だけでは未定義。"""
        with self.assertRaises(InvalidDataTypeException):
            parser.IDLParser().load('struct S { TypeCode t; };')
        with self.assertRaises(InvalidDataTypeException):
            parser.IDLParser().load('struct S { CORBA::Unknown t; };')

    def test_definition_in_idl_wins(self):
        """A CORBA::TypeCode defined in the IDL is used instead. / IDL で定義した CORBA::TypeCode が優先される。"""
        g = parser.IDLParser().load('module CORBA { native TypeCode; };\nstruct S { CORBA::TypeCode t; };')
        t = g.struct_by_name('S').members[0].type
        self.assertTrue(t.is_native)
        self.assertIs(t, g.module_by_name('CORBA').native_by_name('TypeCode'))

    def test_default_value(self):
        """The default value made by generate_constructor_python is None. / generate_constructor_python の既定値は None。"""
        s = self.sdo.struct_by_name('Parameter')
        self.assertEqual(self.p.generate_constructor_python(s), 'SDOPackage.Parameter(0, None, None)')


class OrbIdlIncludeTest(unittest.TestCase):
    """Category: Primitive types and constants / カテゴリ: プリミティブ型・const

    "#include <orb.idl>" (issue #138).
    "#include <orb.idl>"(#138)。
    """

    def test_missing_orb_idl_is_skipped(self):
        """An orb.idl that can not be found is skipped. / 見つからない orb.idl は読み飛ばす。"""
        g = parser.IDLParser().load('#include <orb.idl>\nstruct S { CORBA::TypeCode t; };')
        self.assertTrue(g.struct_by_name('S').members[0].type.is_builtin_corba_type)

    def test_other_missing_include_is_still_an_error(self):
        """Another missing include is still an error. / 他の見つからない include は従来どおりエラー。"""
        with self.assertRaises(IDLCanNotFindException):
            parser.IDLParser().load('#include <other.idl>\nstruct S { long a; };')

    def test_orb_idl_found_is_used(self):
        """An orb.idl that is found is read, and its definitions win. / 見つかった orb.idl は読み、その定義が優先される。"""
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, 'orb.idl'), 'w') as f:
                f.write('module CORBA { interface TypeCode { }; };\n')
            g = parser.IDLParser(idl_dirs=[d]).load('#include <orb.idl>\nstruct S { CORBA::TypeCode t; };')
            self.assertTrue(g.struct_by_name('S').members[0].type.is_interface)


if __name__ == '__main__':
    unittest.main()
