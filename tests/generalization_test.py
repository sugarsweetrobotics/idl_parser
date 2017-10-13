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

idl_path = 'idls/generalization.idl'

class GeneralizationTestFunctions(unittest.TestCase):
    def setUp(self):
        pass

    def test_module(self):
        parser_ = parser.IDLParser()
        with open(idl_path, 'r') as idlf:
            m = parser_.load(idlf.read())
            self.assertEqual(m.name,'__global__')
            moduleA = m.modules[0]
            self.assertEqual(moduleA.name, 'moduleA')
            interfaceA = moduleA.interface_by_name('InterfaceA')
            self.assertEqual(interfaceA.name, 'InterfaceA')
            interfaceB = moduleA.interface_by_name('InterfaceB')
            self.assertEqual(interfaceB.name, 'InterfaceB')

            self.assertEqual(len(interfaceA.inheritances), 0)
            self.assertEqual(len(interfaceB.inheritances), 1)        
            self.assertEqual(interfaceB.inheritances[0].full_path, 'moduleA::InterfaceA') # Must be fullpath


if __name__ == '__main__':
    unittest.main()


def suite():
    suite = unittest.TestSuite()
    suite.addTests(unittest.makeSuite(MultiModuleTestFunctions))
    return suite
