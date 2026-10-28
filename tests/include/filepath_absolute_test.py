"""Tests for issue #142: file paths are absolute, and a reopened module
lists every file it is opened in.

The filepath of a definition in an included file was absolute, but that of
a definition in the file given to parse_idl() was the path as given
(relative), and a module opened in several files had the filepath of the
last one. Now every filepath is absolute, a module keeps the file where it
is first opened, and IDLModule.filepaths lists all of them.
"""
import os
import shutil
import tempfile
import unittest

from idl_parser import parser


class FilepathAbsoluteTest(unittest.TestCase):
    """Category: Include and file loading / カテゴリ: include・ファイル読込

    Absolute file paths and the files of a reopened module (issue #142).
    絶対パスの filepath と、再オープンしたモジュールのファイル一覧(#142)。
    """

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.cwd = os.getcwd()
        with open(os.path.join(self.dir, 'base.idl'), 'w') as f:
            f.write('module Base { struct P { long x; }; };\n')
        with open(os.path.join(self.dir, 'main.idl'), 'w') as f:
            f.write('#include "base.idl"\nmodule Base { struct P2 { long y; }; };\n'
                    '#pragma keylist Base::P2 y\n')
        os.chdir(self.dir)  # so that "main.idl" is a relative path

    def tearDown(self):
        os.chdir(self.cwd)
        shutil.rmtree(self.dir)

    def parse(self):
        p = parser.IDLParser()
        p.parse_idl('main.idl')
        return p

    def test_same_form(self):
        """Definitions of the main and the included file have absolute paths. / 主ファイルと include 先の定義のパスが、どちらも絶対パス。"""
        base = self.parse().global_module.module_by_name('Base')
        p, p2 = base.struct_by_name('P'), base.struct_by_name('P2')
        self.assertEqual(p.filepath, os.path.abspath('base.idl'))
        self.assertEqual(p2.filepath, os.path.abspath('main.idl'))
        self.assertTrue(os.path.isabs(p2.member_by_name('y').filepath))

    def test_reopened_module(self):
        """A reopened module has the first file and lists every file. / 再オープンしたモジュールは最初のファイルを持ち、全ファイルを並べる。"""
        base = self.parse().global_module.module_by_name('Base')
        self.assertEqual(os.path.basename(base.filepath), 'base.idl')
        self.assertEqual([os.path.basename(f) for f in base.filepaths], ['base.idl', 'main.idl'])
        self.assertTrue(all(os.path.isabs(f) for f in base.filepaths))

    def test_pragma(self):
        """Pragmas have absolute paths too. / pragma のパスも絶対パス。"""
        p = self.parse()
        self.assertTrue(os.path.isabs(p.pragmas[0].filepath))

    def test_load_with_relative_filepath(self):
        """load(filepath=...) makes the path absolute. / load(filepath=...) のパスも絶対パスになる。"""
        g = parser.IDLParser().load('module A { struct S { long a; }; };', filepath='a.idl')
        s = g.module_by_name('A').struct_by_name('S')
        self.assertEqual(s.filepath, os.path.abspath('a.idl'))
        self.assertEqual(g.module_by_name('A').filepaths, [os.path.abspath('a.idl')])

    def test_load_without_filepath(self):
        """Without filepath, filepath stays None and filepaths is empty. / filepath なしなら None のまま、filepaths は空。"""
        g = parser.IDLParser().load('module A { struct S { long a; }; };')
        self.assertIsNone(g.module_by_name('A').filepath)
        self.assertEqual(g.module_by_name('A').filepaths, [])

    def test_module_in_two_parses(self):
        """A module opened by two parse_idl() calls lists both files. / 2 回の parse_idl() で開いたモジュールは両方のファイルを並べる。"""
        with open('other.idl', 'w') as f:
            f.write('module Base { struct P3 { long z; }; };\n')
        p = self.parse()
        p.parse_idl('other.idl')
        base = p.global_module.module_by_name('Base')
        self.assertEqual([os.path.basename(f) for f in base.filepaths], ['base.idl', 'main.idl', 'other.idl'])
        self.assertEqual(os.path.basename(p.global_module.filepath), 'main.idl')


if __name__ == '__main__':
    unittest.main()
