"""Regression tests for issue #76.

An unknown word in a module or the global scope (e.g. a misspelled keyword,
"strcut S { ... };") was dropped silently, together with the "{ ... }" block
after it. It is still skipped, for compatibility, but now with an
UnknownIDLSyntaxWarning; it will be an InvalidIDLSyntaxError in a future
release. Valid definitions that are not supported yet (valuetype,
component, ...) are skipped with an UnsupportedIDLSyntaxWarning.
"""
import os
import unittest
import warnings
from idl_parser import parser
from idl_parser.exception import (IDLParserWarning, UnknownIDLSyntaxWarning,
                                  UnsupportedIDLSyntaxWarning)
from tests import support


def load(idl, filepath=None):
    """Parse ``idl`` and return (global module, list of idl_parser warnings)."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        g = parser.IDLParser().load(idl, filepath=filepath)
    return g, [w for w in caught if issubclass(w.category, IDLParserWarning)]


TYPOS = {
    # IDL -> (unknown word, line, expected to_simple_dic())
    'missing_space_after_module': ('moduleA { struct S { long x; }; };',
                                   'moduleA', {'module __global__': []}),
    'struct': ('module M { strcut S { long x; }; };',
               'strcut', {'module __global__': [{'module M': []}]}),
    'interface': ('module M { interfce I { void f(); }; };',
                  'interfce', {'module __global__': [{'module M': []}]}),
    'declaration': ('module M { foo bar; struct T { long y; }; };',
                    'foo', {'module __global__': [{'module M': [{'struct T': [{'y': 'long'}]}]}]}),
}

UNSUPPORTED = {
    'valuetype': 'valuetype V { public long x; };',
    'abstract_valuetype': 'abstract valuetype V { };',
    'boxed_valuetype': 'valuetype V long;',
    'eventtype': 'eventtype E { public long x; };',
    'component': 'component C { provides I p; };',
    'home': 'home H manages C { };',
    'typeprefix': 'typeprefix M "example.com";',
}


class UnknownWordTest(unittest.TestCase):
    """Category: Modules, scopes and type name resolution / カテゴリ: モジュール・スコープ・型名解決

    An unknown word is skipped with a warning, not silently (issue #76).
    未知の語は黙って捨てずに警告を出して読み飛ばす(#76)。
    """

    def test_unknown_word_warns(self):
        """A misspelled keyword gives an UnknownIDLSyntaxWarning naming the word.

        キーワードの書き間違いで、その語を示す UnknownIDLSyntaxWarning が出る。
        """
        for label, (idl, word, _) in TYPOS.items():
            with self.subTest(label):
                _, ws = load(idl)
                self.assertEqual([w.category for w in ws], [UnknownIDLSyntaxWarning])
                self.assertIn('"%s"' % word, str(ws[0].message))
                self.assertIn('line 1', str(ws[0].message))

    def test_result_is_unchanged(self):
        """The definition is still skipped as before (compatibility for this release).

        定義は従来どおり読み飛ばす(このリリースでは互換性を保つ)。
        """
        for label, (idl, _, expected) in TYPOS.items():
            with self.subTest(label):
                g, _ = load(idl)
                self.assertEqual(g.to_simple_dic(), expected)

    def test_message_has_file_and_line(self):
        """The warning names the file and the line of the unknown word.

        警告にファイル名と未知の語の行番号が入る。
        """
        _, ws = load('module M {\n  struct A { long a; };\n  strcut S {\n    long x;\n  };\n};',
                     filepath='typo.idl')
        self.assertEqual(len(ws), 1)
        self.assertIn('File "typo.idl", line 3', str(ws[0].message))
        self.assertIn('module M', str(ws[0].message))

    def test_warning_points_at_the_caller(self):
        """The warning is reported at the line that called load(), not inside idl_parser.

        警告の発生箇所は idl_parser の中ではなく load() を呼んだ行になる。
        """
        _, ws = load('strcut S { long x; };')
        self.assertEqual(os.path.abspath(ws[0].filename), os.path.abspath(__file__))

    def test_can_be_turned_into_an_error(self):
        """warnings.simplefilter('error', ...) makes it an exception already now.

        warnings.simplefilter('error', ...) で今から例外にできる。
        """
        with warnings.catch_warnings():
            warnings.simplefilter('error', UnknownIDLSyntaxWarning)
            with self.assertRaises(UnknownIDLSyntaxWarning):
                parser.IDLParser().load('module M { strcut S { long x; }; };')

    def test_unknown_word_before_closing_brace(self):
        """An unknown word just before "}" does not swallow the end of the module.

        "}" の直前の未知の語でモジュールの終わりが消えない。
        """
        g, ws = load('module M { foo };\nstruct Z { long z; };')
        self.assertEqual([w.category for w in ws], [UnknownIDLSyntaxWarning])
        self.assertEqual([s.name for s in g.structs], ['Z'])
        self.assertEqual(g.module_by_name('M').structs, [])

    def test_unsupported_definitions_warn(self):
        """Valid but unsupported definitions give an UnsupportedIDLSyntaxWarning.

        正しいが未対応の定義では UnsupportedIDLSyntaxWarning が出る。
        """
        for label, decl in UNSUPPORTED.items():
            with self.subTest(label):
                g, ws = load('module M {\n  ' + decl + '\n  struct S { long x; };\n};')
                self.assertEqual([w.category for w in ws], [UnsupportedIDLSyntaxWarning])
                self.assertIn('line 2', str(ws[0].message))
                self.assertEqual([s.full_path for s in g.module_by_name('M').structs], ['M::S'])

    def test_modifiers_and_annotation_definitions_do_not_warn(self):
        """"local interface" is parsed, and an @annotation definition is skipped quietly.

        "local interface" は解析し、@annotation 定義は警告なしで読み飛ばす。
        """
        g, ws = load('@annotation A { long value default 0; };\n'
                     'module M { local interface I { void f(); }; };')
        self.assertEqual(ws, [])
        self.assertEqual([i.name for i in g.module_by_name('M').interfaces], ['I'])

    def test_valid_idl_does_not_warn(self):
        """IDL files used by the tests give no warning.

        テスト用の正しい IDL ファイルでは警告が出ない。
        """
        for name in ('basic_module_test.idl', 'multi_module_test.idl',
                     'forward_declaration.idl', 'issue18_idl42_int_types.idl'):
            with self.subTest(name):
                path = os.path.join(support.IDL_DIR, name)
                with open(path) as f:
                    _, ws = load(f.read(), filepath=path)
                self.assertEqual(ws, [])

    def test_categories(self):
        """Both warnings are UserWarnings, so they are shown by default.

        どちらも UserWarning なので既定で表示される。
        """
        self.assertTrue(issubclass(UnknownIDLSyntaxWarning, UserWarning))
        self.assertTrue(issubclass(UnsupportedIDLSyntaxWarning, UserWarning))


if __name__ == '__main__':
    unittest.main()
