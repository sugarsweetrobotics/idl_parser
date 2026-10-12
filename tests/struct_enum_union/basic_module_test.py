"""basic_module_test.idl: structs, unions and enums."""
import os
import unittest
from idl_parser import parser
from idl_parser.type import IDLType
from tests import support


IDL_DIR = support.IDL_DIR

idl_path = os.path.join(IDL_DIR, 'basic_module_test.idl')


class BasicTestFunctions(unittest.TestCase):
    """Category: Structs, enums and unions / カテゴリ: struct・enum・union

    Structs, unions and enums in basic_module_test.idl.
    basic_module_test.idl の struct・union・enum。
    """

    def setUp(self):
        pass

    def test_struct_types(self):
        """Structs and their member types.

        struct とそのメンバー型。
        """
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
        """Union discriminators and members.

        union の判別子とメンバー。
        """
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
        """Enum values and their numbers.

        enum の値と番号。
        """
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

    def test_enum_value_full_path(self):
        """An enumerator's full_path is scoped at the module enclosing the enum (issue #79).

        列挙子の full_path は enum を囲むモジュールのスコープになる（issue #79）。
        """
        m = parser.IDLParser().load(
            'module M { module N { enum E { A, B }; }; enum F { C }; }; enum G { D };')
        n = m.module_by_name('M').module_by_name('N')
        self.assertEqual(n.enum_by_name('E').value_by_name('A').full_path, 'M::N::A')
        self.assertEqual(n.enum_by_name('E').value_by_name('B').full_path, 'M::N::B')
        self.assertEqual(m.module_by_name('M').enum_by_name('F').value_by_name('C').full_path, 'M::C')
        self.assertEqual(m.enum_by_name('G').value_by_name('D').full_path, '::D')


if __name__ == '__main__':
    unittest.main()
