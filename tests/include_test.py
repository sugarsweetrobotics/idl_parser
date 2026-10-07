import os
import unittest
from idl_parser import parser

IDL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'idls')

idl_dir = os.path.join(IDL_DIR, 'circular')


class IncludeTestFunctions(unittest.TestCase):

    def test_circular_include_load(self):
        """Mutually including IDLs must not recurse forever (issue #6)."""
        parser_ = parser.IDLParser(idl_dirs=[idl_dir])
        path = idl_dir + '/circular_a.idl'
        with open(path, 'r') as f:
            m = parser_.load(f.read(), filepath=path)
        names = sorted(mod.name for mod in m.modules)
        self.assertEqual(names, ['circularA', 'circularB'])
        self.assertEqual(m.module_by_name('circularA').struct_by_name('StructA').name, 'StructA')
        self.assertEqual(m.module_by_name('circularB').struct_by_name('StructB').name, 'StructB')

    def test_circular_include_parse(self):
        parser_ = parser.IDLParser(idl_dirs=[idl_dir])
        parser_.parse(idls=[idl_dir + '/circular_a.idl'])
        names = sorted(mod.name for mod in parser_.global_module.modules)
        self.assertEqual(names, ['circularA', 'circularB'])

    def test_same_file_included_twice(self):
        parser_ = parser.IDLParser(idl_dirs=[idl_dir])
        with open(idl_dir + '/diamond.idl', 'r') as f:
            m = parser_.load(f.read())
        structs = m.module_by_name('circularA').structs
        self.assertEqual([s.name for s in structs], ['StructA'])
        member = m.module_by_name('diamond').struct_by_name('StructD').member_by_name('a')
        self.assertEqual(member.type.full_path, 'circularA::StructA')


if __name__ == '__main__':
    unittest.main()
