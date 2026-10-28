"""Regression tests for issue #143.

IDL that omniidl rejects was read without an error: a name defined twice
in one scope, two names that differ only in case, a oneway operation that
returns a value or has an out argument, and an operation or attribute
name inherited from two base interfaces. These are InvalidIDLSyntaxErrors
now.
"""
import os
import shutil
import tempfile
import unittest
from idl_parser import parser
from idl_parser.exception import InvalidIDLSyntaxError


def load(idl):
    return parser.IDLParser().load(idl)


class DuplicateDefinitionTest(unittest.TestCase):
    """Category: Modules, scopes and type name resolution / カテゴリ: モジュール・スコープ・型名解決

    A name is defined once in a scope (issue #143).
    1 つのスコープで同じ名前は 1 回しか定義できない(#143)。
    """

    def test_same_definition_twice(self):
        """Defining a name twice in one scope is an error, also across kinds.

        同じスコープで同じ名前を 2 回定義するとエラーになる(種類が違っても)。
        """
        for idl in ['struct S { long a; }; struct S { long b; };',
                    'module M { enum E { A }; enum E { B }; };',
                    'typedef long T; typedef short T;',
                    'const long C = 1; const long C = 2;',
                    'struct X { long a; }; typedef long X;',
                    'module M { interface I { }; struct I { long a; }; };',
                    'interface I { }; interface I { };',
                    'valuetype V { }; valuetype V { };',
                    'module M { }; struct M { long a; };',
                    'interface I { struct S { long a; }; exception S { }; };']:
            with self.subTest(idl):
                with self.assertRaises(InvalidIDLSyntaxError) as cm:
                    load(idl)
                self.assertIn('already defined', str(cm.exception))

    def test_message_has_scope_and_line(self):
        """The error names the scope and the line of the second definition.

        エラーにスコープと 2 回目の定義の行番号が入る。
        """
        with self.assertRaises(InvalidIDLSyntaxError) as cm:
            load('module M {\n  struct S { long a; };\n  struct S { long b; };\n};')
        self.assertIn('module "M"', str(cm.exception))
        self.assertEqual(cm.exception.line_number, 3)

    def test_enumerator_is_in_the_enclosing_scope(self):
        """An enumerator name is declared in the scope of its enum.

        列挙子の名前は enum を囲むスコープに宣言される。
        """
        for idl in ['enum E { A, B }; const long A = 1;',
                    'enum E { A }; enum F { A };']:
            with self.subTest(idl):
                with self.assertRaises(InvalidIDLSyntaxError):
                    load(idl)

    def test_allowed_repetitions(self):
        """Reopening a module and forward declarations are not duplicates.

        module の再オープンと前方宣言は重複にならない。
        """
        g = load('module M { struct A { long a; }; };\n'
                 'module M { struct B { long b; }; };\n'
                 'interface I; interface I { }; interface I;\n'
                 'struct F; struct F { long x; };\n'
                 'union U; union U switch (long) { case 1: long a; };\n'
                 'valuetype V; valuetype V { };')
        self.assertEqual([s.name for s in g.module_by_name('M').structs], ['A', 'B'])
        self.assertEqual([i.name for i in g.interfaces], ['I'])
        self.assertEqual([s.name for s in g.structs], ['F'])

    def test_same_name_in_different_scopes(self):
        """The same name in different scopes is allowed.

        別のスコープでは同じ名前を使える。
        """
        g = load('struct S { long a; };\n'
                 'module M { struct S { long b; }; interface I { struct S { long c; }; }; };')
        self.assertEqual(g.module_by_name('M').interface_by_name('I').struct_by_name('S').full_path,
                         'M::I::S')

    def test_header_included_by_several_files(self):
        """A header included by several files parsed together is not a duplicate.

        複数のファイルから include されたヘッダーは重複にならない。
        """
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d)
        files = {'common.idl': '#ifndef COMMON\n#define COMMON\nmodule C { struct T { long t; }; };\n#endif\n',
                 'a.idl': '#include "common.idl"\nmodule A { struct S { C::T t; }; };\n',
                 'b.idl': '#include "common.idl"\nmodule B { struct S { C::T t; }; };\n'}
        for name, text in files.items():
            with open(os.path.join(d, name), 'w') as f:
                f.write(text)
        p = parser.IDLParser()
        p.parse(idls=[os.path.join(d, 'a.idl'), os.path.join(d, 'b.idl')])
        self.assertEqual([s.name for s in p.global_module.module_by_name('C').structs], ['T'])


class CaseInsensitiveCollisionTest(unittest.TestCase):
    """Category: Modules, scopes and type name resolution / カテゴリ: モジュール・スコープ・型名解決

    Two names that differ only in case collide (issue #143).
    大文字小文字だけが違う名前は衝突する(#143)。
    """

    def test_definitions(self):
        """Definitions in one scope.

        同じスコープの定義。
        """
        with self.assertRaises(InvalidIDLSyntaxError) as cm:
            load('module M { struct S { long a; }; typedef long s; };')
        self.assertIn('differs only in case', str(cm.exception))
        with self.assertRaises(InvalidIDLSyntaxError):
            load('module M { }; module m { };')

    def test_members(self):
        """Members, enumerators, arguments and fields.

        メンバー、列挙子、引数、フィールド。
        """
        for idl in ['struct S { long a; long A; };',
                    'exception E { long a; short A; };',
                    'union U switch (long) { case 1: long a; case 2: short A; };',
                    'enum E { RED, red };',
                    'bitmask B { F1, f1 };',
                    'bitset B { bitfield<3> x; bitfield<2> X; };',
                    'interface I { void f(in long a, in long A); };',
                    'interface I { attribute long x; void X(); };',
                    'interface I { const long N = 1; attribute long n; };',
                    'valuetype V { public long a; private long A; };']:
            with self.subTest(idl):
                with self.assertRaises(InvalidIDLSyntaxError):
                    load(idl)

    def test_members_with_the_same_name(self):
        """Members with exactly the same name are an error too.

        まったく同じ名前のメンバーもエラーになる。
        """
        for idl in ['struct S { long a; short a; };',
                    'struct S { long a, a; };',
                    'struct B { long a; }; struct D : B { long a; };',
                    'union U switch (long) { case 1: long a; case 2: short a; };',
                    'interface I { void f(in long a, out long a); };',
                    'interface I { void f(); void f(); };',
                    'bitset A { bitfield<3> x; }; bitset B : A { bitfield<2> x; };']:
            with self.subTest(idl):
                with self.assertRaises(InvalidIDLSyntaxError) as cm:
                    load(idl)
                self.assertRegex(str(cm.exception), 'more than once|already defined')

    def test_unnamed_bitfields(self):
        """Unnamed bitfields have no name, so there can be several.

        名前のない bitfield は名前を持たないので、いくつあってもよい。
        """
        g = load('bitset B { bitfield<3> x; bitfield<2>; bitfield<1>; bitfield<1> y; };')
        self.assertEqual(len(g.bitset_by_name('B').bitfields), 4)


class OnewayTest(unittest.TestCase):
    """Category: Interfaces and operations / カテゴリ: インターフェース・オペレーション

    The rules of oneway operations (issue #143).
    oneway オペレーションの制約(#143)。
    """

    def test_valid_oneway(self):
        """A oneway operation that returns void and has only in arguments.

        void を返し in 引数だけを持つ oneway オペレーション。
        """
        g = load('interface I { oneway void f(in long a, long b); };')
        self.assertTrue(g.interface_by_name('I').method_by_name('f').oneway)

    def test_invalid_oneway(self):
        """A return value, an out or inout argument and raises are errors.

        戻り値、out / inout 引数、raises はエラーになる。
        """
        cases = {'interface I { oneway long f(); };': 'must return void',
                 'interface I { oneway string f(); };': 'must return void',
                 'interface I { oneway void f(out long x); };': 'out argument "x"',
                 'interface I { oneway void f(in long a, inout long b); };': 'inout argument "b"',
                 'exception E { }; interface I { oneway void f() raises (E); };': 'can not raise'}
        for idl, message in cases.items():
            with self.subTest(idl):
                with self.assertRaises(InvalidIDLSyntaxError) as cm:
                    load(idl)
                self.assertIn(message, str(cm.exception))
                self.assertEqual(cm.exception.line_number, 1)


class InheritedNameTest(unittest.TestCase):
    """Category: Interfaces and operations / カテゴリ: インターフェース・オペレーション

    Operation and attribute names that collide through inheritance (issue #143).
    継承によるオペレーション名・属性名の衝突(#143)。
    """

    def test_from_two_bases(self):
        """The same name from two different bases is an error.

        2 つの別の基底から同じ名前を継承するとエラーになる。
        """
        for idl in ['interface A { void f(); }; interface B { void f(); }; interface C : A, B { };',
                    'interface A { attribute long x; }; interface B { void X(); }; interface C : A, B { };',
                    'interface A { void f(); }; interface A2 : A { };\n'
                    'interface B { void f(); }; interface C : A2, B { };']:
            with self.subTest(idl):
                with self.assertRaises(InvalidIDLSyntaxError) as cm:
                    load(idl)
                self.assertIn('inherits', str(cm.exception))

    def test_redefinition(self):
        """Defining an inherited operation or attribute again is an error.

        継承したオペレーションや属性を定義し直すとエラーになる。
        """
        for idl in ['interface A { void f(); }; interface B : A { void f(); };',
                    'interface A { void f(); }; interface B : A { attribute long F; };',
                    'interface A { attribute long x; }; interface B : A { }; interface C : B { void x(); };']:
            with self.subTest(idl):
                with self.assertRaises(InvalidIDLSyntaxError) as cm:
                    load(idl)
                self.assertIn('redefines', str(cm.exception))

    def test_diamond(self):
        """A base reached by two paths (diamond inheritance) counts once.

        2 つの経路でたどる基底(ひし形継承)は 1 回と数える。
        """
        g = load('interface A { void f(); attribute long x; };\n'
                 'interface B : A { void g(); }; interface C : A { void h(); };\n'
                 'interface D : B, C { void i(); };')
        self.assertEqual(g.interface_by_name('D').method_by_name('i').name, 'i')

    def test_types_can_be_redefined(self):
        """Types and constants of a base may be defined again in a derived interface.

        基底の型や定数は派生インターフェースで定義し直してよい。
        """
        g = load('interface A { struct S { long a; }; const long N = 1; };\n'
                 'interface B : A { struct S { short b; }; const long N = 2; };')
        self.assertEqual(g.interface_by_name('B').struct_by_name('S').full_path, '::B::S')

    def test_valuetype_supports(self):
        """A valuetype that defines again an operation of a supported interface.

        サポートするインターフェースのオペレーションを定義し直す valuetype。
        """
        with self.assertRaises(InvalidIDLSyntaxError):
            load('interface I { void f(); }; valuetype V supports I { void f(); };')
        with self.assertRaises(InvalidIDLSyntaxError):
            load('valuetype A { public long a; }; valuetype B : A { public long a; };')


if __name__ == '__main__':
    unittest.main()
