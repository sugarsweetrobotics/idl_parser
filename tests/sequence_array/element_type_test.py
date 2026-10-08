"""Element types of sequences and arrays must be declared (issue #67).

An undeclared type used directly as a member raised InvalidDataTypeException,
but the same type used as the element type of a sequence<> or an array was
accepted, and the parsed result failed later (e.g. ``inner_type.obj`` was None).
Forward-declared element types are covered in
tests/forward_declaration/element_type_forward_test.py.
"""
import contextlib
import io
import unittest
from idl_parser import parser
from idl_parser import exception


def load(idl):
    with contextlib.redirect_stdout(io.StringIO()):
        return parser.IDLParser().load(idl)


class UndeclaredElementTypeTestFunctions(unittest.TestCase):

    def assertInvalidType(self, idl):
        with self.assertRaises(exception.InvalidDataTypeException):
            load(idl)

    def test_direct_member(self):
        self.assertInvalidType('module M { struct S { Nope n; }; };')

    def test_sequence_member(self):
        self.assertInvalidType('module M { struct S { sequence<Nope> ns; }; };')

    def test_sequence_typedef(self):
        self.assertInvalidType('module M { typedef sequence<Nope> NS; };')

    def test_sequence_union_member(self):
        self.assertInvalidType(
            'module M { union U switch (long) { case 1: sequence<Nope> ns; }; };')

    def test_nested_sequence_member(self):
        self.assertInvalidType(
            'module M { struct S { sequence<sequence<Nope> > ns; }; };')

    def test_bounded_sequence_member(self):
        self.assertInvalidType('module M { struct S { sequence<Nope, 5> ns; }; };')

    def test_array_member(self):
        self.assertInvalidType('module M { struct S { Nope ns[3]; }; };')

    def test_multi_dimensional_array_member(self):
        self.assertInvalidType('module M { struct S { Nope ns[3][2]; }; };')

    def test_array_typedef(self):
        self.assertInvalidType('module M { typedef Nope NS[3]; };')

    def test_array_union_member(self):
        self.assertInvalidType(
            'module M { union U switch (long) { case 1: Nope ns[3]; }; };')

    def test_type_declared_later_is_not_found(self):
        # Without a forward declaration a type must be declared before use
        self.assertInvalidType(
            'module M { struct S { sequence<T> ts; }; struct T { long x; }; };')


class DeclaredElementTypeTestFunctions(unittest.TestCase):

    def test_declared_struct(self):
        M = load('module M { struct A { long x; };'
                 ' struct S { sequence<A> as_; A arr[2]; }; };').module_by_name('M')
        S = M.struct_by_name('S')
        self.assertIs(S.members[0].type.inner_type.obj, M.struct_by_name('A'))
        self.assertIs(S.members[1].type.inner_type.obj, M.struct_by_name('A'))

    def test_scoped_names(self):
        idl = ('module M { struct A { long x; }; module N { struct S { sequence<A> a; }; }; };'
               ' module K { struct S { sequence<M::A> a; sequence< ::M::A> b; }; };')
        load(idl)

    def test_recursive_struct(self):
        M = load('module M { struct Node { long v; sequence<Node> children; }; };'
                 ).module_by_name('M')
        node = M.struct_by_name('Node')
        self.assertIs(node.members[1].type.inner_type.obj, node)

    def test_recursive_union(self):
        M = load('module M { union U switch (long) { case 1: sequence<U> us; }; };'
                 ).module_by_name('M')
        U = M.union_by_name('U')
        self.assertIs(U.members[0].type.inner_type.obj, U)


if __name__ == '__main__':
    unittest.main()
