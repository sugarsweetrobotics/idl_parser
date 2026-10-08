"""basic_module_test.idl: the global and named modules."""
import os
import unittest
from idl_parser import parser
from tests import support


IDL_DIR = support.IDL_DIR

idl_path = os.path.join(IDL_DIR, 'basic_module_test.idl')


class BasicTestFunctions(unittest.TestCase):
    """Category: Modules, scopes and type name resolution / カテゴリ: モジュール・スコープ・型名解決

    The global and named modules of basic_module_test.idl.
    basic_module_test.idl のグローバル module と名前付き module。
    """

    def setUp(self):
        pass

    def test_module(self):
        """The global and named modules and a struct of basic_module_test.idl.

        basic_module_test.idl のグローバル/名前付き module と struct の取得。
        """
        parser_ = parser.IDLParser()
        with open(idl_path, 'r') as idlf:
            m = parser_.load(idlf.read())
            self.assertEqual(m.name,'__global__')
            my_module = m.modules[1]
            self.assertEqual(my_module.name, 'my_module')
            my_struct = my_module.struct_by_name('my_struct1')
            self.assertEqual(my_struct.name, 'my_struct1')


if __name__ == '__main__':
    unittest.main()
