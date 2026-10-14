"""parse_dirs(): parse every IDL file in directories (issue #108)."""
import os
import shutil
import tempfile
import unittest
from idl_parser import parser
from tests import support

idl_root = os.path.join(support.IDL_DIR, 'multi_include_dirs')
include_dirs = [os.path.join(idl_root, d) for d in ('common', 'geometry', 'navigation')]


def _all_names(m):
    return sorted('%s::%s' % (mod.name, x.name) for mod in m.modules
                  for x in mod.structs + mod.typedefs + mod.interfaces)


class ParseDirsTest(unittest.TestCase):
    """Category: Include and file loading / カテゴリ: include・ファイル読込

    parse_dirs() parses the IDL files found in directories.
    parse_dirs() はディレクトリ内の IDL ファイルをパースする。
    """

    def test_parse_dirs(self):
        """parse_dirs() alone parses every file, and each type is defined once.

        parse_dirs() だけで全ファイルがパースされ、型は1回だけ定義される。
        """
        p = parser.IDLParser()
        found = p.parse_dirs(include_dirs)
        self.assertEqual([os.path.relpath(f, idl_root).replace(os.sep, '/') for f in found],
                         ['common/time.idl', 'geometry/geometry.idl', 'geometry/path.idl',
                          'navigation/navigator.idl'])
        self.assertEqual(_all_names(p.global_module),
                         ['common::Time', 'geometry::Path', 'geometry::Point', 'geometry::Pose',
                          'geometry::PoseList', 'navigation::Navigator'])
        pose = p.global_module.module_by_name('geometry').struct_by_name('Pose')
        self.assertEqual(pose.member_by_name('stamp').type.full_path, 'common::Time')

    def test_same_as_parse_of_all_files(self):
        """parse_dirs() gives the same result as parse() of the listed files.

        parse_dirs() はファイルを列挙した parse() と同じ結果になる。
        """
        p1 = parser.IDLParser()
        idls = p1.parse_dirs(include_dirs)
        p2 = parser.IDLParser(idl_dirs=include_dirs)
        p2.parse(idls=idls)
        self.assertEqual(p1.global_module.to_simple_dic(), p2.global_module.to_simple_dic())

    def test_dirs_are_include_dirs(self):
        """The directories are added to the include directories.

        渡したディレクトリは include の検索先にも追加される。
        """
        p = parser.IDLParser(idl_dirs=include_dirs[:1])
        p.parse_dirs(include_dirs[1:])
        self.assertEqual(p.dirs, include_dirs)
        self.assertEqual(sorted(m.name for m in p.global_module.modules),
                         ['common', 'geometry', 'navigation'])

    def test_constructor_dirs_are_not_parsed(self):
        """Only the given directories are listed, not the include directories.

        列挙されるのは渡したディレクトリだけで、include の検索先は列挙されない。
        """
        p = parser.IDLParser(idl_dirs=include_dirs)
        found = p.parse_dirs(include_dirs[:1])
        self.assertEqual([os.path.basename(f) for f in found], ['time.idl'])
        self.assertEqual([m.name for m in p.global_module.modules], ['common'])

    def test_except_files(self):
        """except_files skips files by name.

        except_files に書いたファイル名はスキップされる。
        """
        p = parser.IDLParser()
        found = p.parse_dirs(include_dirs, except_files=['navigator.idl'])
        self.assertEqual([os.path.basename(f) for f in found],
                         ['time.idl', 'geometry.idl', 'path.idl'])
        self.assertEqual(sorted(m.name for m in p.global_module.modules), ['common', 'geometry'])

    def test_not_recursive_and_only_idl(self):
        """Sub directories and files other than *.idl are not read.

        サブディレクトリと *.idl 以外のファイルは読まれない。
        """
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        shutil.copy(os.path.join(include_dirs[0], 'time.idl'), tmp)
        os.mkdir(os.path.join(tmp, 'sub'))
        os.mkdir(os.path.join(tmp, 'dir.idl'))
        with open(os.path.join(tmp, 'sub', 'other.idl'), 'w') as f:
            f.write('module other { struct A { long a; }; };\n')
        with open(os.path.join(tmp, 'notes.txt'), 'w') as f:
            f.write('not idl\n')
        p = parser.IDLParser()
        found = p.parse_dirs([tmp])
        self.assertEqual(found, [os.path.join(os.path.abspath(tmp), 'time.idl')])
        self.assertEqual([m.name for m in p.global_module.modules], ['common'])

    def test_relative_dirs(self):
        """Relative directories give the same result, and each file is read once.

        相対パスのディレクトリでも同じ結果になり、各ファイルは1回だけ読まれる。
        """
        cwd = os.getcwd()
        os.chdir(idl_root)
        self.addCleanup(os.chdir, cwd)
        p = parser.IDLParser()
        found = p.parse_dirs(['common', 'geometry', 'navigation'])
        self.assertEqual(found, [os.path.join(idl_root, 'common', 'time.idl'),
                                 os.path.join(idl_root, 'geometry', 'geometry.idl'),
                                 os.path.join(idl_root, 'geometry', 'path.idl'),
                                 os.path.join(idl_root, 'navigation', 'navigator.idl')])
        self.assertEqual(sorted(p._parsed_files), sorted(found))
        p_abs = parser.IDLParser()
        p_abs.parse_dirs(include_dirs)
        self.assertEqual(p.global_module.to_simple_dic(), p_abs.global_module.to_simple_dic())

    def test_missing_dir(self):
        """A directory that does not exist raises FileNotFoundError before parsing.

        存在しないディレクトリでは何もパースせず FileNotFoundError になる。
        """
        p = parser.IDLParser()
        missing = os.path.join(idl_root, 'no_such_dir')
        with self.assertRaises(FileNotFoundError):
            p.parse_dirs([include_dirs[0], missing])
        self.assertEqual(p.global_module.modules, [])
        self.assertEqual(p.dirs, [])

    def test_called_again(self):
        """Calling parse_dirs() again, or after parse(), parses nothing twice.

        parse_dirs() を再度呼んでも、parse() の後に呼んでも二重にパースされない。
        """
        p = parser.IDLParser()
        p.parse_dirs(include_dirs)
        before = p.global_module.to_simple_dic()
        parsed = list(p._parsed_files)
        self.assertEqual(len(parsed), 4)
        p.parse_dirs(include_dirs)
        self.assertEqual(p._parsed_files, parsed)
        self.assertEqual(p.global_module.to_simple_dic(), before)

        p2 = parser.IDLParser(idl_dirs=include_dirs)
        p2.parse(idls=[os.path.join(include_dirs[2], 'navigator.idl')])
        p2.parse_dirs(include_dirs)
        self.assertEqual(sorted(p2._parsed_files), sorted(parsed))
        self.assertEqual(p2.global_module.to_simple_dic(), before)

    def test_parse_idl_dirs_unchanged(self):
        """parse(idl_dirs=...) still only adds include directories.

        parse(idl_dirs=...) はこれまでどおり include の検索先を追加するだけ。
        """
        p = parser.IDLParser()
        p.parse(idl_dirs=include_dirs)
        self.assertEqual(p.global_module.modules, [])
        self.assertEqual(p.dirs, include_dirs)


if __name__ == '__main__':
    unittest.main()
