"""Key names of #pragma keylist are checked against the struct (issue #38)."""
import os
import tempfile
import unittest
import warnings

from idl_parser import parser
from idl_parser.pragma import KeylistWarning


def load(text):
    p = parser.IDLParser()
    return p, p.load(text)


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
