"""IDLCanNotFindException for a missing #include names the file (issue #110)."""
import os
import shutil
import tempfile
import unittest
from idl_parser import parser, exception


class MissingIncludeTestFunctions(unittest.TestCase):
    """Category: Include and file loading / カテゴリ: include・ファイル読込

    A missing #include names the file, the place of the #include and the
    searched directories (issue #110).
    見つからない #include のファイル名、#include の位置、探したディレクトリが
    例外に含まれる(issue #110)。
    """

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.inc_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dir)
        shutil.rmtree(self.inc_dir)

    def write(self, name, text, d=None):
        path = os.path.join(d or self.dir, name)
        with open(path, 'w') as f:
            f.write(text)
        return path

    def test_load_string(self):
        """A missing #include in a string names the file and the line.

        文字列中の見つからない #include のファイル名と行番号。
        """
        with self.assertRaises(exception.IDLCanNotFindException) as cm:
            parser.IDLParser().load('module a {};\n#include "nothere.idl"\n')
        e = cm.exception
        self.assertEqual(e.line_number, 2)
        self.assertIn('"nothere.idl"', str(e))
        self.assertIn('line 2', str(e))

    def test_nested_include(self):
        """A missing #include in an included file names that file and line.

        include されたファイル中の見つからない #include は、そのファイルと行を示す。
        """
        self.write('b.idl', 'module b {};\n\n#include <common/gone.idl>\n', self.inc_dir)
        a = self.write('a.idl', '#include "b.idl"\nmodule a {};\n')
        with self.assertRaises(exception.IDLCanNotFindException) as cm:
            parser.IDLParser(idl_dirs=[self.inc_dir]).parse_idl(a)
        e = cm.exception
        self.assertEqual(e.file_name, os.path.join(self.inc_dir, 'b.idl'))
        self.assertEqual(e.line_number, 3)
        self.assertIn('"common/gone.idl"', str(e))
        self.assertIn(self.inc_dir, str(e))

    def test_searched_dirs(self):
        """The message lists the including file's directory and the include dirs.

        メッセージに include 元のディレクトリと include ディレクトリが並ぶ。
        """
        a = self.write('a.idl', '#include "nothere.idl"\n')
        with self.assertRaises(exception.IDLCanNotFindException) as cm:
            parser.IDLParser(idl_dirs=[self.inc_dir]).parse_idl(a)
        msg = str(cm.exception)
        self.assertIn('File "%s", line 1' % a, msg)
        self.assertIn(os.path.dirname(os.path.abspath(a)), msg)
        self.assertIn(self.inc_dir, msg)

    def test_includes(self):
        """IDLParser.includes() names the missing file and its line too.

        IDLParser.includes() も見つからないファイル名と行番号を示す。
        """
        a = self.write('a.idl', 'module a {};\n#include "nothere.idl"\n')
        with self.assertRaises(exception.IDLCanNotFindException) as cm:
            parser.IDLParser().includes(a)
        e = cm.exception
        self.assertEqual(e.file_name, a)
        self.assertEqual(e.line_number, 2)
        self.assertIn('"nothere.idl"', str(e))


if __name__ == '__main__':
    unittest.main()
