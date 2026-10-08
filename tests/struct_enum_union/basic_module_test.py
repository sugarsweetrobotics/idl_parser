"""basic_module_test.idl: structs, unions and enums."""
import os
import unittest
from idl_parser import parser
from idl_parser.type import IDLType
from tests import support


IDL_DIR = support.IDL_DIR

idl_path = os.path.join(IDL_DIR, 'basic_module_test.idl')


class BasicTestFunctions(unittest.TestCase):
    def setUp(self):
        pass

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


if __name__ == '__main__':
    unittest.main()
