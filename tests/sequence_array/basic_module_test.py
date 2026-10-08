"""basic_module_test.idl: typedefs, sequences and arrays."""
import os
import unittest
from idl_parser import parser
from tests import support


IDL_DIR = support.IDL_DIR

idl_path = os.path.join(IDL_DIR, 'basic_module_test.idl')


class BasicTestFunctions(unittest.TestCase):
    """Category: Sequences, arrays and typedefs / カテゴリ: sequence・array・typedef

    Typedefs, sequences and arrays in basic_module_test.idl.
    basic_module_test.idl の typedef・sequence・配列。
    """

    def setUp(self):
        pass

    def test_typedef_types(self):
        """Typedefs of primitives, structs and others.

        プリミティブ・struct などの typedef。
        """
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

    def test_sequence_test(self):
        """Sequence typedefs and their element types.

        sequence の typedef と要素型。
        """
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
        """Typedefs of multi-dimensional arrays.

        多次元配列の typedef。
        """
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


if __name__ == '__main__':
    unittest.main()
