"""Tests for issue #140: escaped identifiers (``_module``) lose their ``_``.

In IDL a leading underscore escapes an identifier that clashes with a
keyword; it is not part of the identifier, so ``long _module;`` declares a
member named ``module``. The name was kept as ``'_module'``, so generated
names and repository IDs differed from omniidl. Names are now given without
the ``_`` (``is_escaped`` and ``written_name`` tell how they were written),
and names are resolved without it.
"""
import unittest

from idl_parser import parser
from idl_parser.exception import InvalidIDLSyntaxError
from idl_parser.node import unescape, is_escaped


IDL = '''
module _M {
  struct _module { long _interface; long normal; };
  typedef _module _Alias;
  struct S { _module a; ::_M::_module b; _M::_Alias c; sequence<_module> d; M::module e; };
  const long _N = 2;
  const long K = _N * 2;
  enum _E { _A, B };
  interface _I { void _op(in long _in); attribute long _attribute; };
  interface J : _I { };
  exception _X { long a; };
  interface K2 { void f() raises (_X); };
  struct _F;
  struct G { _F f; };
  struct _F { long a; };
};
'''


class EscapedIdentifierTest(unittest.TestCase):
    """Category: Scopes and modules / カテゴリ: スコープ・モジュール

    Escaped identifiers lose their leading "_" (issue #140).
    エスケープ付き識別子の先頭の "_" を外す(#140)。
    """

    @classmethod
    def setUpClass(cls):
        cls.g = parser.IDLParser().load(IDL)
        cls.m = cls.g.module_by_name('M')

    def test_names(self):
        """Names lose the "_"; is_escaped and written_name keep how they were written. / name は "_" を外し、is_escaped と written_name で書いた形が分かる。"""
        self.assertEqual(self.m.name, 'M')
        self.assertTrue(self.m.is_escaped)
        self.assertEqual(self.m.written_name, '_M')
        s = self.m.struct_by_name('module')
        self.assertEqual(s.full_path, 'M::module')
        self.assertEqual([x.name for x in s.members], ['interface', 'normal'])
        self.assertEqual([x.is_escaped for x in s.members], [True, False])
        self.assertEqual(s.members[1].written_name, 'normal')

    def test_keywords_need_escape(self):
        """Without "_", a keyword is still an error. / "_" なしのキーワードは従来どおりエラー。"""
        with self.assertRaises(InvalidIDLSyntaxError):
            parser.IDLParser().load('struct S { long module; };')

    def test_type_references(self):
        """Type names are resolved without the "_". / 型名は "_" を外して解決される。"""
        s = self.m.struct_by_name('module')
        S = self.m.struct_by_name('S')
        self.assertIs(S.member_by_name('a').type, s)
        self.assertIs(S.member_by_name('b').type, s)
        self.assertIs(S.member_by_name('c').type, self.m.typedef_by_name('Alias'))
        self.assertIs(S.member_by_name('d').type.inner_type, s)
        self.assertIs(S.member_by_name('e').type, s)
        self.assertEqual(str(S.member_by_name('a').type), 'module')

    def test_by_name_accepts_both(self):
        """*_by_name() accepts the name with or without "_". / *_by_name() は "_" 付きでも外した名前でも引ける。"""
        self.assertIs(self.g.module_by_name('_M'), self.m)
        self.assertIs(self.m.struct_by_name('_module'), self.m.struct_by_name('module'))

    def test_constants_and_enums(self):
        """Constants and enumerators. / 定数と列挙子。"""
        self.assertEqual(self.m.const_by_name('K').value, 4)
        self.assertEqual(self.m.const_by_name('N').name, 'N')
        self.assertEqual([v.name for v in self.m.enum_by_name('E').values], ['A', 'B'])

    def test_interfaces(self):
        """Operations, arguments, attributes, inheritance and raises. / operation・引数・attribute・継承・raises。"""
        i = self.m.interface_by_name('I')
        self.assertEqual(i.methods[0].name, 'op')
        self.assertEqual(i.methods[0].arguments[0].name, 'in')
        self.assertEqual(i.attributes[0].name, 'attribute')
        self.assertIs(self.m.interface_by_name('J').inheritances[0], i)
        self.assertEqual(self.m.interface_by_name('K2').methods[0].exceptions[0].name, 'X')

    def test_forward_declaration(self):
        """A forward declaration and its definition match without the "_". / 前方宣言と定義は "_" を外して対応する。"""
        self.assertEqual(self.m.forward_structs, ['F'])
        self.assertEqual(self.m.undefined_forward_structs, [])
        self.assertIs(self.m.struct_by_name('G').members[0].type, self.m.struct_by_name('F'))

    def test_same_name_with_and_without_escape(self):
        """_S and S are the same name. / _S と S は同じ名前。"""
        g = parser.IDLParser().load('struct _S { long a; }; struct S { long b; };')
        self.assertEqual([s.name for s in g.structs], ['S'])

    def test_to_dic(self):
        """to_dic() uses the names without "_". / to_dic() は "_" を外した名前を使う。"""
        d = self.g.to_dic()['modules'][0]
        self.assertEqual(d['name'], 'M')
        self.assertEqual(d['structs'][0]['members'][0]['name'], 'interface')

    def test_unescape(self):
        """unescape() and is_escaped(). / unescape() と is_escaped()。"""
        self.assertEqual(unescape('_module'), 'module')
        self.assertEqual(unescape('::_M::_X'), '::M::X')
        self.assertEqual(unescape('__global__'), '__global__')
        self.assertEqual(unescape('_1'), '_1')
        self.assertEqual(unescape('a_b'), 'a_b')
        self.assertTrue(is_escaped('_x'))
        self.assertFalse(is_escaped('x_'))


if __name__ == '__main__':
    unittest.main()
