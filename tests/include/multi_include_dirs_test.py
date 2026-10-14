"""#include chains that cross several include directories."""
import os
import unittest
from idl_parser import exception, parser
from tests import support

idl_root = os.path.join(support.IDL_DIR, 'multi_include_dirs')
include_dirs = [os.path.join(idl_root, d) for d in ('common', 'geometry', 'navigation')]
navigator_idl = os.path.join(idl_root, 'navigation', 'navigator.idl')


class MultiIncludeDirsTest(unittest.TestCase):
    """Category: Include and file loading / カテゴリ: include・ファイル読込

    navigation/navigator.idl -> geometry/path.idl -> geometry/geometry.idl
    -> common/time.idl, found through three include directories.
    3つの include ディレクトリをまたいで芋蔓式に #include する。
    """

    def _check(self, m):
        self.assertEqual(sorted(mod.name for mod in m.modules), ['common', 'geometry', 'navigation'])
        geometry = m.module_by_name('geometry')
        self.assertEqual([s.name for s in m.module_by_name('common').structs], ['Time'])
        self.assertEqual([s.name for s in geometry.structs], ['Point', 'Pose', 'Path'])
        self.assertEqual(geometry.struct_by_name('Pose').member_by_name('stamp').type.full_path,
                         'common::Time')
        plan = m.module_by_name('navigation').interface_by_name('Navigator').method_by_name('plan')
        self.assertEqual(plan.returns.obj.full_path, 'geometry::Path')
        self.assertEqual(plan.argument_by_name('goal').type.obj.full_path, 'geometry::Pose')

    def test_parse(self):
        """parse() of one file reads the files it includes directly and through other files.

        1ファイルの parse() で、直接・間接に include されたファイルが読まれる。
        """
        parser_ = parser.IDLParser(idl_dirs=include_dirs)
        parser_.parse(idls=[navigator_idl])
        self._check(parser_.global_module)

    def test_load(self):
        """load() with include_dirs reads the same files.

        include_dirs を指定した load() でも同じファイルが読まれる。
        """
        with open(navigator_idl) as f:
            m = parser.IDLParser().load(f.read(), include_dirs=include_dirs, filepath=navigator_idl)
        self._check(m)

    def test_parse_all_files(self):
        """Parsing every file in the directories defines each type once.

        ディレクトリ内の全ファイルを parse しても型は1回だけ定義される。
        """
        idls = [os.path.join(d, f) for d in include_dirs for f in sorted(os.listdir(d))
                if f.endswith('.idl')]
        parser_ = parser.IDLParser(idl_dirs=include_dirs)
        parser_.parse(idls=idls)
        self._check(parser_.global_module)
        self.assertEqual([t.name for t in parser_.global_module.module_by_name('geometry').typedefs],
                         ['PoseList'])

    def test_includes(self):
        """includes() finds files of other directories through the include directories.

        includes() が別ディレクトリのファイルを include ディレクトリから見つける。
        """
        parser_ = parser.IDLParser(idl_dirs=include_dirs)
        paths = parser_.includes(os.path.join(idl_root, 'geometry', 'path.idl'))
        self.assertEqual([os.path.normpath(p) for p in paths],
                         [os.path.join(idl_root, 'geometry', 'geometry.idl'),
                          os.path.join(idl_root, 'common', 'time.idl')])

    def test_missing_include_dir(self):
        """Without the directory of an included file, IDLCanNotFindException is raised.

        include 先のディレクトリが無いと IDLCanNotFindException になる。
        """
        parser_ = parser.IDLParser(idl_dirs=include_dirs[1:])
        with self.assertRaises(exception.IDLCanNotFindException):
            parser_.parse(idls=[navigator_idl])


if __name__ == '__main__':
    unittest.main()
