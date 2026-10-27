"""#include in #if / #ifdef / #elif / #else branches (issue #127)."""
import os
import shutil
import tempfile
import unittest
from idl_parser import parser, exception


class ConditionalIncludeTestFunctions(unittest.TestCase):
    """Category: Include and file loading / カテゴリ: include・ファイル読込

    An #include in a branch that is skipped is not read, and the branches
    are selected with the macros defined so far, also in included files
    (issue #127).
    読み飛ばす分岐の #include は読み込まない。分岐はその位置までに定義された
    マクロ(include したファイルのものも含む)で選ぶ(issue #127)。
    """

    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dir)

    def write(self, name, text):
        path = os.path.join(self.dir, name)
        with open(path, 'w') as f:
            f.write(text)
        return path

    def parse(self, path, **kwargs):
        p = parser.IDLParser(**kwargs)
        p.parse_idl(path)
        return p

    def struct_names(self, p):
        return [s.name for s in p.global_module.structs]

    def test_missing_file_in_skipped_ifdef(self):
        """A missing file in a skipped #ifdef branch is not searched.

        読み飛ばす #ifdef 分岐の存在しないファイルは探さない。
        """
        a = self.write('a.idl', '#ifdef UNDEFINED_MACRO\n#include "missing.idl"\n#endif\nstruct A {};\n')
        self.assertEqual(self.struct_names(self.parse(a)), ['A'])

    def test_missing_file_in_kept_branch(self):
        """A missing file in a kept branch is still an error.

        有効な分岐の存在しないファイルは今まで通りエラー。
        """
        a = self.write('a.idl', '#ifndef UNDEFINED_MACRO\n#include "missing.idl"\n#endif\nstruct A {};\n')
        with self.assertRaises(exception.IDLCanNotFindException) as cm:
            self.parse(a)
        self.assertEqual(cm.exception.line_number, 2)

    def test_if_0_not_parsed(self):
        """A file in an #if 0 branch is not parsed.

        #if 0 の中のファイルは解析しない。
        """
        other = self.write('other.idl', 'struct FromOther {};\n')
        b = self.write('b.idl', '#if 0\n#include "other.idl"\n#endif\nstruct B {};\n')
        p = self.parse(b)
        self.assertEqual(self.struct_names(p), ['B'])
        # It was not read, so it can still be parsed on its own.
        p.parse_idl(other)
        self.assertEqual(self.struct_names(p), ['B', 'FromOther'])

    def test_nested_skipped_branch(self):
        """An #include in a kept #if inside a skipped #if is not read.

        読み飛ばす #if の中の #if 1 にある #include も読まない。
        """
        a = self.write('a.idl', '#if 0\n#if 1\n#include "missing.idl"\n#endif\n#endif\nstruct A {};\n')
        self.assertEqual(self.struct_names(self.parse(a)), ['A'])

    def test_elif_else_select_file(self):
        """#if / #elif / #else select the file that is included.

        #if / #elif / #else で include するファイルが選ばれる。
        """
        self.write('x.idl', 'struct X {};\n')
        self.write('y.idl', 'struct Y {};\n')
        self.write('z.idl', 'struct Z {};\n')
        a = self.write('a.idl', '#if PLATFORM == 1\n#include "x.idl"\n'
                                '#elif PLATFORM == 2\n#include "y.idl"\n'
                                '#else\n#include "z.idl"\n#endif\n')
        self.assertEqual(self.struct_names(self.parse(a)), ['Z'])
        self.assertEqual(self.struct_names(self.parse(a, defines={'PLATFORM': 1})), ['X'])
        self.assertEqual(self.struct_names(self.parse(a, defines={'PLATFORM': 2})), ['Y'])

    def test_macro_of_including_file(self):
        """Macros defined before an #include are used in the included file.

        #include の前に定義したマクロが include したファイルの分岐に使われる。
        """
        self.write('inc.idl', '#ifdef WITH_EXTRA\nstruct Extra {};\n'
                              '#include "missing.idl"\n#endif\nstruct Inc {};\n')
        a = self.write('a.idl', '#include "inc.idl"\n')
        self.assertEqual(self.struct_names(self.parse(a)), ['Inc'])
        a2 = self.write('a2.idl', '#define WITH_EXTRA\n#include "inc.idl"\n')
        with self.assertRaises(exception.IDLCanNotFindException):
            self.parse(a2)

    def test_macro_of_included_file(self):
        """Macros defined in an included file are used after the #include.

        include したファイルで定義したマクロが #include の後の分岐に使われる。
        """
        self.write('config.idl', '#define USE_B 1\n')
        self.write('b.idl', 'struct B {};\n')
        a = self.write('a.idl', '#include "config.idl"\n#if USE_B\n#include "b.idl"\n#endif\n'
                                '#ifndef USE_B\n#include "missing.idl"\n#endif\n')
        self.assertEqual(self.struct_names(self.parse(a)), ['B'])

    def test_include_guard(self):
        """Include guards still work, also for a diamond include.

        インクルードガードは菱形の include でも今まで通り動く。
        """
        self.write('base.idl', '#ifndef BASE_IDL\n#define BASE_IDL\nstruct Base {};\n#endif\n')
        self.write('l.idl', '#ifndef L_IDL\n#define L_IDL\n#include "base.idl"\nstruct L { Base b; };\n#endif\n')
        self.write('r.idl', '#ifndef R_IDL\n#define R_IDL\n#include "base.idl"\nstruct R { Base b; };\n#endif\n')
        top = self.write('top.idl', '#include "l.idl"\n#include "r.idl"\nstruct Top { L l; R r; };\n')
        p = self.parse(top)
        self.assertEqual(self.struct_names(p), ['Base', 'L', 'R', 'Top'])
        self.assertEqual(os.path.basename(p.global_module.struct_by_name('Base').filepath), 'base.idl')

    def test_included_file_is_parsed(self):
        """A file pasted by #include is not parsed again on its own.

        #include で読み込んだファイルを単独で再度解析しない。
        """
        inc = self.write('inc.idl', 'struct Inc {};\n')
        a = self.write('a.idl', '#include "inc.idl"\nstruct A { Inc i; };\n')
        p = self.parse(a)
        p.parse_idl(inc)
        self.assertEqual(self.struct_names(p), ['Inc', 'A'])

    def test_unbalanced_if_in_included_file(self):
        """An #if without #endif in an included file is an error of that file.

        include したファイル内の #endif のない #if はそのファイルのエラー。
        """
        self.write('inc.idl', '#ifdef X\nstruct Inc {};\n')
        a = self.write('a.idl', '#include "inc.idl"\n#endif\n')
        with self.assertRaises(exception.InvalidIDLSyntaxError) as cm:
            self.parse(a)
        self.assertEqual(os.path.basename(cm.exception.file_name), 'inc.idl')
        self.assertEqual(cm.exception.line_number, 1)

    def test_load_string(self):
        """load() also ignores an #include in a skipped branch.

        load() でも読み飛ばす分岐の #include は無視する。
        """
        gm = parser.IDLParser().load('#ifdef X\n#include "missing.idl"\n#endif\nstruct A {};\n')
        self.assertEqual([s.name for s in gm.structs], ['A'])


if __name__ == '__main__':
    unittest.main()
