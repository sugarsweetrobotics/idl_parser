"""basic_module_test.idl: interfaces and their methods."""
import os
import unittest
from idl_parser import parser
from tests import support


IDL_DIR = support.IDL_DIR

idl_path = os.path.join(IDL_DIR, 'basic_module_test.idl')


class BasicTestFunctions(unittest.TestCase):
    def setUp(self):
        pass

    def test_interface_types(self):
        parser_ = parser.IDLParser()
        with open(idl_path, 'r') as idlf:
            m = parser_.load(idlf.read())
            self.assertEqual(m.name,'__global__')
            my_module = m.modules[1]
            self.assertEqual(my_module.name, 'my_module')
            
            my_int = my_module.interface_by_name('my_interface1')
            self.assertEqual(my_int.basename, 'my_interface1')
            method1 = my_int.method_by_name('method1')
            self.assertEqual(method1.name, 'method1')
            
            self.assertEqual(method1.returns.name, 'long')
            la = method1.argument_by_name('long_arg')
            self.assertEqual(la.name, 'long_arg')
            self.assertEqual(la.type.name, 'long')
            self.assertEqual(la.direction, 'in')

            da = method1.argument_by_name('double_arg')
            self.assertEqual(da.name, 'double_arg')
            self.assertEqual(da.type.name, 'double')
            self.assertEqual(da.direction, 'out')
            
            sa = method1.argument_by_name('short_arg')
            self.assertEqual(sa.name, 'short_arg')
            self.assertEqual(sa.type.name, 'short')
            self.assertEqual(sa.direction, 'inout')
            
            method2 = my_int.method_by_name('method2')
            self.assertEqual(method2.returns.basename, 'my_struct1')
            self.assertEqual(method2.argument_by_name('my_struct1_arg').type.basename, 'my_struct1')
            self.assertEqual(method2.argument_by_name('my_struct2_arg').type.basename, 'my_struct2')


if __name__ == '__main__':
    unittest.main()
