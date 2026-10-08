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
    def setUp(self):
        pass

    def test_module(self):
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
    """Interface inheritance cases from issue #5."""

    @classmethod
    def setUpClass(cls):
        with open(extended_idl_path, 'r') as idlf:
            cls.m = parser.IDLParser().load(idlf.read())
        cls.moduleP = cls.m.module_by_name('moduleP')
        cls.moduleQ = cls.m.module_by_name('moduleQ')

    def test_inheritances_are_interface_objects(self):
        derived = self.moduleP.interface_by_name('Derived')
        base = self.moduleP.interface_by_name('Base')
        self.assertIs(derived.inheritances[0], base)
        self.assertTrue(derived.inheritances[0].is_interface)
        self.assertIsNotNone(derived.inheritances[0].method_by_name('methodBase'))

    def test_no_inheritance(self):
        self.assertEqual(bases(self.moduleP.interface_by_name('Base')), [])

    def test_unqualified_name_in_same_module(self):
        self.assertEqual(bases(self.moduleP.interface_by_name('Derived')), ['moduleP::Base'])

    def test_multi_level_inheritance(self):
        grandchild = self.moduleP.interface_by_name('Grandchild')
        self.assertEqual(bases(grandchild), ['moduleP::Derived'])
        self.assertEqual(bases(grandchild.inheritances[0]), ['moduleP::Base'])

    def test_multiple_inheritance_keeps_order(self):
        self.assertEqual(bases(self.moduleP.interface_by_name('Multi')),
                         ['moduleP::Base', 'moduleP::Other'])

    def test_absolute_name(self):
        self.assertEqual(bases(self.moduleP.interface_by_name('Absolute')), ['moduleP::Base'])

    def test_scoped_name_in_other_module(self):
        self.assertEqual(bases(self.moduleQ.interface_by_name('CrossDerived')), ['moduleP::Base'])

    def test_innermost_scope_wins(self):
        self.assertEqual(bases(self.moduleQ.interface_by_name('LocalDerived')), ['moduleQ::Base'])

    def test_enclosing_scope_lookup(self):
        inner = self.moduleQ.module_by_name('inner')
        self.assertEqual(bases(inner.interface_by_name('InnerDerived')), ['moduleQ::Base'])

    def test_global_scope(self):
        global_derived = self.m.interface_by_name('GlobalDerived')
        self.assertIs(global_derived.inheritances[0], self.m.interface_by_name('GlobalBase'))
        from_global = self.moduleP.interface_by_name('FromGlobal')
        self.assertIs(from_global.inheritances[0], self.m.interface_by_name('GlobalBase'))

    def test_methods_still_parsed(self):
        multi = self.moduleP.interface_by_name('Multi')
        self.assertEqual([mt.name for mt in multi.methods], ['methodMulti'])

    def test_to_dic_contains_inheritances(self):
        dic = self.moduleP.interface_by_name('Multi').to_dic()
        self.assertEqual(dic['inheritances'], ['moduleP::Base', 'moduleP::Other'])
        self.assertEqual(self.moduleP.interface_by_name('Base').to_dic()['inheritances'], [])


class GeneralizationSyntaxTestFunctions(unittest.TestCase):
    """Inheritance written inline, including spacing variants and errors."""

    def load(self, idl):
        with contextlib.redirect_stdout(io.StringIO()):
            return parser.IDLParser().load(idl)

    def test_issue5_example(self):
        m = self.load('module Example { interface base { }; interface derived : base { }; };')
        derived = m.module_by_name('Example').interface_by_name('derived')
        self.assertEqual(bases(derived), ['Example::base'])

    def test_spacing_variants(self):
        for decl in ('B:A', 'B : A', 'B: A', 'B :A'):
            with self.subTest(decl=decl):
                m = self.load('module M { interface A {}; interface %s {}; };' % decl)
                self.assertEqual(bases(m.module_by_name('M').interface_by_name('B')), ['M::A'])

    def test_multiple_inheritance_spacing(self):
        m = self.load('module M { interface A {}; interface B {}; interface C : A,B {}; };')
        self.assertEqual(bases(m.module_by_name('M').interface_by_name('C')), ['M::A', 'M::B'])

    def test_undefined_base(self):
        with self.assertRaises(exception.IDLCanNotFindException):
            self.load('module M { interface B : Nope {}; };')

    def test_base_must_be_declared_before(self):
        with self.assertRaises(exception.IDLCanNotFindException):
            self.load('module M { interface B : A {}; interface A {}; };')

    def test_base_must_be_interface(self):
        with self.assertRaises(exception.IDLCanNotFindException):
            self.load('module M { struct S { long a; }; interface B : S {}; };')

    def test_absolute_name_is_not_relative(self):
        # "::Base" means the global Base only, even if M::Base exists
        with self.assertRaises(exception.IDLCanNotFindException):
            self.load('module M { interface Base {}; interface B : ::Base {}; };')

    def test_duplicate_base(self):
        with self.assertRaises(exception.InvalidIDLSyntaxError):
            self.load('module M { interface A {}; interface B : A, A {}; };')

    def test_missing_base_name(self):
        for decl in ('B : {}', 'B : A, {}'):
            with self.subTest(decl=decl):
                with self.assertRaises(exception.InvalidIDLSyntaxError):
                    self.load('module M { interface A {}; interface %s; };' % decl)

    def test_errors_are_parser_exceptions(self):
        # Previously these paths raised NameError (exception module not imported)
        with self.assertRaises(exception.IDLParserException):
            self.load('module M { interface B : Nope {}; };')


if __name__ == '__main__':
    unittest.main()
