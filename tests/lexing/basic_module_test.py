"""basic_module_test.idl: definitions written with odd spacing."""
import os
import unittest
from idl_parser import parser
from tests import support


IDL_DIR = support.IDL_DIR

idl_path = os.path.join(IDL_DIR, 'basic_module_test.idl')


class BasicTestFunctions(unittest.TestCase):
    """Category: Lexing, preprocessing and error line numbers / カテゴリ: 字句解析・前処理・エラー行番号

    Definitions in basic_module_test.idl written with odd spacing.
    basic_module_test.idl の、空白の入れ方が変則的な定義。
    """

    def setUp(self):
        pass

    def test_odd_spaces(self):
        """Definitions such as arrays written with odd spacing.

        配列などに変則的な空白が入った定義。
        """
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
