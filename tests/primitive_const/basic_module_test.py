"""basic_module_test.idl: primitive member types and consts."""
import os
import unittest
from idl_parser import parser
from tests import support


IDL_DIR = support.IDL_DIR

idl_path = os.path.join(IDL_DIR, 'basic_module_test.idl')


class BasicTestFunctions(unittest.TestCase):
    """Category: Primitive types and constants / カテゴリ: 基本型・定数

    Primitive member types and consts in basic_module_test.idl.
    basic_module_test.idl のプリミティブ型メンバーと const。
    """

    def setUp(self):
        pass

    def test_primitive_types(self):
        """Struct members of each primitive type.

        各種プリミティブ型の struct メンバー。
        """
        parser_ = parser.IDLParser()
        with open(idl_path, 'r') as idlf:
            m = parser_.load(idlf.read())

            self.assertEqual(m.name,'__global__')
            my_module = m.modules[1]
            self.assertEqual(my_module.name, 'my_module')
            my_struct = my_module.struct_by_name('my_struct3')
            self.assertEqual(my_struct.name, 'my_struct3')
            
            typenames = {
                'octet': 'octet_member',
                'char': 'char_member',
                'wchar': 'wchar_member',
                'string': 'string_member',
                'unsigned short': 'ushort_member',
                'short': 'short_member',
                'unsigned long': 'ulong_member',
                'long': 'long_member',
                'float': 'float_member',
                'double': 'double_member'
                }

            for typename, valuename in typenames.items():
                m = my_struct.member_by_name(valuename)
                self.assertEqual(typename, m.type.name)
                self.assertTrue(m.type.is_primitive)
                self.assertFalse(m.type.is_struct)
                self.assertFalse(m.type.is_typedef)
                self.assertFalse(m.type.is_enum)
                self.assertFalse(m.type.is_interface)
                self.assertFalse(m.type.is_const)


    def test_const_types(self):
        """Types and values of various consts.

        各種 const の型と値。
        """
        parser_ = parser.IDLParser()
        with open(idl_path, 'r') as idlf:
            m = parser_.load(idlf.read())
            self.assertEqual(m.name,'__global__')
            my_module = m.modules[1]
            self.assertEqual(my_module.name, 'my_module')
            
            value1 = my_module.const_by_name('value1')
            self.assertTrue(value1.is_const)
            self.assertEqual(value1.value_string, '-1')
            self.assertEqual(value1.type.name, 'long')
            
            value2 = my_module.const_by_name('value2')
            self.assertTrue(value2.is_const)
            self.assertEqual(value2.value_string, '4')
            self.assertEqual(value2.type.name, 'unsigned long')


if __name__ == '__main__':
    unittest.main()
