"""Template modules (issue #121).

``module MT <typename T> { ... };`` (IDL 4.2 building block "Template
Modules") and its instantiation ``module MI = MT<long>;`` raised
InvalidIDLSyntaxError. They are not supported yet, so they are skipped with
an UnsupportedIDLSyntaxWarning, like the definitions of issue #100.
"""
import unittest
import warnings
from idl_parser import parser
from idl_parser.exception import UnsupportedIDLSyntaxWarning


def load(idl):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        g = parser.IDLParser().load(idl)
    return g, [str(w.message) for w in caught if issubclass(w.category, UnsupportedIDLSyntaxWarning)]


class TemplateModuleTest(unittest.TestCase):
    """Category: Modules, scopes and type name resolution / カテゴリ: モジュール・スコープ・型名解決

    Template modules are skipped with a warning (issue #121).
    テンプレートモジュールは警告を出して読み飛ばす(#121)。
    """

    def test_template_module_is_skipped(self):
        """A template module and its instantiation are skipped with UnsupportedIDLSyntaxWarning.

        テンプレートモジュールとそのインスタンス化は UnsupportedIDLSyntaxWarning を出して読み飛ばす。
        """
        g, messages = load('module MT <typename T> { struct S { T t; }; };\n'
                           'module MI = MT<long>;\n'
                           'module N { struct S { long x; }; };')
        self.assertEqual([m.name for m in g.modules], ['N'])
        self.assertEqual(g.structs, [])
        self.assertEqual(len(messages), 2)
        self.assertIn('line 1', messages[0])
        self.assertIn('"module MT <typename T> { ... }"', messages[0])
        self.assertIn('line 2', messages[1])
        self.assertIn('"module MI = MT<long>"', messages[1])

    def test_spellings(self):
        """Parameters written next to the name, several parameters, and nested braces.

        名前に続けて書いたパラメータ、複数のパラメータ、入れ子の { } でも読み飛ばす。
        """
        for idl in ('module MT<typename T> { struct S { T t; }; };',
                    'module MT< typename T, const long N > { typedef sequence<T, N> TSeq; };',
                    'module MT <struct S, sequence<long> L> { module Inner { struct X { long a; }; }; };'):
            with self.subTest(idl):
                g, messages = load(idl + ' struct After { long a; };')
                self.assertEqual(g.modules, [])
                self.assertEqual([s.name for s in g.structs], ['After'])
                self.assertEqual(len(messages), 1)

    def test_inside_module(self):
        """A template module inside a module does not end that module.

        module の中のテンプレートモジュールで外側の module が閉じない。
        """
        g, messages = load('module M { module MT <typename T> { struct S { T t; }; }; '
                           'module MI = MT<long>; struct A { long a; }; };')
        m = g.module_by_name('M')
        self.assertEqual(m.modules, [])
        self.assertEqual([s.full_path for s in m.structs], ['M::A'])
        self.assertEqual(len(messages), 2)

    def test_plain_module_is_not_a_template(self):
        """An ordinary module is still parsed, with no warning.

        通常の module はこれまで通り読み、警告も出ない。
        """
        g, messages = load('module M { struct S { long x; }; };')
        self.assertEqual([s.full_path for s in g.module_by_name('M').structs], ['M::S'])
        self.assertEqual(messages, [])


if __name__ == '__main__':
    unittest.main()
