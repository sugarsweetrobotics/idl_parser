import os
import contextlib
import io
import unittest
from idl_parser import parser
from idl_parser import exception

IDL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'idls')


idl_path = os.path.join(IDL_DIR, 'forward_declaration.idl')


def load(idl):
    with contextlib.redirect_stdout(io.StringIO()):
        return parser.IDLParser().load(idl)


class ForwardDeclarationTestFunctions(unittest.TestCase):
    """Forward declarations of interfaces ("interface A;") parsed from a file."""

    @classmethod
    def setUpClass(cls):
        with open(idl_path, 'r') as idlf:
            cls.m = parser.IDLParser().load(idlf.read())
        cls.moduleF = cls.m.module_by_name('moduleF')

    def test_definitions_are_interfaces(self):
        names = [i.name for i in self.moduleF.interfaces]
        self.assertEqual(names, ['Graph', 'Node', 'Item', 'SubItem', 'Twice', 'Reopened'])
        for i in self.moduleF.interfaces:
            self.assertFalse(i.is_forward)

    def test_forward_declarations_are_recorded_once(self):
        self.assertEqual(self.moduleF.forward_interfaces,
                         ['Node', 'Item', 'Twice', 'Undefined', 'Reopened'])

    def test_undefined_forward_interfaces(self):
        self.assertEqual(self.moduleF.undefined_forward_interfaces, ['Undefined'])
        self.assertIsNone(self.moduleF.interface_by_name('Undefined'))

    def test_mutual_references(self):
        graph = self.moduleF.interface_by_name('Graph')
        self.assertEqual(graph.method_by_name('root').returns.name, 'Node')
        self.assertEqual(graph.method_by_name('addNode').arguments[0].type.name, 'Node')
        node = self.moduleF.interface_by_name('Node')
        self.assertEqual(node.method_by_name('owner').returns.name, 'Graph')

    def test_struct_member_resolves_to_definition(self):
        holder = self.moduleF.struct_by_name('Holder')
        item = holder.members[0].type
        self.assertTrue(item.is_interface)
        self.assertIs(item, self.moduleF.interface_by_name('Item'))

    def test_sequence_of_forward_interface(self):
        item_list = self.moduleF.typedef_by_name('ItemList')
        self.assertTrue(item_list.type.is_sequence)
        self.assertEqual(item_list.type.name, 'sequence < Item >')
        self.assertEqual(item_list.type.inner_type.name, 'Item')

    def test_typedef_of_forward_interface(self):
        alias = self.moduleF.typedef_by_name('ItemAlias')
        self.assertIs(alias.type, self.moduleF.interface_by_name('Item'))

    def test_union_member_resolves_to_definition(self):
        choice = self.moduleF.union_by_name('Choice')
        self.assertIs(choice.members[0].type, self.moduleF.interface_by_name('Item'))

    def test_inheritance_after_definition(self):
        sub = self.moduleF.interface_by_name('SubItem')
        self.assertEqual([i.full_path for i in sub.inheritances], ['moduleF::Item'])

    def test_definition_after_module_reopened(self):
        self.assertEqual(len(self.m.modules), 1)
        reopened = self.moduleF.interface_by_name('Reopened')
        self.assertIsNotNone(reopened.method_by_name('reopenedMethod'))

    def test_global_scope(self):
        self.assertEqual(self.m.forward_interfaces, ['GlobalForward'])
        self.assertEqual(self.m.undefined_forward_interfaces, [])
        user = self.m.interface_by_name('GlobalUser')
        self.assertEqual(user.methods[0].arguments[0].type.name, 'GlobalForward')


class ForwardDeclarationSyntaxTestFunctions(unittest.TestCase):
    """Inline cases, including errors."""

    def test_forward_only(self):
        m = load('module M { interface A; };')
        M = m.module_by_name('M')
        self.assertEqual(M.interfaces, [])
        self.assertEqual(M.forward_interfaces, ['A'])

    def test_forward_after_definition(self):
        m = load('module M { interface A { void f(); }; interface A; };')
        M = m.module_by_name('M')
        self.assertEqual([i.name for i in M.interfaces], ['A'])
        self.assertIsNotNone(M.interface_by_name('A').method_by_name('f'))
        self.assertEqual(M.undefined_forward_interfaces, [])

    def test_scoped_reference_to_forward_interface(self):
        m = load('module M { interface A; }; module N { struct S { M::A a; }; }; module M { interface A {}; };')
        s = m.module_by_name('N').struct_by_name('S')
        self.assertEqual(s.members[0].type.full_path, 'M::A')

    def test_inherit_from_forward_only_is_error(self):
        # OMG IDL: a base interface must be defined, not just forward-declared
        with self.assertRaises(exception.IDLCanNotFindException):
            load('module M { interface A; interface B : A {}; interface A {}; };')

    def test_inner_forward_declaration_hides_outer_definition(self):
        # "Base" in Q refers to Q::Base (still incomplete), not the global Base
        with self.assertRaises(exception.IDLCanNotFindException):
            load('interface Base {}; module Q { interface Base; interface X : Base {}; };')

    def test_undeclared_type_is_still_an_error(self):
        with self.assertRaises(exception.InvalidDataTypeException):
            load('module M { struct S { Nope a; }; };')

    def test_undeclared_union_member_type_is_parser_error(self):
        # Previously raised NameError (exception class not imported in union.py)
        with self.assertRaises(exception.InvalidDataTypeException):
            load('module M { union U switch (long) { case 1: Nope a; }; };')


if __name__ == '__main__':
    unittest.main()
