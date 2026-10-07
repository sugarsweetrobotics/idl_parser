"""Regression tests for issue #69.

A fully qualified type name with a leading '::' ("::M::A") was not found by
find_types(), so it raised InvalidDataTypeException (struct and union
members), IndexError (typedef), or was silently left unresolved
(``obj`` was None for sequence elements and method arguments).
The leading '::' is now dropped before comparing, and a typedef of an
unknown type raises InvalidDataTypeException.
"""
import contextlib
import io
import unittest
from idl_parser import parser
from idl_parser import exception

A = 'module M { struct A { long x; }; }; '


def load(idl):
    with contextlib.redirect_stdout(io.StringIO()):
        return parser.IDLParser().load(idl)


class LeadingScopeTestFunctions(unittest.TestCase):

    def assertIsMA(self, obj):
        self.assertIsNotNone(obj)
        self.assertEqual(obj.classname, 'IDLStruct')
        self.assertEqual(obj.full_path, 'M::A')

    def test_find_types(self):
        r = load(A)
        self.assertEqual(len(r.find_types('M::A')), 1)
        self.assertEqual(len(r.find_types('::M::A')), 1)
        self.assertIsMA(r.find_types('::M::A')[0])

    def test_find_types_leading_scope_is_global(self):
        # '::A' names a global A only, not M::A
        r = load(A)
        self.assertEqual(len(r.find_types('::A')), 0)
        r = load(A + 'struct A { long y; };')
        typs = r.find_types('::A')
        self.assertEqual(len(typs), 1)
        self.assertEqual(typs[0].full_path.lstrip(':'), 'A')

    def test_struct_member(self):
        r = load(A + 'module K { struct S { ::M::A d; }; };')
        m = r.module_by_name('K').struct_by_name('S').members[0]
        self.assertIsMA(m.type.obj)

    def test_typedef(self):
        r = load(A + 'module K { typedef ::M::A T; };')
        self.assertIsMA(r.module_by_name('K').typedef_by_name('T').type)

    def test_union_member(self):
        r = load(A + 'module K { union U switch (long) { case 1: ::M::A a; }; };')
        u = r.module_by_name('K').union_by_name('U')
        self.assertIsMA(u.members[0].type.obj)

    def test_sequence_member(self):
        r = load(A + 'module K { struct S { sequence< ::M::A> c; }; };')
        m = r.module_by_name('K').struct_by_name('S').members[0]
        self.assertIsMA(m.type.inner_type.obj)

    def test_method_argument(self):
        r = load(A + 'module K { interface I { void f(in ::M::A a); }; };')
        i = r.module_by_name('K').interface_by_name('I')
        self.assertIsMA(i.methods[0].arguments[0].type.obj)

    def test_typedef_unknown_type(self):
        with self.assertRaises(exception.InvalidDataTypeException):
            load(A + 'module K { typedef ::M::Z T; };')
        with self.assertRaises(exception.InvalidDataTypeException):
            load('module K { typedef Nope T; };')


if __name__ == '__main__':
    unittest.main()
