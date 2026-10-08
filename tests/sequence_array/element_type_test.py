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
    """Category: Sequences, arrays and typedefs / カテゴリ: sequence・array・typedef

    Undeclared element types of sequences and arrays are errors (issue #67).
    sequence/配列の未宣言の要素型はエラーになる(#67)。
    """

    def assertInvalidType(self, idl):
        with self.assertRaises(exception.InvalidDataTypeException):
            load(idl)

    def test_direct_member(self):
        """A member of an undeclared type raises InvalidDataTypeException.

        未宣言型の直接メンバーで InvalidDataTypeException。
        """
        self.assertInvalidType('module M { struct S { Nope n; }; };')

    def test_sequence_member(self):
        """A sequence<undeclared type> member is an error.

        sequence<未宣言型> メンバーでエラー。
        """
        self.assertInvalidType('module M { struct S { sequence<Nope> ns; }; };')

    def test_sequence_typedef(self):
        """A typedef of sequence<undeclared type> is an error.

        sequence<未宣言型> の typedef でエラー。
        """
        self.assertInvalidType('module M { typedef sequence<Nope> NS; };')

    def test_sequence_union_member(self):
        """A sequence<undeclared type> union member is an error.

        union の sequence<未宣言型> メンバーでエラー。
        """
        self.assertInvalidType(
            'module M { union U switch (long) { case 1: sequence<Nope> ns; }; };')

    def test_nested_sequence_member(self):
        """An undeclared type in a nested sequence is an error.

        入れ子 sequence の未宣言型でエラー。
        """
        self.assertInvalidType(
            'module M { struct S { sequence<sequence<Nope> > ns; }; };')

    def test_bounded_sequence_member(self):
        """An undeclared type in a bounded sequence is an error.

        上限付き sequence の未宣言型でエラー。
        """
        self.assertInvalidType('module M { struct S { sequence<Nope, 5> ns; }; };')

    def test_array_member(self):
        """An array member of an undeclared type is an error.

        未宣言型の配列メンバーでエラー。
        """
        self.assertInvalidType('module M { struct S { Nope ns[3]; }; };')

    def test_multi_dimensional_array_member(self):
        """A multi-dimensional array of an undeclared type is an error.

        未宣言型の多次元配列でエラー。
        """
        self.assertInvalidType('module M { struct S { Nope ns[3][2]; }; };')

    def test_array_typedef(self):
        """An array typedef of an undeclared type is an error.

        未宣言型の配列 typedef でエラー。
        """
        self.assertInvalidType('module M { typedef Nope NS[3]; };')

    def test_array_union_member(self):
        """A union array member of an undeclared type is an error.

        union の未宣言型配列メンバーでエラー。
        """
        self.assertInvalidType(
            'module M { union U switch (long) { case 1: Nope ns[3]; }; };')

    def test_type_declared_later_is_not_found(self):
        """A type declared later cannot be used as a sequence element type.

        後で宣言される型を sequence 要素に使うとエラー。
        """
        # Without a forward declaration a type must be declared before use
        self.assertInvalidType(
            'module M { struct S { sequence<T> ts; }; struct T { long x; }; };')


class DeclaredElementTypeTestFunctions(unittest.TestCase):
    """Category: Sequences, arrays and typedefs / カテゴリ: sequence・array・typedef

    Declared and recursive element types of sequences and arrays (issue #67).
    宣言済み・再帰的な sequence/配列の要素型(#67)。
    """

    def test_declared_struct(self):
        """Element types of sequences and arrays of a declared struct are resolved.

        宣言済み struct の sequence/配列の要素型が解決される。
        """
        M = load('module M { struct A { long x; };'
                 ' struct S { sequence<A> as_; A arr[2]; }; };').module_by_name('M')
        S = M.struct_by_name('S')
        self.assertIs(S.members[0].type.inner_type.obj, M.struct_by_name('A'))
        self.assertIs(S.members[1].type.inner_type.obj, M.struct_by_name('A'))

    def test_scoped_names(self):
        """Scoped and absolute names are accepted as element types.

        スコープ付き名・絶対名の要素型が受け付けられる。
        """
        idl = ('module M { struct A { long x; }; module N { struct S { sequence<A> a; }; }; };'
               ' module K { struct S { sequence<M::A> a; sequence< ::M::A> b; }; };')
        load(idl)

    def test_recursive_struct(self):
        """A recursive struct holding a sequence of itself.

        自分自身の sequence を持つ再帰 struct。
        """
        M = load('module M { struct Node { long v; sequence<Node> children; }; };'
                 ).module_by_name('M')
        node = M.struct_by_name('Node')
        self.assertIs(node.members[1].type.inner_type.obj, node)

    def test_recursive_union(self):
        """A recursive union holding a sequence of itself.

        自分自身の sequence を持つ再帰 union。
        """
        M = load('module M { union U switch (long) { case 1: sequence<U> us; }; };'
                 ).module_by_name('M')
        U = M.union_by_name('U')
        self.assertIs(U.members[0].type.inner_type.obj, U)


if __name__ == '__main__':
    unittest.main()
