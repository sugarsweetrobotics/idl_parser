"""Forward declarations of interfaces ("interface A;")."""
import os
import contextlib
import io
import unittest
from idl_parser import parser
from idl_parser import exception
from tests import support

IDL_DIR = support.IDL_DIR


idl_path = os.path.join(IDL_DIR, 'forward_declaration.idl')


def load(idl):
    with contextlib.redirect_stdout(io.StringIO()):
        return parser.IDLParser().load(idl)


class ForwardDeclarationTestFunctions(unittest.TestCase):
    """Category: Forward declarations / カテゴリ: 前方宣言

    Forward declarations of interfaces ("interface A;") parsed from forward_declaration.idl.
    forward_declaration.idl から読む interface の前方宣言("interface A;")。
    """

    @classmethod
    def setUpClass(cls):
        with open(idl_path, 'r') as idlf:
            cls.m = parser.IDLParser().load(idlf.read())
        cls.moduleF = cls.m.module_by_name('moduleF')

    def test_definitions_are_interfaces(self):
        """With forward declarations in the IDL, only definitions are in interfaces, and is_forward is false.

        前方宣言のある IDL で、本定義だけが interfaces に入り is_forward が偽。
        """
        names = [i.name for i in self.moduleF.interfaces]
        self.assertEqual(names, ['Graph', 'Node', 'Item', 'SubItem', 'Twice', 'Reopened'])
        for i in self.moduleF.interfaces:
            self.assertFalse(i.is_forward)

    def test_forward_declarations_are_recorded_once(self):
        """Forward-declared names are recorded in forward_interfaces without duplicates.

        前方宣言名が forward_interfaces に重複なく記録される。
        """
        self.assertEqual(self.moduleF.forward_interfaces,
                         ['Node', 'Item', 'Twice', 'Undefined', 'Reopened'])

    def test_undefined_forward_interfaces(self):
        """A forward declaration without a definition stays in undefined_forward_interfaces.

        本定義のない前方宣言が undefined_forward_interfaces に残る。
        """
        self.assertEqual(self.moduleF.undefined_forward_interfaces, ['Undefined'])
        self.assertIsNone(self.moduleF.interface_by_name('Undefined'))

    def test_mutual_references(self):
        """Forward declarations let interfaces refer to each other.

        前方宣言で interface 同士の相互参照ができる。
        """
        graph = self.moduleF.interface_by_name('Graph')
        self.assertEqual(graph.method_by_name('root').returns.name, 'Node')
        self.assertEqual(graph.method_by_name('addNode').arguments[0].type.name, 'Node')
        node = self.moduleF.interface_by_name('Node')
        self.assertEqual(node.method_by_name('owner').returns.name, 'Graph')

    def test_struct_member_resolves_to_definition(self):
        """A struct member of a forward-declared interface type resolves to the definition.

        前方宣言 interface 型の struct メンバーが本定義に解決される。
        """
        holder = self.moduleF.struct_by_name('Holder')
        item = holder.members[0].type
        self.assertTrue(item.is_interface)
        self.assertIs(item, self.moduleF.interface_by_name('Item'))

    def test_sequence_of_forward_interface(self):
        """A typedef of sequence<forward-declared interface>.

        sequence<前方宣言 interface> の typedef。
        """
        item_list = self.moduleF.typedef_by_name('ItemList')
        self.assertTrue(item_list.type.is_sequence)
        self.assertEqual(item_list.type.name, 'sequence < Item >')
        self.assertEqual(item_list.type.inner_type.name, 'Item')

    def test_typedef_of_forward_interface(self):
        """A typedef of a forward-declared interface points to the definition.

        前方宣言 interface の typedef が本定義を指す。
        """
        alias = self.moduleF.typedef_by_name('ItemAlias')
        self.assertIs(alias.type, self.moduleF.interface_by_name('Item'))

    def test_union_member_resolves_to_definition(self):
        """A union member of a forward-declared interface type resolves to the definition.

        前方宣言 interface 型の union メンバーが本定義に解決される。
        """
        choice = self.moduleF.union_by_name('Choice')
        self.assertIs(choice.members[0].type, self.moduleF.interface_by_name('Item'))

    def test_inheritance_after_definition(self):
        """A forward-declared interface can be inherited once it is defined.

        本定義の後なら前方宣言した interface を継承できる。
        """
        sub = self.moduleF.interface_by_name('SubItem')
        self.assertEqual([i.full_path for i in sub.inheritances], ['moduleF::Item'])

    def test_definition_after_module_reopened(self):
        """A definition in a reopened module ends up in the same single module.

        module を再オープンした先で本定義しても1つの module にまとまる。
        """
        self.assertEqual(len(self.m.modules), 1)
        reopened = self.moduleF.interface_by_name('Reopened')
        self.assertIsNotNone(reopened.method_by_name('reopenedMethod'))

    def test_global_scope(self):
        """Forward declaration of an interface at global scope.

        グローバルスコープでの interface 前方宣言。
        """
        self.assertEqual(self.m.forward_interfaces, ['GlobalForward'])
        self.assertEqual(self.m.undefined_forward_interfaces, [])
        user = self.m.interface_by_name('GlobalUser')
        self.assertEqual(user.methods[0].arguments[0].type.name, 'GlobalForward')


class ForwardDeclarationSyntaxTestFunctions(unittest.TestCase):
    """Category: Forward declarations / カテゴリ: 前方宣言

    Interface forward declarations written inline, including errors.
    インラインで書いた interface の前方宣言(エラーを含む)。
    """

    def test_forward_only(self):
        """A forward declaration without a definition.

        前方宣言だけで本定義がない場合。
        """
        m = load('module M { interface A; };')
        M = m.module_by_name('M')
        self.assertEqual(M.interfaces, [])
        self.assertEqual(M.forward_interfaces, ['A'])

    def test_forward_after_definition(self):
        """A forward declaration after the definition keeps the definition.

        本定義の後に前方宣言しても定義が残る。
        """
        m = load('module M { interface A { void f(); }; interface A; };')
        M = m.module_by_name('M')
        self.assertEqual([i.name for i in M.interfaces], ['A'])
        self.assertIsNotNone(M.interface_by_name('A').method_by_name('f'))
        self.assertEqual(M.undefined_forward_interfaces, [])

    def test_scoped_reference_to_forward_interface(self):
        """A forward-declared interface can be referenced as M::A from another module.

        別モジュールから M::A で前方宣言 interface を参照できる。
        """
        m = load('module M { interface A; }; module N { struct S { M::A a; }; }; module M { interface A {}; };')
        s = m.module_by_name('N').struct_by_name('S')
        self.assertEqual(s.members[0].type.full_path, 'M::A')

    def test_inherit_from_forward_only_is_error(self):
        """Inheriting from an interface that is only forward-declared is an error.

        前方宣言しかない interface の継承はエラー。
        """
        # OMG IDL: a base interface must be defined, not just forward-declared
        with self.assertRaises(exception.IDLCanNotFindException):
            load('module M { interface A; interface B : A {}; interface A {}; };')

    def test_inner_forward_declaration_hides_outer_definition(self):
        """An inner forward declaration hides an outer definition of the same name, so inheriting it is an error.

        内側の前方宣言が外側の同名定義を隠すため継承はエラー。
        """
        # "Base" in Q refers to Q::Base (still incomplete), not the global Base
        with self.assertRaises(exception.IDLCanNotFindException):
            load('interface Base {}; module Q { interface Base; interface X : Base {}; };')

    def test_undeclared_type_is_still_an_error(self):
        """An undeclared type still raises InvalidDataTypeException.

        未宣言の型は従来どおり InvalidDataTypeException。
        """
        with self.assertRaises(exception.InvalidDataTypeException):
            load('module M { struct S { Nope a; }; };')

    def test_undeclared_union_member_type_is_parser_error(self):
        """An undeclared union member type also raises InvalidDataTypeException.

        union メンバーの未宣言型も InvalidDataTypeException。
        """
        # Previously raised NameError (exception class not imported in union.py)
        with self.assertRaises(exception.InvalidDataTypeException):
            load('module M { union U switch (long) { case 1: Nope a; }; };')


if __name__ == '__main__':
    unittest.main()
