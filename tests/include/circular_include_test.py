"""#include of mutually including / diamond-shaped IDL files (issue #6)."""
import os
import unittest
from idl_parser import parser
from tests import support

IDL_DIR = support.IDL_DIR

idl_dir = os.path.join(IDL_DIR, 'circular')


class IncludeTestFunctions(unittest.TestCase):
    """Category: Include and file loading / カテゴリ: include・ファイル読込

    Mutually including and diamond-shaped #include (issue #6).
    相互 include とダイヤモンド型の #include(#6)。
    """

    def test_circular_include_load(self):
        """load() of mutually including IDLs does not recurse forever (issue #6).

        相互 include する IDL を load() しても無限再帰しない(#6)。
        """
        parser_ = parser.IDLParser(idl_dirs=[idl_dir])
        path = idl_dir + '/circular_a.idl'
        with open(path, 'r') as f:
            m = parser_.load(f.read(), filepath=path)
        names = sorted(mod.name for mod in m.modules)
        self.assertEqual(names, ['circularA', 'circularB'])
        self.assertEqual(m.module_by_name('circularA').struct_by_name('StructA').name, 'StructA')
        self.assertEqual(m.module_by_name('circularB').struct_by_name('StructB').name, 'StructB')

    def test_circular_include_parse(self):
        """parse() of mutually including IDLs does not recurse forever.

        相互 include する IDL を parse() しても無限再帰しない。
        """
        parser_ = parser.IDLParser(idl_dirs=[idl_dir])
        parser_.parse(idls=[idl_dir + '/circular_a.idl'])
        names = sorted(mod.name for mod in parser_.global_module.modules)
        self.assertEqual(names, ['circularA', 'circularB'])

    def test_same_file_included_twice(self):
        """A file included through two paths (diamond) is not defined twice.

        同じファイルを2経路で include しても定義が重複しない(ダイヤモンド)。
        """
        parser_ = parser.IDLParser(idl_dirs=[idl_dir])
        with open(idl_dir + '/diamond.idl', 'r') as f:
            m = parser_.load(f.read())
        structs = m.module_by_name('circularA').structs
        self.assertEqual([s.name for s in structs], ['StructA'])
        member = m.module_by_name('diamond').struct_by_name('StructD').member_by_name('a')
        self.assertEqual(member.type.full_path, 'circularA::StructA')


if __name__ == '__main__':
    unittest.main()
