import os, sys, traceback
import unittest
from idl_parser import parser
from idl_parser.type import IDLType
from idl_parser.exception import IDLParserException

IDL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'idls')


idl_path = os.path.join(IDL_DIR, 'invalid_idl.idl')

class InvalidIDLTestFunctions(unittest.TestCase):
    def setUp(self):
        pass

    def test_invalid_message(self):
        parser_ = parser.IDLParser()
        try:
            with open(idl_path, 'r') as idlf:
                m = parser_.load(idlf.read(), filepath=idl_path)
        except IDLParserException as ex:
            self.assertEqual(ex.line_number, 10)

        except:
            traceback.print_exc()
            raise ex

if __name__ == '__main__':
    unittest.main()


def suite():
    suite = unittest.TestSuite()
    suite.addTests(unittest.makeSuite(MultiModuleTestFunctions))
    return suite
