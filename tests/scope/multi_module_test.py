"""Several modules in one IDL, and same-named structs in different modules."""
import os
import unittest
from idl_parser import parser
from tests import support

IDL_DIR = support.IDL_DIR


idl_path = os.path.join(IDL_DIR, 'multi_module_test.idl')


class MultiModuleTestFunctions(unittest.TestCase):
    """Category: Modules, scopes and type name resolution / カテゴリ: モジュール・スコープ・型名解決

    Several modules in one IDL, and same-named structs in different modules.
    1つの IDL 内の複数 module と、別 module の同名 struct。
    """

    def setUp(self):
        pass

    def test_module(self):
        """Each module and struct of an IDL with several modules.

        複数 module を含む IDL の各 module/struct。
        """
        parser_ = parser.IDLParser()
        with open(idl_path, 'r') as idlf:
            m = parser_.load(idlf.read())
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
            double_member = structB.member_by_name('double_valueA')
            self.assertEqual(double_member.name, 'double_valueA')

            moduleC = m.modules[2]
            self.assertEqual(moduleC.name, 'moduleC')
            structC = moduleC.struct_by_name('StructC')
            self.assertEqual(structC.name, 'StructC')
            structA_member = structC.member_by_name('structA_value')
            self.assertEqual(structA_member.name, 'structA_value')


    def test_distinguish_same_struct_different_module(self):
        """Same-named structs in different modules are told apart by full_path.

        別 module の同名 struct を full_path で区別できる。
        """
        parser_ = parser.IDLParser()
        with open(os.path.join(IDL_DIR, 'multi_module_test.idl'), 'r') as idlf:
            m = parser_.load(idlf.read(), include_dirs=[IDL_DIR])
            
            self.assertEqual(m.name,'__global__')
            moduleD = m.modules[3]
            self.assertEqual(moduleD.name, 'moduleD')
            structD = moduleD.struct_by_name('StructD')
            self.assertEqual(structD.full_path, 'moduleD::StructD')
            structA_member = structD.member_by_name('structA_value')
            self.assertEqual(structA_member.type.full_path, 'moduleD::StructA')


if __name__ == '__main__':
    unittest.main()
