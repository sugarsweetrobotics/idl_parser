"""Interface inheritance (issue #5)."""
import contextlib
import io
import os
import unittest
from idl_parser import parser
from idl_parser import exception
from tests import support

IDL_DIR = support.IDL_DIR


idl_path = os.path.join(IDL_DIR, 'generalization.idl')
extended_idl_path = os.path.join(IDL_DIR, 'generalization_extended.idl')


def bases(interface):
    return [i.full_path for i in interface.inheritances]


class GeneralizationTestFunctions(unittest.TestCase):
    """Category: Interfaces, operations and inheritance / カテゴリ: interface・operation・継承

    Interfaces in generalization.idl are read.
    generalization.idl の interface が読める。
    """

    def setUp(self):
        pass

    def test_module(self):
        """The modules and interfaces of generalization.idl are read.

        generalization.idl の module と interface が読める。
        """
        parser_ = parser.IDLParser()
        with open(idl_path, 'r') as idlf:
            m = parser_.load(idlf.read())
            self.assertEqual(m.name,'__global__')
            moduleA = m.modules[0]
            self.assertEqual(moduleA.name, 'moduleA')
            interfaceA = moduleA.interface_by_name('InterfaceA')
            self.assertEqual(interfaceA.name, 'InterfaceA')
            interfaceB = moduleA.interface_by_name('InterfaceB')
            self.assertEqual(interfaceB.name, 'InterfaceB')

            self.assertEqual(len(interfaceA.inheritances), 0)
            self.assertEqual(len(interfaceB.inheritances), 1)
            self.assertEqual(interfaceB.inheritances[0].full_path, 'moduleA::InterfaceA') # Must be fullpath


class GeneralizationExtendedTestFunctions(unittest.TestCase):
    """Category: Interfaces, operations and inheritance / カテゴリ: interface・operation・継承

    Interface inheritance cases from generalization_extended.idl (issue #5).
    generalization_extended.idl による interface 継承の各ケース(#5)。
    """

    @classmethod
    def setUpClass(cls):
        with open(extended_idl_path, 'r') as idlf:
            cls.m = parser.IDLParser().load(idlf.read())
        cls.moduleP = cls.m.module_by_name('moduleP')
        cls.moduleQ = cls.m.module_by_name('moduleQ')

    def test_inheritances_are_interface_objects(self):
        """inheritances holds the base interface objects themselves.

        inheritances が継承元 interface オブジェクトそのものを指す。
        """
        derived = self.moduleP.interface_by_name('Derived')
        base = self.moduleP.interface_by_name('Base')
        self.assertIs(derived.inheritances[0], base)
        self.assertTrue(derived.inheritances[0].is_interface)
        self.assertIsNotNone(derived.inheritances[0].method_by_name('methodBase'))

    def test_no_inheritance(self):
        """Without inheritance, inheritances is empty.

        継承なしなら inheritances が空。
        """
        self.assertEqual(bases(self.moduleP.interface_by_name('Base')), [])

    def test_unqualified_name_in_same_module(self):
        """A base in the same module is resolved by its unqualified name.

        同じモジュールの継承元を修飾なしの名前で解決。
        """
        self.assertEqual(bases(self.moduleP.interface_by_name('Derived')), ['moduleP::Base'])

    def test_multi_level_inheritance(self):
        """Multi-level inheritance.

        多段継承。
        """
        grandchild = self.moduleP.interface_by_name('Grandchild')
        self.assertEqual(bases(grandchild), ['moduleP::Derived'])
        self.assertEqual(bases(grandchild.inheritances[0]), ['moduleP::Base'])

    def test_multiple_inheritance_keeps_order(self):
        """Multiple inheritance keeps the order of the bases.

        多重継承で継承元の順序が保たれる。
        """
        self.assertEqual(bases(self.moduleP.interface_by_name('Multi')),
                         ['moduleP::Base', 'moduleP::Other'])

    def test_absolute_name(self):
        """Inheritance by an absolute name such as ::moduleP::Base.

        ::moduleP::Base のような絶対名で継承。
        """
        self.assertEqual(bases(self.moduleP.interface_by_name('Absolute')), ['moduleP::Base'])

    def test_scoped_name_in_other_module(self):
        """Inheritance of an interface in another module by scoped name.

        別モジュールの interface をスコープ付き名で継承。
        """
        self.assertEqual(bases(self.moduleQ.interface_by_name('CrossDerived')), ['moduleP::Base'])

    def test_innermost_scope_wins(self):
        """When bases share a name, the innermost scope wins.

        同名の継承元は最も内側のスコープが優先される。
        """
        self.assertEqual(bases(self.moduleQ.interface_by_name('LocalDerived')), ['moduleQ::Base'])

    def test_enclosing_scope_lookup(self):
        """A nested module finds a base in an enclosing scope.

        入れ子モジュールから外側スコープの継承元を探せる。
        """
        inner = self.moduleQ.module_by_name('inner')
        self.assertEqual(bases(inner.interface_by_name('InnerDerived')), ['moduleQ::Base'])

    def test_global_scope(self):
        """Inheritance of interfaces at global scope.

        グローバルスコープの interface の継承。
        """
        global_derived = self.m.interface_by_name('GlobalDerived')
        self.assertIs(global_derived.inheritances[0], self.m.interface_by_name('GlobalBase'))
        from_global = self.moduleP.interface_by_name('FromGlobal')
        self.assertIs(from_global.inheritances[0], self.m.interface_by_name('GlobalBase'))

    def test_methods_still_parsed(self):
        """Methods of an interface with inheritance are still parsed.

        継承付き interface でもメソッドが解析される。
        """
        multi = self.moduleP.interface_by_name('Multi')
        self.assertEqual([mt.name for mt in multi.methods], ['methodMulti'])

    def test_to_dic_contains_inheritances(self):
        """to_dic() contains inheritances.

        to_dic() に inheritances が出る。
        """
        dic = self.moduleP.interface_by_name('Multi').to_dic()
        self.assertEqual(dic['inheritances'], ['moduleP::Base', 'moduleP::Other'])
        self.assertEqual(self.moduleP.interface_by_name('Base').to_dic()['inheritances'], [])


class GeneralizationSyntaxTestFunctions(unittest.TestCase):
    """Category: Interfaces, operations and inheritance / カテゴリ: interface・operation・継承

    Inheritance written inline, including spacing variants and errors.
    インラインで書いた継承(空白の違いとエラーを含む)。
    """

    def load(self, idl):
        with contextlib.redirect_stdout(io.StringIO()):
            return parser.IDLParser().load(idl)

    def test_issue5_example(self):
        """The example from issue #5 (interface derived : base).

        issue #5 の例(interface derived : base)。
        """
        m = self.load('module Example { interface base { }; interface derived : base { }; };')
        derived = m.module_by_name('Example').interface_by_name('derived')
        self.assertEqual(bases(derived), ['Example::base'])

    def test_spacing_variants(self):
        """Spacing variants around the colon, such as "B:A" and "B : A".

        「B:A」「B : A」などコロン前後の空白の違い。
        """
        for decl in ('B:A', 'B : A', 'B: A', 'B :A'):
            with self.subTest(decl=decl):
                m = self.load('module M { interface A {}; interface %s {}; };' % decl)
                self.assertEqual(bases(m.module_by_name('M').interface_by_name('B')), ['M::A'])

    def test_multiple_inheritance_spacing(self):
        """Multiple inheritance written without spaces, as in "A,B".

        「A,B」のように空白なしの多重継承。
        """
        m = self.load('module M { interface A {}; interface B {}; interface C : A,B {}; };')
        self.assertEqual(bases(m.module_by_name('M').interface_by_name('C')), ['M::A', 'M::B'])

    def test_undefined_base(self):
        """An undefined base raises IDLCanNotFindException.

        存在しない継承元で IDLCanNotFindException。
        """
        with self.assertRaises(exception.IDLCanNotFindException):
            self.load('module M { interface B : Nope {}; };')

    def test_base_must_be_declared_before(self):
        """A base defined later is an error.

        後で定義される継承元はエラー。
        """
        with self.assertRaises(exception.IDLCanNotFindException):
            self.load('module M { interface B : A {}; interface A {}; };')

    def test_base_must_be_interface(self):
        """Inheriting from a struct is an error.

        struct を継承するとエラー。
        """
        with self.assertRaises(exception.IDLCanNotFindException):
            self.load('module M { struct S { long a; }; interface B : S {}; };')

    def test_absolute_name_is_not_relative(self):
        """::Base is not resolved as a relative name (error).

        ::Base は相対名として解決しない(エラー)。
        """
        # "::Base" means the global Base only, even if M::Base exists
        with self.assertRaises(exception.IDLCanNotFindException):
            self.load('module M { interface Base {}; interface B : ::Base {}; };')

    def test_duplicate_base(self):
        """A duplicate base raises InvalidIDLSyntaxError.

        同じ継承元の重複で InvalidIDLSyntaxError。
        """
        with self.assertRaises(exception.InvalidIDLSyntaxError):
            self.load('module M { interface A {}; interface B : A, A {}; };')

    def test_missing_base_name(self):
        """A missing name after the colon or comma is an error.

        コロンやカンマの後に名前がないとエラー。
        """
        for decl in ('B : {}', 'B : A, {}'):
            with self.subTest(decl=decl):
                with self.assertRaises(exception.InvalidIDLSyntaxError):
                    self.load('module M { interface A {}; interface %s; };' % decl)

    def test_errors_are_parser_exceptions(self):
        """Inheritance errors are subclasses of IDLParserException.

        継承のエラーが IDLParserException の派生である。
        """
        # Previously these paths raised NameError (exception module not imported)
        with self.assertRaises(exception.IDLParserException):
            self.load('module M { interface B : Nope {}; };')


if __name__ == '__main__':
    unittest.main()
