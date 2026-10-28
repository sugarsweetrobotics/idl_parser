"""Regression tests for issues #76 and #94.

An unknown word in a module or the global scope (e.g. a misspelled keyword,
"strcut S { ... };") was dropped silently, together with the "{ ... }" block
after it. From 0.3.2 it was skipped with an UnknownIDLSyntaxWarning (#76);
from 0.4.0 it is an InvalidIDLSyntaxError (#94). Valid definitions that are
not supported yet (component, home, ...) are still skipped with an
UnsupportedIDLSyntaxWarning; valuetype and eventtype are parsed (#99).
"""
import os
import unittest
import warnings
from idl_parser import parser
from idl_parser.exception import (IDLParserWarning, InvalidIDLSyntaxError,
                                  UnknownIDLSyntaxWarning, UnsupportedIDLSyntaxWarning)
from tests import support


def load(idl, filepath=None):
    """Parse ``idl`` and return (global module, list of idl_parser warnings)."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        g = parser.IDLParser().load(idl, filepath=filepath)
    return g, [w for w in caught if issubclass(w.category, IDLParserWarning)]


TYPOS = {
    # IDL -> (unknown word, where)
    'missing_space_after_module': ('moduleA { struct S { long x; }; };',
                                   'moduleA', 'the global scope'),
    'struct': ('module M { strcut S { long x; }; };', 'strcut', 'module M'),
    'interface': ('module M { interfce I { void f(); }; };', 'interfce', 'module M'),
    'declaration': ('module M { foo bar; struct T { long y; }; };', 'foo', 'module M'),
}

UNSUPPORTED = {
    'component': 'component C { provides I p; };',
    'home': 'home H manages C { };',
    'typeprefix': 'typeprefix M "example.com";',
}


class UnknownWordTest(unittest.TestCase):
    """Category: Modules, scopes and type name resolution / カテゴリ: モジュール・スコープ・型名解決

    An unknown word is an error (issues #76 and #94).
    未知の語はエラーになる(#76、#94)。
    """

    def test_unknown_word_is_an_error(self):
        """A misspelled keyword is an InvalidIDLSyntaxError naming the word and the scope.

        キーワードの書き間違いは、その語とスコープを示す InvalidIDLSyntaxError になる。
        """
        for label, (idl, word, where) in TYPOS.items():
            with self.subTest(label):
                with self.assertRaises(InvalidIDLSyntaxError) as cm:
                    load(idl)
                self.assertIn('"%s"' % word, str(cm.exception))
                self.assertIn(where, str(cm.exception))
                self.assertEqual(cm.exception.line_number, 1)

    def test_message_has_file_and_line(self):
        """The error names the file and the line of the unknown word.

        エラーにファイル名と未知の語の行番号が入る。
        """
        with self.assertRaises(InvalidIDLSyntaxError) as cm:
            load('module M {\n  struct A { long a; };\n  strcut S {\n    long x;\n  };\n};',
                 filepath='typo.idl')
        # file names are absolute paths (issue #142)
        self.assertIn('File "%s", line 3' % os.path.abspath('typo.idl'), str(cm.exception))
        self.assertIn('module M', str(cm.exception))
        self.assertIn('"strcut S { ... }"', str(cm.exception))

    def test_no_warning_is_issued(self):
        """UnknownIDLSyntaxWarning is no longer issued, even with the error filter of 0.3.2.

        0.3.2 の error フィルタを設定していても UnknownIDLSyntaxWarning は出ない。
        """
        with warnings.catch_warnings():
            warnings.simplefilter('error', UnknownIDLSyntaxWarning)
            with self.assertRaises(InvalidIDLSyntaxError):
                parser.IDLParser().load('module M { strcut S { long x; }; };')

    def test_unknown_word_before_closing_brace(self):
        """An unknown word just before "}" is an error too.

        "}" の直前の未知の語もエラーになる。
        """
        with self.assertRaises(InvalidIDLSyntaxError) as cm:
            load('module M { foo };\nstruct Z { long z; };')
        self.assertIn('"foo"', str(cm.exception))

    def test_type_definitions_in_interface(self):
        """Types defined in an interface are not unknown words (issue #101).

        interface の中の型定義は未知の語にならない(#101)。
        """
        g, ws = load('module M { interface I { struct S { long a; }; void f(); }; };')
        self.assertEqual(ws, [])
        self.assertEqual([m.name for m in g.module_by_name('M').interface_by_name('I').methods], ['f'])

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
                     'module M { local interface I { void f(); }; abstract valuetype V { }; };')
        self.assertEqual(ws, [])
        self.assertEqual([i.name for i in g.module_by_name('M').interfaces], ['I'])
        self.assertEqual([v.name for v in g.module_by_name('M').valuetypes], ['V'])

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
        UnknownIDLSyntaxWarning is kept for code that refers to it.

        どちらも UserWarning なので既定で表示される。UnknownIDLSyntaxWarning は
        参照しているコードのために残している。
        """
        self.assertTrue(issubclass(UnknownIDLSyntaxWarning, UserWarning))
        self.assertTrue(issubclass(UnsupportedIDLSyntaxWarning, UserWarning))


if __name__ == '__main__':
    unittest.main()
