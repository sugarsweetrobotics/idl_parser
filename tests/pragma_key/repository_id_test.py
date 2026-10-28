"""Tests for issue #135: repository IDs of the definitions.

``#pragma prefix`` / ``#pragma ID`` / ``#pragma version`` were only recorded
in IDLParser.pragmas, and ``typeid`` / ``typeprefix`` were skipped with a
warning, so the repository ID (``IDL:omg.org/CosNaming/NamingContext:1.0``)
of a definition could not be known. Each definition now has
``repository_id``, computed with the rules of the CORBA specification.
"""
import os
import tempfile
import unittest
import warnings

from idl_parser import parser
from idl_parser.exception import InvalidIDLSyntaxError, IDLParserWarning
from idl_parser.repository_id import find_definition


def load(idl):
    p = parser.IDLParser()
    return p, p.load(idl)


def rid(g, name):
    return find_definition(name, g).repository_id


# The example of "Generation of OMG IDL-Format IDs" in the CORBA specification
SPEC_IDL = '''
module M1 {
  typedef long T1;
  typedef long T2;
#pragma ID T2 "DCE:d62207a2-011e-11ce-88b4-0800090b5d3e:3"
};
#pragma prefix "P1"
module M2 {
  module M3 {
#pragma prefix "P2"
    typedef long T3;
  };
  typedef long T4;
#pragma version T4 2.4
};
'''


class SpecExampleTest(unittest.TestCase):
    """Category: Pragmas and keys / カテゴリ: pragma・key

    The example of the CORBA specification (issue #135).
    CORBA 仕様の例のとおりのリポジトリID(#135)。
    """

    @classmethod
    def setUpClass(cls):
        cls.p, cls.g = load(SPEC_IDL)

    def test_default(self):
        """Without pragmas the ID is IDL:<scoped name>:1.0. / pragma なしでは IDL:<スコープ名>:1.0。"""
        self.assertEqual(rid(self.g, 'M1'), 'IDL:M1:1.0')
        self.assertEqual(rid(self.g, 'M1::T1'), 'IDL:M1/T1:1.0')

    def test_pragma_id(self):
        """#pragma ID gives the whole ID. / #pragma ID で ID 全体を指定できる。"""
        self.assertEqual(rid(self.g, 'M1::T2'), 'DCE:d62207a2-011e-11ce-88b4-0800090b5d3e:3')
        pragma = [x for x in self.p.pragmas if x.is_id][0]
        self.assertIs(pragma.target, find_definition('M1::T2', self.g))
        self.assertEqual(pragma.value, 'DCE:d62207a2-011e-11ce-88b4-0800090b5d3e:3')

    def test_prefix(self):
        """#pragma prefix applies to the definitions after it. / #pragma prefix は後の定義に効く。"""
        self.assertEqual(rid(self.g, 'M2'), 'IDL:P1/M2:1.0')
        self.assertEqual(rid(self.g, 'M2::M3'), 'IDL:P1/M2/M3:1.0')

    def test_prefix_in_nested_scope(self):
        """A prefix in a module gives names relative to that module. / モジュール内の prefix ではそのモジュールからの相対名になる。"""
        self.assertEqual(rid(self.g, 'M2::M3::T3'), 'IDL:P2/T3:1.0')

    def test_prefix_ends_with_scope_and_version(self):
        """The prefix ends with its scope; #pragma version changes the version. / prefix はスコープの終わりまで、#pragma version で版が変わる。"""
        self.assertEqual(rid(self.g, 'M2::T4'), 'IDL:P1/M2/T4:2.4')


COSNAMING_IDL = '''
#pragma prefix "omg.org"
module CosNaming {
  typedef string Istring;
  struct NameComponent { Istring id; Istring kind; };
  interface NamingContext {
    exception NotFound { long why; };
    void unbind(in Istring n) raises (NotFound);
    readonly attribute long count;
  };
  enum BindingType { nobject, ncontext };
  const long MAX = 10;
  union U switch (long) { case 1: long a; };
  native N;
  valuetype V { public long a; };
};
#pragma ID CosNaming::NamingContext "IDL:omg.org/CosNaming/NamingContext:1.0"
'''


class KindsTest(unittest.TestCase):
    """Category: Pragmas and keys / カテゴリ: pragma・key

    Which nodes have a repository ID (issue #135).
    リポジトリIDを持つノードの種類(#135)。
    """

    @classmethod
    def setUpClass(cls):
        cls.p, cls.g = load(COSNAMING_IDL)
        cls.m = cls.g.module_by_name('CosNaming')

    def test_definitions(self):
        """Every kind of definition has an ID. / 各種の定義が ID を持つ。"""
        for name, expected in [
                ('CosNaming', 'IDL:omg.org/CosNaming:1.0'),
                ('CosNaming::Istring', 'IDL:omg.org/CosNaming/Istring:1.0'),
                ('CosNaming::NameComponent', 'IDL:omg.org/CosNaming/NameComponent:1.0'),
                ('CosNaming::NamingContext', 'IDL:omg.org/CosNaming/NamingContext:1.0'),
                ('CosNaming::NamingContext::NotFound', 'IDL:omg.org/CosNaming/NamingContext/NotFound:1.0'),
                ('CosNaming::NamingContext::unbind', 'IDL:omg.org/CosNaming/NamingContext/unbind:1.0'),
                ('CosNaming::NamingContext::count', 'IDL:omg.org/CosNaming/NamingContext/count:1.0'),
                ('CosNaming::BindingType', 'IDL:omg.org/CosNaming/BindingType:1.0'),
                ('CosNaming::MAX', 'IDL:omg.org/CosNaming/MAX:1.0'),
                ('CosNaming::U', 'IDL:omg.org/CosNaming/U:1.0'),
                ('CosNaming::N', 'IDL:omg.org/CosNaming/N:1.0'),
                ('CosNaming::V', 'IDL:omg.org/CosNaming/V:1.0')]:
            with self.subTest(name):
                self.assertEqual(rid(self.g, name), expected)

    def test_property_on_nodes(self):
        """repository_id is a property of the nodes. / repository_id はノードのプロパティ。"""
        nc = self.m.interface_by_name('NamingContext')
        self.assertEqual(nc.repository_id, 'IDL:omg.org/CosNaming/NamingContext:1.0')
        self.assertEqual(nc.exceptions[0].repository_id,
                         'IDL:omg.org/CosNaming/NamingContext/NotFound:1.0')

    def test_nodes_without_id(self):
        """The global scope, members, enumerators and types have none. / グローバルスコープ・メンバー・列挙子・型は None。"""
        self.assertIsNone(self.g.repository_id)
        s = self.m.struct_by_name('NameComponent')
        self.assertIsNone(s.members[0].repository_id)
        self.assertIsNone(self.m.enum_by_name('BindingType').values[0].repository_id)
        self.assertIsNone(self.m.interface_by_name('NamingContext').methods[0].arguments[0].repository_id)

    def test_same_id_twice_is_allowed(self):
        """Giving the same ID again is not an error. / 同じ ID の再指定はエラーにならない。"""
        p, g = load(COSNAMING_IDL)
        self.assertEqual(rid(g, 'CosNaming::NamingContext'), 'IDL:omg.org/CosNaming/NamingContext:1.0')


class PrefixScopeTest(unittest.TestCase):
    """Category: Pragmas and keys / カテゴリ: pragma・key

    Where a #pragma prefix applies (issue #135).
    #pragma prefix が効く範囲(#135)。
    """

    def test_prefix_ends_with_module(self):
        """A prefix in a module ends with the module. / モジュール内の prefix はモジュールの終わりで切れる。"""
        p, g = load('module A {\n#pragma prefix "x"\n struct S { long a; };\n};\nstruct T { long b; };')
        self.assertEqual(rid(g, 'A::S'), 'IDL:x/S:1.0')
        self.assertEqual(rid(g, 'A'), 'IDL:A:1.0')
        self.assertEqual(rid(g, 'T'), 'IDL:T:1.0')

    def test_prefix_in_interface(self):
        """A prefix in an interface applies to what follows in it. / interface 内の prefix はその後の定義に効く。"""
        p, g = load('interface I {\n void f();\n#pragma prefix "x"\n void g();\n};')
        self.assertEqual(rid(g, 'I::f'), 'IDL:I/f:1.0')
        self.assertEqual(rid(g, 'I::g'), 'IDL:x/g:1.0')

    def test_prefix_replaced_and_cleared(self):
        """A later prefix replaces it, and "" clears it. / 次の prefix で置き換わり、"" で消える。"""
        p, g = load('#pragma prefix "a"\nstruct A { long a; };\n#pragma prefix "b"\n'
                    'struct B { long b; };\n#pragma prefix ""\nstruct C { long c; };')
        self.assertEqual([rid(g, n) for n in 'ABC'],
                         ['IDL:a/A:1.0', 'IDL:b/B:1.0', 'IDL:C:1.0'])

    def test_reopened_module(self):
        """A prefix in an earlier opening of a module does not carry over. / 前のオープンの prefix は次のオープンに持ち越さない。"""
        p, g = load('module M {\n#pragma prefix "x"\n struct A { long a; };\n};\n'
                    'module M { struct B { long b; }; };')
        self.assertEqual(rid(g, 'M::A'), 'IDL:x/A:1.0')
        self.assertEqual(rid(g, 'M::B'), 'IDL:M/B:1.0')

    def test_prefix_does_not_carry_to_next_load(self):
        """Each load() starts with no prefix. / load() ごとに prefix なしで始まる。"""
        p = parser.IDLParser()
        p.load('#pragma prefix "x"\nstruct A { long a; };')
        g = p.load('struct B { long b; };')
        self.assertEqual(rid(g, 'A'), 'IDL:x/A:1.0')
        self.assertEqual(rid(g, 'B'), 'IDL:B:1.0')

    def test_forward_declaration(self):
        """A pragma ID given before the definition applies to it. / 定義の前に書いた #pragma ID も定義に効く。"""
        p, g = load('interface I;\n#pragma ID I "IDL:my/I:2.0"\ninterface I { };')
        self.assertEqual(g.interface_by_name('I').repository_id, 'IDL:my/I:2.0')


class IncludeTest(unittest.TestCase):
    """Category: Pragmas and keys / カテゴリ: pragma・key

    A #pragma prefix does not go into or out of an #include file (issue #135).
    #pragma prefix は #include の内外に引き継がれない(#135)。
    """

    def test_include(self):
        """The included file starts without a prefix, and the prefix is back after it. / include 先は prefix なしで始まり、戻ると元に戻る。"""
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, 'base.idl'), 'w') as f:
                f.write('module Base { struct P { long x; }; };\n'
                        '#pragma prefix "base.org"\n'
                        'module Base2 { struct Q { long y; }; };\n')
            main = os.path.join(d, 'main.idl')
            with open(main, 'w') as f:
                f.write('#pragma prefix "main.org"\n'
                        'module A { struct S { long a; }; };\n'
                        '#include "base.idl"\n'
                        'module B { struct T { long b; }; };\n')
            p = parser.IDLParser()
            p.parse_idl(main)
            g = p.global_module
            self.assertEqual(rid(g, 'A::S'), 'IDL:main.org/A/S:1.0')
            self.assertEqual(rid(g, 'Base::P'), 'IDL:Base/P:1.0')
            self.assertEqual(rid(g, 'Base2::Q'), 'IDL:base.org/Base2/Q:1.0')
            self.assertEqual(rid(g, 'B::T'), 'IDL:main.org/B/T:1.0')
            self.assertEqual([x.name for x in p.pragmas], ['prefix', 'prefix'])


class TypeIdTypePrefixTest(unittest.TestCase):
    """Category: Pragmas and keys / カテゴリ: pragma・key

    typeid and typeprefix declarations (issue #135).
    typeid と typeprefix 宣言(#135)。
    """

    def load_quiet(self, idl):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            g = parser.IDLParser().load(idl)
        self.assertEqual([w for w in caught if issubclass(w.category, IDLParserWarning)], [])
        return g

    def test_typeprefix(self):
        """typeprefix applies to the scope and everything in it, with the full scoped name. / typeprefix はスコープ自身と中の全定義に、完全なスコープ名で効く。"""
        g = self.load_quiet('module M { module N { struct S { long a; }; }; interface I { void f(); }; };\n'
                            'typeprefix M "example.com";')
        self.assertEqual(rid(g, 'M'), 'IDL:example.com/M:1.0')
        self.assertEqual(rid(g, 'M::N::S'), 'IDL:example.com/M/N/S:1.0')
        self.assertEqual(rid(g, 'M::I::f'), 'IDL:example.com/M/I/f:1.0')

    def test_typeprefix_inside_scope(self):
        """typeprefix written inside the module, and an inner one wins. / モジュール内に書いた typeprefix、内側のものが優先。"""
        g = self.load_quiet('module Components {\n typeprefix Components "omg.org";\n'
                            ' interface CCMObject { };\n'
                            ' module Deep { struct S { long a; }; typeprefix Deep "deep.org"; };\n};')
        self.assertEqual(rid(g, 'Components::CCMObject'), 'IDL:omg.org/Components/CCMObject:1.0')
        self.assertEqual(rid(g, 'Components::Deep::S'), 'IDL:deep.org/Components/Deep/S:1.0')

    def test_typeprefix_global(self):
        """typeprefix :: applies to everything. / typeprefix :: は全体に効く。"""
        g = self.load_quiet('typeprefix :: "all.org";\nstruct S { long a; };')
        self.assertEqual(rid(g, 'S'), 'IDL:all.org/S:1.0')

    def test_typeprefix_wins_over_pragma(self):
        """typeprefix wins over #pragma prefix. / typeprefix は #pragma prefix より優先される。"""
        g = self.load_quiet('#pragma prefix "p"\nmodule M { struct S { long a; }; };\ntypeprefix M "t";')
        self.assertEqual(rid(g, 'M::S'), 'IDL:t/M/S:1.0')

    def test_typeid(self):
        """typeid gives the whole ID, also inside an interface, and wins over typeprefix. / typeid は ID 全体を指定し、interface 内でも書け、typeprefix より優先される。"""
        g = self.load_quiet('module M { struct S { long a; }; interface I { void f(); typeid f "IDL:x/f:3.0"; }; };\n'
                            'typeid M::S "IDL:my/S:2.0";\ntypeprefix M "t";')
        self.assertEqual(rid(g, 'M::S'), 'IDL:my/S:2.0')
        self.assertEqual(rid(g, 'M::I::f'), 'IDL:x/f:3.0')
        self.assertEqual([m.name for m in g.module_by_name('M').interface_by_name('I').methods], ['f'])

    def test_invalid_declaration(self):
        """A declaration without a string is an error. / 文字列のない宣言はエラー。"""
        for idl in ('typeid M;', 'typeprefix M example;', 'module M {}; typeprefix M "a" "b";'):
            with self.subTest(idl):
                with self.assertRaises(InvalidIDLSyntaxError):
                    parser.IDLParser().load(idl)

    def test_typeprefix_on_non_scope(self):
        """typeprefix on a struct is an error. / struct への typeprefix はエラー。"""
        with self.assertRaises(InvalidIDLSyntaxError):
            parser.IDLParser().load('struct S { long a; }; typeprefix S "x";')


class ConflictTest(unittest.TestCase):
    """Category: Pragmas and keys / カテゴリ: pragma・key

    Conflicting repository ID settings are errors (issue #135).
    矛盾するリポジトリIDの指定はエラー(#135)。
    """

    def assertError(self, idl):
        with self.assertRaises(InvalidIDLSyntaxError):
            parser.IDLParser().load(idl)

    def test_two_ids(self):
        """Two different IDs. / 異なる 2 つの ID。"""
        self.assertError('struct S { long a; };\n#pragma ID S "IDL:a/S:1.0"\n#pragma ID S "IDL:b/S:1.0"')
        self.assertError('struct S { long a; };\n#pragma ID S "IDL:a/S:1.0"\ntypeid S "IDL:b/S:1.0";')

    def test_two_versions(self):
        """Two different versions, or an invalid one. / 異なる 2 つの版、または不正な版。"""
        self.assertError('struct S { long a; };\n#pragma version S 1.1\n#pragma version S 1.2')
        self.assertError('struct S { long a; };\n#pragma version S 1')

    def test_version_and_id(self):
        """A version that does not match the ID. / ID と合わない版。"""
        self.assertError('struct S { long a; };\n#pragma ID S "IDL:a/S:1.0"\n#pragma version S 2.0')
        self.assertError('struct S { long a; };\n#pragma ID S "DCE:xyz:1"\n#pragma version S 1.0')
        p, g = load('struct S { long a; };\n#pragma ID S "IDL:a/S:2.0"\n#pragma version S 2.0')
        self.assertEqual(rid(g, 'S'), 'IDL:a/S:2.0')

    def test_two_typeprefixes(self):
        """Two different type prefixes on one scope. / 1 つのスコープに異なる 2 つの typeprefix。"""
        self.assertError('module M { }; typeprefix M "a"; typeprefix M "b";')

    def test_unknown_name_is_kept(self):
        """A pragma for an unknown name has no target. / 見つからない名前の pragma は target が None。"""
        p, g = load('struct S { long a; };\n#pragma ID X "IDL:x:1.0"')
        self.assertIsNone(p.pragmas[0].target)
        self.assertEqual(rid(g, 'S'), 'IDL:S:1.0')


class PragmaInPlaceTest(unittest.TestCase):
    """Category: Pragmas and keys / カテゴリ: pragma・key

    Pragmas kept in place do not change how the rest is read (issue #135).
    位置を保ったまま残した pragma が、他の部分の読み方を変えない(#135)。
    """

    def test_pragma_inside_definition(self):
        """A pragma inside a struct or inside "[ ]" is skipped. / struct の中や "[ ]" の中の pragma は読み飛ばされる。"""
        p, g = load('struct S {\n#pragma foo bar\nlong a; long b[\n#pragma x\n3]; };\n'
                    '#pragma keylist S a')
        s = g.struct_by_name('S')
        self.assertEqual(s.keys, ['a'])
        self.assertEqual(str(s.member_by_name('b').type), 'long[3]')
        self.assertEqual([x.name for x in p.pragmas], ['foo', 'x', 'keylist'])

    def test_token_buffer(self):
        """TokenBuffer skips the pragmas and returns them from take_pragmas(). / TokenBuffer は pragma を飛ばし、take_pragmas() で返す。"""
        from idl_parser.pragma import IDLPragma
        from idl_parser.token_buffer import TokenBuffer
        prefix = IDLPragma('prefix "x"')
        buf = TokenBuffer([(1, None, 'a b'), (2, None, prefix), (3, None, 'c')])
        self.assertEqual(buf.peek(2)[2], 'c')
        self.assertEqual([buf.pop()[2], buf.pop()[2]], ['a', 'b'])
        self.assertEqual(buf.take_pragmas(), [])
        self.assertEqual(buf.pop()[2], 'c')
        self.assertEqual(buf.take_pragmas(), [prefix])
        self.assertEqual(prefix.value, 'x')
        self.assertIsNone(buf.pop()[2])


if __name__ == '__main__':
    unittest.main()
