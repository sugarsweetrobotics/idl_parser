import os, sys
import unittest
import idl_parser

idl_path = 'idls/module_test.idl'
class TestFunctions(unittest.TestCase):
    def setUp(self):
        pass

    def test_module(self):
        parser = idl_parser.IDLParser()
        m = parser.load(open(idl_path, 'r').read())
        self.assertEqual(m.name,'__global__')
        my_module = m.modules[0]
        self.assertEqual(my_module.name, 'my_module')
        my_struct = my_module.struct_by_name('my_struct1')
        self.assertEqual(my_struct.name, 'my_struct1')

    def test_primitive_types(self):
        parser = idl_parser.IDLParser()
        m = parser.load(open(idl_path, 'r').read())
        self.assertEqual(m.name,'__global__')
        my_module = m.modules[0]
        self.assertEqual(my_module.name, 'my_module')
        my_struct = my_module.struct_by_name('my_struct3')
        self.assertEqual(my_struct.name, 'my_struct3') 

        typenames = {
            'octet': 'octet_member',
            'unsigned long': 'ulong_member',
            
            'char': 'char_member',
            'wchar': 'wchar_member',
            'string': 'string_member',
            'unsigned short': 'ushort_member',
            'short': 'short_member',
            'unsigned long': 'ulong_member',
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



    def test_typedef_types(self):
        parser = idl_parser.IDLParser()
        m = parser.load(open(idl_path, 'r').read())
        self.assertEqual(m.name,'__global__')
        my_module = m.modules[0]
        self.assertEqual(my_module.name, 'my_module')

        my_byte = my_module.typedef_by_name('my_byte')
        self.assertEqual(my_byte.name, 'my_byte')
        self.assertEqual(my_byte.type.name, 'octet')

        my_st = my_module.typedef_by_name('my_struct_typedef')
        self.assertEqual(my_st.name, 'my_struct_typedef')
        self.assertEqual(my_st.type.basename, 'my_struct1')
        self.assertEqual(my_st.type.member_by_name('long_member').type.name, 'long')

    def test_interface_types(self):
        parser = idl_parser.IDLParser()
        m = parser.load(open(idl_path, 'r').read())
        self.assertEqual(m.name,'__global__')
        my_module = m.modules[0]
        self.assertEqual(my_module.name, 'my_module')
        
        my_int = my_module.interface_by_name('my_interface1')
        self.assertEqual(my_int.basename, 'my_interface1')
        method1 = my_int.method_by_name('method1')
        self.assertEqual(method1.name, 'method1')

        self.assertEqual(method1.returns.name, 'long')
        la = method1.argument_by_name('long_arg')
        self.assertEqual(la.name, 'long_arg')
        self.assertEqual(la.type.name, 'long')
        self.assertEqual(la.direction, 'in')

        da = method1.argument_by_name('double_arg')
        self.assertEqual(da.name, 'double_arg')
        self.assertEqual(da.type.name, 'double')
        self.assertEqual(da.direction, 'out')

        sa = method1.argument_by_name('short_arg')
        self.assertEqual(sa.name, 'short_arg')
        self.assertEqual(sa.type.name, 'short')
        self.assertEqual(sa.direction, 'inout')


        method2 = my_int.method_by_name('method2')
        self.assertEqual(method2.returns.basename, 'my_struct1')
        self.assertEqual(method2.argument_by_name('my_struct1_arg').type.basename, 'my_struct1')
        self.assertEqual(method2.argument_by_name('my_struct2_arg').type.basename, 'my_struct2')
        
    def test_struct_types(self):
        parser = idl_parser.IDLParser()
        m = parser.load(open(idl_path, 'r').read())
        self.assertEqual(m.name,'__global__')
        my_module = m.modules[0]
        self.assertEqual(my_module.name, 'my_module')
        my_struct2 = my_module.struct_by_name('my_struct2')
        self.assertEqual(my_struct2.basename, 'my_struct2')

        m = my_struct2.member_by_name('my_struct_member')
        self.assertEqual(m.type.basename, 'my_struct1')

        my_struct = m.type
        self.assertTrue(my_struct.is_struct)


        
if __name__ == '__main__':
    unittest.main()
