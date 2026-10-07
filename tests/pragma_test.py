"""Tests for #pragma handling (issues #10 and #28)."""
import os
import tempfile
import unittest
import warnings

from idl_parser import parser
from idl_parser.pragma import KeylistWarning

IDL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'idls')


def load(text):
    p = parser.IDLParser()
    return p, p.load(text)


class PragmaTest(unittest.TestCase):

    def setUp(self):
        self.parser = parser.IDLParser()
        with open(os.path.join(IDL_DIR, 'issue28_pragma_keylist.idl'), 'r') as f:
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
        with open(os.path.join(IDL_DIR, 'issue9_const_pragma.idl'), 'r') as f:
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


class KeylistValidationTest(unittest.TestCase):
    """Key names of #pragma keylist are checked against the struct (issue #38)."""

    PREFIX = ('module M {\n'
              '  struct In { long x; };\n'
              '  typedef In InT;\n'
              '  typedef InT InT2;\n'
              '  struct S { long id; In a; InT2 t; long c; sequence<In> q; };\n')

    def keylist(self, keys):
        idl = self.PREFIX + '#pragma keylist S %s\n};\n' % keys
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always')
            p, g = load(idl)
        found = [x for x in w if issubclass(x.category, KeylistWarning)]
        return p.pragmas[0], g.module_by_name('M').struct_by_name('S'), found

    def test_existing_key_has_no_warning(self):
        pragma, s, w = self.keylist('id')
        self.assertEqual(w, [])
        self.assertEqual(pragma.unresolved_keys, [])
        self.assertEqual(s.keys, ['id'])

    def test_missing_key_warns_and_is_kept(self):
        pragma, s, w = self.keylist('id nosuch')
        self.assertEqual(len(w), 1)
        msg = str(w[0].message)
        self.assertIn("'nosuch'", msg)
        self.assertIn('M::S', msg)
        self.assertIn('line 6', msg)
        self.assertEqual(pragma.unresolved_keys, ['nosuch'])
        # kept as written so that existing IDL files keep working
        self.assertEqual(s.keys, ['id', 'nosuch'])

    def test_nested_member(self):
        pragma, s, w = self.keylist('a.x t.x')
        self.assertEqual(w, [])
        self.assertEqual(pragma.unresolved_keys, [])
        self.assertEqual(s.keys, ['a.x', 't.x'])

    def test_missing_nested_member(self):
        pragma, s, w = self.keylist('a.y')
        self.assertEqual(len(w), 1)
        self.assertEqual(pragma.unresolved_keys, ['a.y'])

    def test_nested_through_non_struct(self):
        pragma, s, w = self.keylist('c.x q.x')
        self.assertEqual(len(w), 2)
        self.assertEqual(pragma.unresolved_keys, ['c.x', 'q.x'])

    def test_malformed_dotted_names(self):
        pragma, s, w = self.keylist('a. .id a..x')
        self.assertEqual(pragma.unresolved_keys, ['a.', '.id', 'a..x'])

    def test_unknown_target_is_not_checked(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always')
            p, g = load('#pragma keylist Missing id\n')
        self.assertEqual([x for x in w if issubclass(x.category, KeylistWarning)], [])
        self.assertIsNone(p.pragmas[0].unresolved_keys)

    def test_other_pragma(self):
        p, g = load('#pragma prefix "foo"\n')
        self.assertIsNone(p.pragmas[0].unresolved_keys)

    def test_warning_names_file(self):
        d = tempfile.mkdtemp()
        path = os.path.join(d, 'topic.idl')
        with open(path, 'w') as f:
            f.write('struct S { long id; };\n#pragma keylist S nosuch\n')
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always')
            parser.IDLParser([d]).parse(idls=[path])
        w = [x for x in w if issubclass(x.category, KeylistWarning)]
        self.assertEqual(len(w), 1)
        self.assertIn('topic.idl', str(w[0].message))


if __name__ == '__main__':
    unittest.main()
