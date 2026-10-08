"""Tests for #pragma handling and #pragma keylist (issues #10 and #28)."""
import os
import tempfile
import unittest

from idl_parser import parser
from tests import support

IDL_DIR = support.IDL_DIR


def load(text):
    p = parser.IDLParser()
    return p, p.load(text)


class PragmaTest(unittest.TestCase):
    """Category: #pragma and keys / カテゴリ: #pragma・キー

    #pragma handling and #pragma keylist (issues #10, #28).
    #pragma の扱いと #pragma keylist(#10, #28)。
    """

    def setUp(self):
        self.parser = parser.IDLParser()
        with open(os.path.join(IDL_DIR, 'issue28_pragma_keylist.idl'), 'r') as f:
            self.g = self.parser.load(f.read())
        self.m = self.g.module_by_name('M')

    def test_pragma_inside_struct_does_not_break_members(self):
        """#pragma inside a struct does not break member parsing (issue #10).

        struct 内の #pragma でメンバー解析が壊れない(#10)。
        """
        s = self.m.struct_by_name('A')
        self.assertEqual([(mb.name, str(mb.type)) for mb in s.members],
                         [('id', 'long'), ('x', 'long')])

    def test_keylist(self):
        """#pragma keylist sets the keys.

        #pragma keylist でキーが設定される。
        """
        self.assertEqual(self.m.struct_by_name('A').keys, ['id'])
        self.assertTrue(self.m.struct_by_name('A').has_keylist)

    def test_multiple_keys(self):
        """A keylist with several keys.

        keylist の複数キー。
        """
        self.assertEqual(self.m.struct_by_name('Multi').keys, ['a', 'b'])

    def test_keylist_without_keys(self):
        """A keylist without keys: has_keylist is true and keys is empty.

        キーなしの keylist は has_keylist が真で keys が空。
        """
        s = self.m.struct_by_name('NoKey')
        self.assertTrue(s.has_keylist)
        self.assertEqual(s.keys, [])

    def test_struct_without_keylist(self):
        """A struct without keylist: has_keylist is false and to_dic() has no keys.

        keylist がない struct は has_keylist が偽で to_dic に keys なし。
        """
        p, g = load('struct S { long a; };\n')
        self.assertFalse(g.struct_by_name('S').has_keylist)
        self.assertEqual(g.struct_by_name('S').keys, [])
        self.assertNotIn('keys', g.struct_by_name('S').to_dic())

    def test_keylist_is_resolved_in_enclosing_module(self):
        """The keylist target is resolved in the module where the pragma is written.

        keylist の対象名は pragma を書いたモジュールで解決される。
        """
        s = self.m.module_by_name('Inner').struct_by_name('A')
        self.assertEqual(s.keys, ['inner_id'])
        # an unrelated struct with the same name in the outer module is not affected
        self.assertEqual(self.m.struct_by_name('A').keys, ['id'])

    def test_keylist_before_struct_definition(self):
        """A keylist written before the struct definition.

        struct 定義より前に書いた keylist。
        """
        self.assertEqual(self.m.struct_by_name('Later').keys, ['id'])

    def test_absolute_name(self):
        """A keylist target given by absolute name.

        keylist の対象を絶対名で指定。
        """
        self.assertEqual(self.m.struct_by_name('Plain').keys, ['v'])

    def test_keys_in_to_dic(self):
        """to_dic() contains the keys from keylist.

        to_dic() に keylist のキーが出る。
        """
        self.assertEqual(self.m.struct_by_name('Multi').to_dic()['keys'], ['a', 'b'])

    def test_pragmas_are_recorded(self):
        """Every #pragma is recorded in parser.pragmas with its name, target and scope.

        全 #pragma が parser.pragmas に名前・対象・スコープ付きで記録される。
        """
        names = [p.name for p in self.parser.pragmas]
        self.assertEqual(names.count('keylist'), 6)
        self.assertIn('prefix', names)
        self.assertIn('vendor', names)
        self.assertTrue(all(p.target is not None
                            for p in self.parser.pragmas if p.is_keylist))
        inner = [p for p in self.parser.pragmas if p.keys == ['inner_id']][0]
        self.assertEqual(inner.scope, ['M', 'Inner'])

    def test_unknown_target_is_kept_unresolved(self):
        """A keylist for a missing target keeps target None.

        存在しない対象の keylist は target=None のまま。
        """
        p, g = load('#pragma keylist Missing id\nstruct S { long id; };\n')
        self.assertIsNone(p.pragmas[0].target)
        self.assertFalse(g.struct_by_name('S').has_keylist)

    def test_pragma_with_keyword_arguments_at_module_level(self):
        """A #pragma containing keywords such as struct is not taken as a definition.

        struct などのキーワードを含む #pragma が定義と誤認されない。
        """
        p, g = load('module M {\n#pragma foo struct bar\n struct S { long a; };\n};\n')
        self.assertEqual([m.name for m in g.module_by_name('M').struct_by_name('S').members], ['a'])

    def test_pragma_variants(self):
        """Variants such as "# pragma" with a space and trailing comments.

        「# pragma」の空白や行末コメントなどの表記揺れ。
        """
        p, g = load('struct S {\n  long a;\n  # pragma keylist S a\n  long b; // c\n};\n')
        self.assertEqual([str(m.type) for m in g.struct_by_name('S').members], ['long', 'long'])
        self.assertEqual(g.struct_by_name('S').keys, ['a'])

    def test_pragma_inside_inactive_ifdef_is_ignored(self):
        """#pragma inside an inactive #ifdef is ignored.

        無効な #ifdef 内の #pragma は無視される。
        """
        p, g = load('#ifdef NOT_DEFINED\n#pragma keylist S a\n#endif\nstruct S { long a; };\n')
        self.assertFalse(g.struct_by_name('S').has_keylist)
        self.assertEqual(p.pragmas, [])

    def test_issue9_idl_keys(self):
        """The keylists of the IDL from issue #9.

        issue #9 の IDL の keylist。
        """
        with open(os.path.join(IDL_DIR, 'issue9_const_pragma.idl'), 'r') as f:
            g = parser.IDLParser().load(f.read())
        for st in g.structs:
            self.assertEqual(st.keys, ['WatcherID'])

    def test_keylist_across_files(self):
        """A keylist applied to a struct in an included file.

        include した別ファイルの struct に keylist を適用。
        """
        d = tempfile.mkdtemp()
        with open(os.path.join(d, 'types.idl'), 'w') as f:
            f.write('module T {\n  struct S { long id; };\n};\n')
        with open(os.path.join(d, 'topics.idl'), 'w') as f:
            f.write('#include "types.idl"\n#pragma keylist T::S id\n')
        p = parser.IDLParser([d])
        p.parse(idls=[os.path.join(d, 'topics.idl')])
        s = p.global_module.module_by_name('T').struct_by_name('S')
        self.assertEqual(s.keys, ['id'])
        self.assertEqual(len([x for x in p.pragmas if x.is_keylist]), 1)


if __name__ == '__main__':
    unittest.main()
