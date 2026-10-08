"""Regression tests for issue #57.

Forward declarations of structs and unions ("struct F;", "union U;") failed
with InvalidIDLSyntaxError. They are now handled like forward-declared
interfaces: the module records the name in forward_structs / forward_unions,
and the definition that follows (if any) is the one in structs / unions.
"""
import contextlib
import io
import unittest
from idl_parser import parser
from idl_parser import exception


def load(idl):
    with contextlib.redirect_stdout(io.StringIO()):
        return parser.IDLParser().load(idl)


class ForwardStructTestFunctions(unittest.TestCase):
    """Category: Forward declarations / カテゴリ: 前方宣言

    Forward declarations of structs ("struct F;") (issue #57).
    struct の前方宣言("struct F;")(#57)。
    """

    def test_forward_only(self):
        """"struct F;" without a definition.

        struct F; だけで本定義がない場合。
        """
        M = load('module M { struct F; };').module_by_name('M')
        self.assertEqual(M.structs, [])
        self.assertEqual(M.forward_structs, ['F'])
        self.assertEqual(M.undefined_forward_structs, ['F'])
        self.assertIsNone(M.struct_by_name('F'))

    def test_forward_then_definition(self):
        """A struct forward declaration followed by its definition.

        struct の前方宣言の後に本定義。
        """
        M = load('module M { struct F; struct F { long x; }; };').module_by_name('M')
        self.assertEqual([s.name for s in M.structs], ['F'])
        self.assertFalse(M.struct_by_name('F').is_forward)
        self.assertEqual(M.struct_by_name('F').members[0].name, 'x')
        self.assertEqual(M.forward_structs, ['F'])
        self.assertEqual(M.undefined_forward_structs, [])

    def test_forward_after_definition(self):
        """A struct forward declaration after its definition.

        struct の本定義の後に前方宣言。
        """
        M = load('module M { struct F { long x; }; struct F; };').module_by_name('M')
        self.assertEqual([s.name for s in M.structs], ['F'])
        self.assertEqual(M.struct_by_name('F').members[0].name, 'x')
        self.assertEqual(M.undefined_forward_structs, [])

    def test_redundant_forward_is_recorded_once(self):
        """A repeated struct forward declaration is recorded once.

        struct の重複した前方宣言が1回だけ記録される。
        """
        M = load('module M { struct F; struct F; };').module_by_name('M')
        self.assertEqual(M.forward_structs, ['F'])

    def test_sequence_member_of_forward_struct(self):
        """A sequence<forward-declared struct> member resolves to the definition.

        sequence<前方宣言 struct> メンバーが本定義に解決される。
        """
        M = load('module M { struct F; struct G { sequence<F> fs; };'
                 ' struct F { long x; }; };').module_by_name('M')
        fs = M.struct_by_name('G').members[0].type
        self.assertTrue(fs.is_sequence)
        self.assertEqual(fs.name, 'sequence < F >')
        self.assertEqual(fs.inner_type.name, 'F')
        self.assertIs(fs.inner_type.obj, M.struct_by_name('F'))

    def test_recursive_struct_through_typedef(self):
        """A recursive struct through a forward declaration and a sequence typedef.

        前方宣言＋typedef sequence による再帰 struct。
        """
        M = load('module M { struct Node; typedef sequence<Node> NodeSeq;'
                 ' struct Node { long value; NodeSeq children; }; };').module_by_name('M')
        node = M.struct_by_name('Node')
        self.assertEqual(M.typedef_by_name('NodeSeq').type.name, 'sequence < Node >')
        self.assertIs(node.members[1].type, M.typedef_by_name('NodeSeq'))

    def test_scoped_reference_to_forward_struct(self):
        """A forward-declared struct referenced as M::F from another module.

        別モジュールから M::F で前方宣言 struct を参照。
        """
        m = load('module M { struct F; }; module N { struct S { sequence<M::F> fs; }; };'
                 ' module M { struct F { long x; }; };')
        fs = m.module_by_name('N').struct_by_name('S').members[0].type
        self.assertEqual(fs.inner_type.name, 'M::F')
        self.assertIs(fs.inner_type.obj, m.module_by_name('M').struct_by_name('F'))

    def test_global_scope(self):
        """Forward declaration of a struct at global scope.

        グローバルスコープでの struct 前方宣言。
        """
        m = load('struct F; struct G { sequence<F> fs; }; struct F { long x; };')
        self.assertEqual(m.forward_structs, ['F'])
        self.assertEqual(m.undefined_forward_structs, [])

    def test_to_dic_has_no_forward_entry(self):
        """to_simple_dic() has no entry for the forward declaration.

        to_simple_dic() に前方宣言の項目が出ない。
        """
        M = load('module M { struct F; struct F { long x; }; };').module_by_name('M')
        self.assertEqual(M.to_simple_dic(), {'module M': [{'struct F': [{'x': 'long'}]}]})

    def test_missing_brace_is_still_an_error(self):
        """A struct without "{" is still an error.

        { のない struct は従来どおりエラー。
        """
        with self.assertRaises(exception.InvalidIDLSyntaxError):
            load('module M { struct F long x; };')

    def test_undeclared_type_is_still_an_error(self):
        """An undeclared type still raises InvalidDataTypeException.

        未宣言の型は従来どおり InvalidDataTypeException。
        """
        with self.assertRaises(exception.InvalidDataTypeException):
            load('module M { struct F; struct G { Nope n; }; };')


class ForwardUnionTestFunctions(unittest.TestCase):
    """Category: Forward declarations / カテゴリ: 前方宣言

    Forward declarations of unions ("union U;") (issue #57).
    union の前方宣言("union U;")(#57)。
    """

    def test_forward_only(self):
        """"union U;" without a definition.

        union U; だけで本定義がない場合。
        """
        M = load('module M { union U; };').module_by_name('M')
        self.assertEqual(M.unions, [])
        self.assertEqual(M.forward_unions, ['U'])
        self.assertEqual(M.undefined_forward_unions, ['U'])

    def test_forward_then_definition(self):
        """A union forward declaration followed by its definition.

        union の前方宣言の後に本定義。
        """
        M = load('module M { union U; union U switch (long) { case 1: long a; }; };').module_by_name('M')
        u = M.union_by_name('U')
        self.assertFalse(u.is_forward)
        self.assertEqual(u.descriminator_kind, 'long')
        self.assertEqual([x.name for x in u.members], ['a'])
        self.assertEqual(M.undefined_forward_unions, [])

    def test_sequence_member_of_forward_union(self):
        """A sequence<forward-declared union> member resolves to the definition.

        sequence<前方宣言 union> メンバーが本定義に解決される。
        """
        M = load('module M { union U; struct S { sequence<U> us; };'
                 ' union U switch (long) { case 1: long a; }; };').module_by_name('M')
        us = M.struct_by_name('S').members[0].type
        self.assertEqual(us.name, 'sequence < U >')
        self.assertIs(us.inner_type.obj, M.union_by_name('U'))

    def test_missing_switch_is_still_an_error(self):
        """A union without switch is still an error.

        switch のない union は従来どおりエラー。
        """
        with self.assertRaises(exception.InvalidIDLSyntaxError):
            load('module M { union U { case 1: long a; }; };')


class ForwardKindsAreSeparateTestFunctions(unittest.TestCase):
    """Category: Forward declarations / カテゴリ: 前方宣言

    Forward declarations of each kind are recorded separately.
    前方宣言は種類ごとに分けて記録される。
    """

    def test_kinds_are_recorded_separately(self):
        """Forward declarations of structs, unions and interfaces are recorded per kind.

        struct/union/interface の前方宣言が種類別に記録される。
        """
        M = load('module M { struct S; union U; interface I; };').module_by_name('M')
        self.assertEqual(M.forward_structs, ['S'])
        self.assertEqual(M.forward_unions, ['U'])
        self.assertEqual(M.forward_interfaces, ['I'])

    def test_is_pending_forward_interface_ignores_structs(self):
        """is_pending_forward_interface() ignores structs; is_pending_forward_declaration() covers both.

        is_pending_forward_interface() は struct を対象外、is_pending_forward_declaration() は両方対象。
        """
        M = load('module M { struct S; interface I; };').module_by_name('M')
        self.assertFalse(M.is_pending_forward_interface('S'))
        self.assertTrue(M.is_pending_forward_interface('I'))
        self.assertTrue(M.is_pending_forward_declaration('S'))
        self.assertTrue(M.is_pending_forward_declaration('I'))


if __name__ == '__main__':
    unittest.main()
