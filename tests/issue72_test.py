"""Regression tests for issue #72.

When types with the same name were defined in several modules, a type name
was resolved to the first definition found, whatever the name written
(``X``, ``B::X`` or ``::B::X``). Names written relative to a nested scope
(``C::X``) were not found at all.

Type names are now resolved with the IDL scoping rules: from the scope
where they are written, innermost first, and from the global scope only
when they start with ``::``.
"""
import contextlib
import io
import unittest
from idl_parser import parser
from idl_parser import exception


def load(idl):
    with contextlib.redirect_stdout(io.StringIO()):
        return parser.IDLParser().load(idl)


def path(node):
    return node.full_path.lstrip(':')


AB = 'module A { struct X { long a; }; }; module B { struct X { long b; }; '

NESTED = ('module A { struct X { long a; }; module C { struct X { long ac; }; }; }; '
          'module B { struct X { long b; }; '
          '  module C { struct X { long bc; }; '
          '    module D { interface Y { %s f(in %s x); }; }; '
          '  }; '
          '};')


class TwoModulesTestFunctions(unittest.TestCase):
    """A::X and B::X, referenced from module B."""

    cases = [('X', 'B::X'), ('B::X', 'B::X'), ('::B::X', 'B::X'),
             ('A::X', 'A::X'), ('::A::X', 'A::X')]

    def test_method_argument_and_return(self):
        for ref, expected in self.cases:
            with self.subTest(ref=ref):
                r = load(AB + 'interface Y { %s f(in %s x); }; };' % (ref, ref))
                m = r.module_by_name('B').interface_by_name('Y').methods[0]
                self.assertEqual(path(m.arguments[0].type.obj), expected)
                self.assertEqual(path(m.returns.obj), expected)

    def test_struct_member(self):
        for ref, expected in self.cases:
            with self.subTest(ref=ref):
                r = load(AB + 'struct S { %s m; %s a[2]; sequence<%s> s; }; };' % (ref, ref, ref))
                s = r.module_by_name('B').struct_by_name('S')
                self.assertEqual(path(s.members[0].type), expected)
                self.assertEqual(path(s.members[1].type.inner_type.obj), expected)
                self.assertEqual(path(s.members[2].type.inner_type.obj), expected)

    def test_union_member(self):
        for ref, expected in self.cases:
            with self.subTest(ref=ref):
                r = load(AB + 'union U switch (long) { case 1: %s x; }; };' % ref)
                u = r.module_by_name('B').union_by_name('U')
                self.assertEqual(path(u.members[0].type), expected)

    def test_typedef(self):
        for ref, expected in self.cases:
            with self.subTest(ref=ref):
                r = load(AB + 'typedef %s T; };' % ref)
                t = r.module_by_name('B').typedef_by_name('T')
                self.assertEqual(path(t.type), expected)

    def test_typedef_resolved_in_its_own_scope(self):
        # T is defined in A as X, so it is A::X even when used from B
        r = load('module A { struct X { long a; }; typedef X T; }; '
                 'module B { struct X { long b; }; struct S { A::T t; }; };')
        t = r.module_by_name('B').struct_by_name('S').members[0].type
        self.assertEqual(path(t), 'A::T')
        self.assertEqual(path(t.type), 'A::X')

    def test_name_is_kept_short(self):
        # The name of a type is still the name of the definition
        r = load(AB + 'interface Y { void f(in A::X x); }; };')
        t = r.module_by_name('B').interface_by_name('Y').methods[0].arguments[0].type
        self.assertEqual(t.name, 'X')
        self.assertEqual(t.ref_name, 'A::X')


class NestedModulesTestFunctions(unittest.TestCase):
    """A::X, A::C::X, B::X and B::C::X, referenced from B::C::D::Y."""

    def test_references(self):
        cases = [('X', 'B::C::X'), ('C::X', 'B::C::X'),
                 ('B::X', 'B::X'), ('B::C::X', 'B::C::X'),
                 ('A::X', 'A::X'), ('A::C::X', 'A::C::X'),
                 ('::B::X', 'B::X'), ('::B::C::X', 'B::C::X'),
                 ('::A::X', 'A::X'), ('::A::C::X', 'A::C::X')]
        for ref, expected in cases:
            with self.subTest(ref=ref):
                r = load(NESTED % (ref, ref))
                y = r.module_by_name('B').module_by_name('C').module_by_name('D').interface_by_name('Y')
                self.assertEqual(path(y.methods[0].arguments[0].type.obj), expected)
                self.assertEqual(path(y.methods[0].returns.obj), expected)

    def test_outer_scope(self):
        # Not found in B::C, so X is B::X
        r = load('struct X { long g; }; module A { struct X { long a; }; }; '
                 'module B { struct X { long b; }; module C { struct S { X m; }; }; };')
        s = r.module_by_name('B').module_by_name('C').struct_by_name('S')
        self.assertEqual(path(s.members[0].type), 'B::X')

    def test_global_scope(self):
        r = load('struct X { long g; }; module A { struct X { long a; }; }; '
                 'module B { struct S { X m; ::X g; }; };')
        s = r.module_by_name('B').struct_by_name('S')
        self.assertEqual(path(s.members[0].type), 'X')
        self.assertEqual(path(s.members[1].type), 'X')

    def test_absolute_name_is_not_relative(self):
        # '::C::X' is not B::C::X
        with self.assertRaises(exception.InvalidDataTypeException):
            load('module B { module C { struct X { long bc; }; }; struct S { ::C::X m; }; };')


class FindTypesTestFunctions(unittest.TestCase):

    def test_find_types_with_scope(self):
        r = load(AB + '};')
        b = r.module_by_name('B')
        self.assertEqual([path(t) for t in r.find_types('X', scope=b)], ['B::X'])
        self.assertEqual([path(t) for t in r.find_types('A::X', scope=b)], ['A::X'])
        self.assertEqual([path(t) for t in r.find_types('::A::X', scope=b)], ['A::X'])

    def test_find_types_without_scope(self):
        # Without a scope, every definition with the name is returned as before
        r = load(AB + '};')
        self.assertEqual(sorted(path(t) for t in r.find_types('X')), ['A::X', 'B::X'])


if __name__ == '__main__':
    unittest.main()
