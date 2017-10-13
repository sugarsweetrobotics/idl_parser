import os, sys
import unittest
from idl_parser import parser
from idl_parser.type import IDLType

from multimodule_test import MultiModuleTestFunctions

__nocoveralls = False # This might be redundant but just in case ...
try:
    from coveralls import Coveralls
    from coveralls.api import log
except:
    sys.stdout.write('''
#######################################
# 
#   importing "coveralls" failed.
#   
#######################################
''')
    __nocoveralls = True

idl_path = 'idls/basic_module_test.idl'

class BasicTestFunctions(unittest.TestCase):
    def setUp(self):
        pass

    def test_module(self):
        parser_ = parser.IDLParser()
        with open(idl_path, 'r') as idlf:
            m = parser_.load(idlf.read())
            self.assertEqual(m.name,'__global__')
            my_module = m.modules[1]
            self.assertEqual(my_module.name, 'my_module')
            my_struct = my_module.struct_by_name('my_struct1')
            self.assertEqual(my_struct.name, 'my_struct1')

    def test_primitive_types(self):
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
        parser_ = parser.IDLParser()
        with open(idl_path, 'r') as idlf:
            m = parser_.load(idlf.read())
            self.assertEqual(m.name,'__global__')
            my_module = m.modules[1]
            self.assertEqual(my_module.name, 'my_module')
            
            my_byte = my_module.typedef_by_name('my_byte')
            self.assertEqual(my_byte.name, 'my_byte')
            self.assertEqual(my_byte.type.name, 'octet')
            
            my_st = my_module.typedef_by_name('my_struct_typedef')
            self.assertEqual(my_st.name, 'my_struct_typedef')
            self.assertEqual(my_st.type.basename, 'my_struct1')
            self.assertEqual(my_st.type.member_by_name('long_member').type.name, 'long')
            pass

    def test_interface_types(self):
        parser_ = parser.IDLParser()
        with open(idl_path, 'r') as idlf:
            m = parser_.load(idlf.read())
            self.assertEqual(m.name,'__global__')
            my_module = m.modules[1]
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
        parser_ = parser.IDLParser()
        with open(idl_path, 'r') as idlf:
            m = parser_.load(idlf.read())
            self.assertEqual(m.name,'__global__')
            my_module = m.modules[1]
            self.assertEqual(my_module.name, 'my_module')
            my_struct2 = my_module.struct_by_name('my_struct2')
            self.assertEqual(my_struct2.basename, 'my_struct2')
            self.assertTrue(my_struct2.is_struct)
            
            m = my_struct2.member_by_name('my_struct_member')
            self.assertEqual(m.type.basename, 'my_struct1')
            
            my_struct = m.type
            self.assertTrue(my_struct.is_struct)
            
    def test_union_types(self):
        parser_ = parser.IDLParser()
        with open(idl_path, 'r') as idlf:
            m = parser_.load(idlf.read())
            self.assertEqual(m.name,'__global__')
            my_module = m.modules[1]
            self.assertEqual(my_module.name, 'my_module')
            my_union_1 = my_module.union_by_name('my_union1')
            self.assertEqual(my_union_1.basename, 'my_union1')
            self.assertTrue(my_union_1.is_union)
            
            m = my_union_1.member_by_name('ull_value')
            self.assertEqual(m.type.name, 'unsigned long long')
            self.assertIn(
                'descriminator_unknown',
                m.descriminator_value_associations)
            self.assertIn(
                'descriminator_kind_count',
                m.descriminator_value_associations)
            self.assertIn(
                'descriminator_ulonglong',
                m.descriminator_value_associations)
            m = my_union_1.member_by_name('ll_value')
            self.assertEqual(m.type.name, 'long long')
            self.assertIn(
                'descriminator_longlong',
                m.descriminator_value_associations)
            m = my_union_1.member_by_name('d_value')
            self.assertEqual(m.type.name, 'double')
            self.assertIn(
                'descriminator_double',
                m.descriminator_value_associations)
            m = my_union_1.member_by_name('str_value')
            sequence_type = IDLType(m.type.name, m.parent)
            self.assertTrue(sequence_type.is_sequence)
            self.assertEqual(sequence_type.inner_type.name, 'char')
            self.assertIn(
                'descriminator_string',
                m.descriminator_value_associations)
        pass

    def test_enum_types(self):
        parser_ = parser.IDLParser()
        with open(idl_path, 'r') as idlf:
            m = parser_.load(idlf.read())
            self.assertEqual(m.name,'__global__')
            my_module = m.modules[1]
            self.assertEqual(my_module.name, 'my_module')
        
            my_enum1 = my_module.enum_by_name('my_enum1')
            self.assertEqual(my_enum1.name, 'my_enum1')
            self.assertTrue(my_enum1.is_enum)
            
            self.assertEqual(my_enum1.value_by_name('data1').value, 0)
            self.assertEqual(my_enum1.value_by_name('data2').value, 1)
            self.assertEqual(my_enum1.value_by_name('data3').value, 2)
        pass

    def test_const_types(self):
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
            
    def test_sequence_test(self):
        parser_ = parser.IDLParser()
        with open(idl_path, 'r') as idlf:
            m = parser_.load(idlf.read())
            self.assertEqual(m.name,'__global__')
            my_module = m.modules[1]
            self.assertEqual(my_module.name, 'my_module')
            
            doubleSeq = my_module.find_types('DoubleSeq')[0]
            self.assertEqual(doubleSeq.name, 'DoubleSeq')
            seq_double = doubleSeq.type
            self.assertTrue(seq_double.is_sequence)
            self.assertEqual(seq_double.inner_type.name, 'double')
            
    def test_arraye_test(self):
        parser_ = parser.IDLParser()
        with open(idl_path, 'r') as idlf:
            m = parser_.load(idlf.read())
            self.assertEqual(m.name,'__global__')
            my_module = m.modules[1]
            self.assertEqual(my_module.name, 'my_module')
            
            mat34 = my_module.find_types('Matrix34')[0]
            self.assertEqual(mat34.name, 'Matrix34')
            self.assertTrue(mat34.is_typedef)
            arr_arr_double = mat34.type
            self.assertTrue(arr_arr_double.is_array)
            self.assertEqual(arr_arr_double.size, 3)
            
            arr_double = arr_arr_double.inner_type
            self.assertEqual(arr_double.name, 'double [4]')
            self.assertTrue(arr_double.is_array)
            self.assertEqual(arr_double.size, 4)
            self.assertEqual(arr_double.inner_type.name, 'double')
            
            
            mat3456 = my_module.find_types('Matrix3456')[0]
            self.assertEqual(mat3456.name, 'Matrix3456')
            self.assertTrue(mat3456.is_typedef)
            arr_arr_arr_arr_ul = mat3456.type
            self.assertTrue(arr_arr_arr_arr_ul.is_array)
            self.assertEqual(arr_arr_arr_arr_ul.size,3)
            
            arr_arr_arr_ul = arr_arr_arr_arr_ul.inner_type
            self.assertTrue(arr_arr_arr_ul.is_array)
            self.assertEqual(arr_arr_arr_ul.size, 4)
            
            arr_arr_ul = arr_arr_arr_ul.inner_type
            self.assertTrue(arr_arr_ul.is_array)
            self.assertEqual(arr_arr_ul.size, 5)
            
            arr_ul = arr_arr_ul.inner_type
            self.assertTrue(arr_ul.is_array)
            self.assertEqual(arr_ul.size, 6)
            self.assertTrue(arr_ul.inner_type.name, 'unsigned long')
            
    def test_odd_spaces(self):
        parser_ = parser.IDLParser()
        with open(idl_path, 'r') as idlf:
            m = parser_.load(idlf.read())
            self.assertEqual(m.name,'__global__')
            my_module = m.modules[1]
            self.assertEqual(my_module.name, 'my_module')
            another_struct = my_module.struct_by_name('another_struct')
            m = another_struct.member_by_name('another_struct_array1')
            self.assertTrue(m.type.is_array)
            self.assertEqual(m.type.inner_type.name, 'double')
            self.assertEqual(m.type.size, 10)
            m = another_struct.member_by_name('another_struct_array2')
            self.assertEqual(m.type.inner_type.name, 'short')
            self.assertTrue(m.type.is_array)
            self.assertEqual(m.type.size, 11)
            m = another_struct.member_by_name('another_struct_array3')
            self.assertEqual(m.type.inner_type.name, 'short')
            self.assertTrue(m.type.is_array)
            self.assertEqual(m.type.size, 44)
            m = another_struct.member_by_name('another_struct_array1')
            m = another_struct.member_by_name('another_struct_seq1')
            self.assertEqual(m.type.inner_type.name, 'my_byte')
            m = another_struct.member_by_name('another_struct_seq2')
            self.assertEqual(m.type.inner_type.name, 'long')

if __name__ == '__main__':
    unittest.main()


def suite():
    suite = unittest.TestSuite()
    suite.addTests(unittest.makeSuite(BasicTestFunctions))
    suite.addTests(unittest.makeSuite(MultiModuleTestFunctions))
    return suite
