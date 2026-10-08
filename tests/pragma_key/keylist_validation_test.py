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
    """Category: #pragma and keys / カテゴリ: #pragma・キー

    Key names of #pragma keylist are checked against the struct (issue #38).
    #pragma keylist のキー名を struct のメンバーと照合する(#38)。
    """

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
        """No warning for a key that exists.

        存在するキーなら警告なし。
        """
        pragma, s, w = self.keylist('id')
        self.assertEqual(w, [])
        self.assertEqual(pragma.unresolved_keys, [])
        self.assertEqual(s.keys, ['id'])

    def test_missing_key_warns_and_is_kept(self):
        """A missing key issues a KeylistWarning (with target and line number) and is kept in keys.

        存在しないキーは KeylistWarning(対象名・行番号付き)を出し、キーには残す。
        """
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
        """Keys on nested members such as a.x.

        a.x のような入れ子メンバーのキー。
        """
        pragma, s, w = self.keylist('a.x t.x')
        self.assertEqual(w, [])
        self.assertEqual(pragma.unresolved_keys, [])
        self.assertEqual(s.keys, ['a.x', 't.x'])

    def test_missing_nested_member(self):
        """A missing nested member issues a warning.

        存在しない入れ子メンバーで警告。
        """
        pragma, s, w = self.keylist('a.y')
        self.assertEqual(len(w), 1)
        self.assertEqual(pragma.unresolved_keys, ['a.y'])

    def test_nested_through_non_struct(self):
        """A nested key through a non-struct member issues a warning.

        struct 以外を経由する入れ子キーで警告。
        """
        pragma, s, w = self.keylist('c.x q.x')
        self.assertEqual(len(w), 2)
        self.assertEqual(pragma.unresolved_keys, ['c.x', 'q.x'])

    def test_malformed_dotted_names(self):
        """Malformed dotted names such as "a.", ".id" and "a..x" are unresolved.

        a. や .id や a..x のような不正なドット区切りは未解決扱い。
        """
        pragma, s, w = self.keylist('a. .id a..x')
        self.assertEqual(pragma.unresolved_keys, ['a.', '.id', 'a..x'])

    def test_unknown_target_is_not_checked(self):
        """Keys are not checked when the keylist target is unknown.

        対象が不明な keylist はキーの検査をしない。
        """
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always')
            p, g = load('#pragma keylist Missing id\n')
        self.assertEqual([x for x in w if issubclass(x.category, KeylistWarning)], [])
        self.assertIsNone(p.pragmas[0].unresolved_keys)

    def test_other_pragma(self):
        """Pragmas other than keylist are not checked.

        keylist 以外の #pragma は検査しない。
        """
        p, g = load('#pragma prefix "foo"\n')
        self.assertIsNone(p.pragmas[0].unresolved_keys)

    def test_warning_names_file(self):
        """The warning message names the file.

        警告メッセージにファイル名が入る。
        """
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
