"""#include resolved through include_dirs (including_idl.idl)."""
import os
import unittest
from idl_parser import parser
from tests import support

IDL_DIR = support.IDL_DIR


class MultiModuleTestFunctions(unittest.TestCase):
    """Category: Include and file loading / カテゴリ: include・ファイル読込

    #include resolved through include_dirs.
    include_dirs を使った #include の解決。
    """

    def setUp(self):
        pass

    def test_include(self):
        """Modules and structs of an #included IDL are read (with include_dirs).

        #include した IDL の module/struct が読める(include_dirs 指定)。
        """
        parser_ = parser.IDLParser()
        with open(os.path.join(IDL_DIR, 'including_idl.idl'), 'r') as idlf:
            m = parser_.load(idlf.read(), include_dirs=[IDL_DIR])
            
            self.assertEqual(m.name,'__global__')
            moduleA = m.modules[0]
            self.assertEqual(moduleA.name, 'moduleA')
            structA = moduleA.struct_by_name('StructA')
            self.assertEqual(structA.name, 'StructA')
            double_member = structA.member_by_name('double_value')
            self.assertEqual(double_member.name, 'double_value')

            moduleB = m.modules[1]
            self.assertEqual(moduleB.name, 'moduleB')
            structB = moduleB.struct_by_name('StructB')
            self.assertEqual(structB.name, 'StructB')
            double_member = structB.member_by_name('structA_value')
            self.assertEqual(double_member.name, 'structA_value')


if __name__ == '__main__':
    unittest.main()
