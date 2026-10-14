"""IDLNode.filepath of nodes read by parse() and through #include (issue #109)."""
import os
import unittest
from idl_parser import parser
from tests import support

idl_root = os.path.join(support.IDL_DIR, 'multi_include_dirs')
include_dirs = [os.path.join(idl_root, d) for d in ('common', 'geometry', 'navigation')]
navigator_idl = os.path.join(idl_root, 'navigation', 'navigator.idl')
time_idl = os.path.join(idl_root, 'common', 'time.idl')
geometry_idl = os.path.join(idl_root, 'geometry', 'geometry.idl')
path_idl = os.path.join(idl_root, 'geometry', 'path.idl')


class FilepathTest(unittest.TestCase):
    """Category: Include and file loading / カテゴリ: include・ファイル読込

    Each node records the file it is written in.
    各ノードの filepath は、そのノードが書かれているファイルになる。
    """

    def assertSameFile(self, node, path):
        self.assertIsNotNone(node.filepath, node.name)
        self.assertEqual(os.path.abspath(node.filepath), os.path.abspath(path), node.name)

    def _check(self, m):
        common = m.module_by_name('common')
        geometry = m.module_by_name('geometry')
        navigation = m.module_by_name('navigation')
        time = common.struct_by_name('Time')
        self.assertSameFile(time, time_idl)
        self.assertSameFile(time.member_by_name('sec'), time_idl)
        for name in ('Point', 'Pose'):
            self.assertSameFile(geometry.struct_by_name(name), geometry_idl)
        self.assertSameFile(geometry.struct_by_name('Pose').member_by_name('stamp'), geometry_idl)
        self.assertSameFile(geometry.struct_by_name('Path'), path_idl)
        self.assertSameFile(geometry.typedef_by_name('PoseList'), path_idl)
        navigator = navigation.interface_by_name('Navigator')
        self.assertSameFile(navigator, navigator_idl)
        self.assertSameFile(navigator.method_by_name('plan'), navigator_idl)
        self.assertSameFile(common, time_idl)
        self.assertSameFile(navigation, navigator_idl)

    def test_parse(self):
        """parse() records the file of each node, also of included files.

        parse() で、include されたファイルのノードにもそのファイルが入る。
        """
        parser_ = parser.IDLParser(idl_dirs=include_dirs)
        parser_.parse(idls=[navigator_idl])
        self._check(parser_.global_module)

    def test_load(self):
        """load(filepath=...) records the included file for nodes of included files.

        load(filepath=...) でも、include されたファイルのノードにはそのファイルが入る。
        """
        with open(navigator_idl) as f:
            m = parser.IDLParser().load(f.read(), include_dirs=include_dirs, filepath=navigator_idl)
        self._check(m)

    def test_parse_single_file(self):
        """parse() of one file without #include records that file.

        include の無い1ファイルの parse() でも filepath が入る。
        """
        parser_ = parser.IDLParser()
        parser_.parse(idls=[time_idl])
        self.assertSameFile(parser_.global_module.module_by_name('common').struct_by_name('Time'), time_idl)

    def test_load_without_filepath(self):
        """load() without filepath keeps None for the nodes of the text.

        filepath なしの load() では、そのテキストのノードは None のまま。
        """
        m = parser.IDLParser().load('module m { struct S { long a; }; };')
        self.assertIsNone(m.module_by_name('m').struct_by_name('S').filepath)

    def test_load_without_filepath_with_include(self):
        """load() without filepath still records the included files.

        filepath なしの load() でも、include されたファイルのノードにはそのファイルが入る。
        """
        m = parser.IDLParser().load('#include "time.idl"\nmodule m { struct S { common::Time t; }; };',
                                    include_dirs=include_dirs)
        self.assertIsNone(m.module_by_name('m').struct_by_name('S').filepath)
        self.assertSameFile(m.module_by_name('common').struct_by_name('Time'), time_idl)


if __name__ == '__main__':
    unittest.main()
