"""Tests for issue #93: native type declarations.

"native N;" was skipped with an UnsupportedIDLSyntaxWarning, so a member,
an argument or a typedef of type N failed with "Can not find Data Type".
A native type is now registered by its name (IDLNative) and found by
find_types().
"""
import unittest
import warnings
from idl_parser import parser
from idl_parser.exception import IDLParserWarning, InvalidIDLSyntaxError


IDL = '''
module M {
  native Cookie;
  @foo native Handle;
  struct S { Cookie c; sequence<Cookie> cs; };
  typedef Cookie CookieAlias;
  interface I { Cookie get(in Handle h, out Cookie c); };
  module N { struct T { Cookie c; }; };
};
'''


def load(idl):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        g = parser.IDLParser().load(idl)
    return g, [w for w in caught if issubclass(w.category, IDLParserWarning)]


class NativeTest(unittest.TestCase):
    """Category: Primitive types and constants / カテゴリ: 基本型・定数

    native type declarations (issue #93).
    native 型の宣言(#93)。
    """

    @classmethod
    def setUpClass(cls):
        cls.g, cls.warnings = load(IDL)
        cls.m = cls.g.module_by_name('M')

    def test_no_warning(self):
        """A native declaration gives no UnsupportedIDLSyntaxWarning any more.

        native の宣言で UnsupportedIDLSyntaxWarning が出なくなる。
        """
        self.assertEqual(self.warnings, [])

    def test_natives_of_module(self):
        """Native types are listed in IDLModule.natives.

        native 型は IDLModule.natives に入る。
        """
        self.assertEqual([n.name for n in self.m.natives], ['Cookie', 'Handle'])
        n = self.m.native_by_name('Cookie')
        self.assertEqual(n.classname, 'IDLNative')
        self.assertTrue(n.is_native)
        self.assertEqual(n.full_path, 'M::Cookie')
        self.assertTrue(self.m.native_by_name('Handle').has_annotation('foo'))

    def test_find_types(self):
        """find_types() finds a native type.

        find_types() で native 型が見つかる。
        """
        self.assertEqual([t.full_path for t in self.g.find_types('M::Cookie')], ['M::Cookie'])

    def test_member_type(self):
        """A native type can be the type of a struct member and a sequence element.

        native 型を struct メンバーや sequence の要素の型に使える。
        """
        s = self.m.struct_by_name('S')
        self.assertTrue(s.member_by_name('c').type.is_native)
        self.assertEqual(str(s.member_by_name('cs').type), 'sequence<Cookie>')
        t = self.m.module_by_name('N').struct_by_name('T')
        self.assertEqual(t.member_by_name('c').type.full_path, 'M::Cookie')

    def test_typedef_and_arguments(self):
        """A native type can be used in a typedef and in operations.

        native 型を typedef と operation で使える。
        """
        self.assertTrue(self.m.typedef_by_name('CookieAlias').type.is_native)
        f = self.m.interface_by_name('I').method_by_name('get')
        self.assertTrue(f.returns.obj.is_native)
        self.assertEqual([(a.direction, str(a.type), a.name) for a in f.arguments],
                         [('in', 'Handle', 'h'), ('out', 'Cookie', 'c')])
        self.assertTrue(f.argument_by_name('h').type.obj.is_native)

    def test_output(self):
        """to_simple_dic() and to_dic() include native types.

        to_simple_dic() と to_dic() に native 型が入る。
        """
        g, _ = load('module M { native N; };')
        self.assertEqual(g.to_simple_dic(), {'module __global__': [{'module M': ['native N']}]})
        self.assertEqual(g.to_dic()['modules'][0]['natives'],
                         [{'name': 'N', 'filepath': None, 'classname': 'IDLNative'}])
        self.assertEqual(g.to_dic()['natives'], [])

    def test_recursive_simple_dic(self):
        """A member of a native type is shown with an empty member list.

        native 型のメンバーは空のメンバー一覧で表示される。
        """
        s = self.m.struct_by_name('S')
        self.assertEqual(s.member_by_name('c').to_simple_dic(recursive=True), {'Cookie c': []})

    def test_constructor_python(self):
        """generate_constructor_python() gives None for a native type.

        generate_constructor_python() は native 型に None を返す。
        """
        p = parser.IDLParser()
        g = p.load('native N; struct S { N n; long x; };')
        self.assertEqual(p.generate_constructor_python(g.struct_by_name('S')), 'S(None, 0)')

    def test_syntax_errors(self):
        """"native;" and "native N" without ";" are errors.

        "native;" と ";" のない "native N" はエラーになる。
        """
        for idl in ('native;', 'native N', 'native N struct S { long x; };'):
            with self.subTest(idl):
                with self.assertRaises(InvalidIDLSyntaxError):
                    parser.IDLParser().load(idl)


if __name__ == '__main__':
    unittest.main()
