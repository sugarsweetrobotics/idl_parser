"""Tests for #pragma handling (issues #10 and #28)."""
import os
import tempfile
import unittest

from idl_parser import parser


def load(text):
    p = parser.IDLParser()
    return p, p.load(text)


class PragmaTest(unittest.TestCase):

    def setUp(self):
        self.parser = parser.IDLParser()
        with open('idls/issue28_pragma_keylist.idl', 'r') as f:
            self.g = self.parser.load(f.read())
        self.m = self.g.module_by_name('M')

    def test_pragma_inside_struct_does_not_break_members(self):
        s = self.m.struct_by_name('A')
        self.assertEqual([(mb.name, str(mb.type)) for mb in s.members],
                         [('id', 'long'), ('x', 'long')])

    def test_keylist(self):
        self.assertEqual(self.m.struct_by_name('A').keys, ['id'])
        self.assertTrue(self.m.struct_by_name('A').has_keylist)

    def test_multiple_keys(self):
        self.assertEqual(self.m.struct_by_name('Multi').keys, ['a', 'b'])

    def test_keylist_without_keys(self):
        s = self.m.struct_by_name('NoKey')
        self.assertTrue(s.has_keylist)
        self.assertEqual(s.keys, [])

    def test_struct_without_keylist(self):
        p, g = load('struct S { long a; };\n')
        self.assertFalse(g.struct_by_name('S').has_keylist)
        self.assertEqual(g.struct_by_name('S').keys, [])
        self.assertNotIn('keys', g.struct_by_name('S').to_dic())

    def test_keylist_is_resolved_in_enclosing_module(self):
        s = self.m.module_by_name('Inner').struct_by_name('A')
        self.assertEqual(s.keys, ['inner_id'])
        # an unrelated struct with the same name in the outer module is not affected
        self.assertEqual(self.m.struct_by_name('A').keys, ['id'])

    def test_keylist_before_struct_definition(self):
        self.assertEqual(self.m.struct_by_name('Later').keys, ['id'])

    def test_absolute_name(self):
        self.assertEqual(self.m.struct_by_name('Plain').keys, ['v'])

    def test_keys_in_to_dic(self):
        self.assertEqual(self.m.struct_by_name('Multi').to_dic()['keys'], ['a', 'b'])

    def test_pragmas_are_recorded(self):
        names = [p.name for p in self.parser.pragmas]
        self.assertEqual(names.count('keylist'), 6)
        self.assertIn('prefix', names)
        self.assertIn('vendor', names)
        self.assertTrue(all(p.target is not None
                            for p in self.parser.pragmas if p.is_keylist))
        inner = [p for p in self.parser.pragmas if p.keys == ['inner_id']][0]
        self.assertEqual(inner.scope, ['M', 'Inner'])

    def test_unknown_target_is_kept_unresolved(self):
        p, g = load('#pragma keylist Missing id\nstruct S { long id; };\n')
        self.assertIsNone(p.pragmas[0].target)
        self.assertFalse(g.struct_by_name('S').has_keylist)

    def test_pragma_with_keyword_arguments_at_module_level(self):
        p, g = load('module M {\n#pragma foo struct bar\n struct S { long a; };\n};\n')
        self.assertEqual([m.name for m in g.module_by_name('M').struct_by_name('S').members], ['a'])

    def test_pragma_variants(self):
        p, g = load('struct S {\n  long a;\n  # pragma keylist S a\n  long b; // c\n};\n')
        self.assertEqual([str(m.type) for m in g.struct_by_name('S').members], ['long', 'long'])
        self.assertEqual(g.struct_by_name('S').keys, ['a'])

    def test_pragma_inside_inactive_ifdef_is_ignored(self):
        p, g = load('#ifdef NOT_DEFINED\n#pragma keylist S a\n#endif\nstruct S { long a; };\n')
        self.assertFalse(g.struct_by_name('S').has_keylist)
        self.assertEqual(p.pragmas, [])

    def test_issue9_idl_keys(self):
        with open('idls/issue9_const_pragma.idl', 'r') as f:
            g = parser.IDLParser().load(f.read())
        for st in g.structs:
            self.assertEqual(st.keys, ['WatcherID'])

    def test_keylist_across_files(self):
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
