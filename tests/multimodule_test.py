import os, sys
import unittest
from idl_parser import parser
from idl_parser.type import IDLType

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

idl_path = 'idls/multi_module_test.idl'

class MultiModuleTestFunctions(unittest.TestCase):
    def setUp(self):
        pass

    def test_module(self):
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


if __name__ == '__main__':
    unittest.main()


def suite():
    suite = unittest.TestSuite()
    suite.addTests(unittest.makeSuite(MultiModuleTestFunctions))
    return suite
