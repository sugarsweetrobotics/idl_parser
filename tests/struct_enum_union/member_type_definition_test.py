"""Regression tests for issue #144.

A struct, union or enum defined in a struct member or a union case
("struct Outer { struct Inner { long v; } inner; };") was an
InvalidIDLSyntaxError ('No semi-colon after "}"'). It is read now, and the
type is defined in the scope of the enclosing struct or union.
"""
import unittest
from idl_parser import parser
from idl_parser.exception import InvalidIDLSyntaxError


IDL = '''
module M {
  struct Outer {
    struct Inner { long v; } inner;
    @key enum Color { RED, GREEN } color;
    union Choice switch (boolean) { case TRUE: long a; } choice;
    Inner again;
    sequence<Inner> many;
  };
  union U switch (long) {
    case 1: struct In { long q; } inn;
    case 2:
    case 3: union V switch (short) { case 1: long x; } v;
    default: enum K { A, B } k;
  };
  exception E { struct Detail { string text; } detail; };
  struct Use { Outer::Inner i; Outer::Color c; U::In j; U::K k; };
};
'''


class MemberTypeDefinitionTest(unittest.TestCase):
    """Category: Structs, enums and unions / カテゴリ: struct・enum・union

    Types defined in struct members and union cases (issue #144).
    struct のメンバーと union の case の中での型定義(#144)。
    """

    @classmethod
    def setUpClass(cls):
        cls.g = parser.IDLParser().load(IDL)
        cls.m = cls.g.module_by_name('M')

    def test_struct_member(self):
        """Types defined in struct members are scoped by the struct.

        struct のメンバーで定義した型は、その struct のスコープに入る。
        """
        o = self.m.struct_by_name('Outer')
        self.assertEqual([s.full_path for s in o.structs], ['M::Outer::Inner'])
        self.assertEqual([e.full_path for e in o.enums], ['M::Outer::Color'])
        self.assertEqual([u.full_path for u in o.unions], ['M::Outer::Choice'])
        self.assertEqual([m.name for m in o.members], ['inner', 'color', 'choice', 'again', 'many'])
        self.assertEqual([m.type.obj.full_path for m in o.members[:4]],
                         ['M::Outer::Inner', 'M::Outer::Color', 'M::Outer::Choice', 'M::Outer::Inner'])
        self.assertEqual(o.members[4].type.inner_type.full_path, 'M::Outer::Inner')

    def test_annotation_of_the_member(self):
        """An annotation before the type definition belongs to the member.

        型定義の前のアノテーションはメンバーに付く。
        """
        color = self.m.struct_by_name('Outer').member_by_name('color')
        self.assertTrue(color.is_key)

    def test_union_case(self):
        """Types defined in union cases are scoped by the union, also after several labels.

        union の case で定義した型は、その union のスコープに入る(ラベルが複数でもよい)。
        """
        u = self.m.union_by_name('U')
        self.assertEqual([s.full_path for s in u.structs], ['M::U::In'])
        self.assertEqual([s.full_path for s in u.unions], ['M::U::V'])
        self.assertEqual([s.full_path for s in u.enums], ['M::U::K'])
        self.assertEqual([(m.name, m.type.obj.full_path) for m in u.members],
                         [('inn', 'M::U::In'), ('v', 'M::U::V'), ('k', 'M::U::K')])
        self.assertTrue(u.member_by_name('k').is_default)

    def test_exception_member(self):
        """An exception member can define a type too.

        exception のメンバーでも型を定義できる。
        """
        e = self.m.exception_by_name('E')
        self.assertEqual(e.member_by_name('detail').type.obj.full_path, 'M::E::Detail')

    def test_scoped_reference(self):
        """The types are found by scoped names from outside.

        外からスコープ付きの名前で参照できる。
        """
        use = self.m.struct_by_name('Use')
        self.assertEqual([m.type.obj.full_path for m in use.members],
                         ['M::Outer::Inner', 'M::Outer::Color', 'M::U::In', 'M::U::K'])
        self.assertEqual([t.full_path for t in self.g.find_types('M::Outer::Inner')],
                         ['M::Outer::Inner'])

    def test_not_in_the_module(self):
        """The types are not added to the enclosing module.

        型は囲んでいるモジュールには追加されない。
        """
        self.assertEqual([s.name for s in self.m.structs], ['Outer', 'Use'])
        self.assertEqual(self.m.enums, [])

    def test_nested(self):
        """A type defined in a member of a type defined in a member.

        メンバーで定義した型の、さらにメンバーで定義した型。
        """
        g = parser.IDLParser().load(
            'struct A { struct B { struct C { long c; } c; } b; };\n'
            'struct D { A::B::C c; };')
        self.assertEqual(g.struct_by_name('D').members[0].type.obj.full_path, '::A::B::C')

    def test_in_an_interface(self):
        """A struct in an interface whose member defines a type.

        interface 内の struct のメンバーで型を定義する。
        """
        g = parser.IDLParser().load(
            'interface I { struct S { struct T { long t; } t; }; void f(in S::T x); };')
        f = g.interface_by_name('I').method_by_name('f')
        self.assertEqual(f.arguments[0].type.obj.full_path, '::I::S::T')

    def test_to_dic(self):
        """to_dic() of the struct has the types defined in it.

        struct の to_dic() に、その中で定義した型が入る。
        """
        dic = self.m.struct_by_name('Outer').to_dic()
        self.assertEqual([s['name'] for s in dic['structs']], ['Inner'])
        self.assertEqual([e['name'] for e in dic['enums']], ['Color'])
        self.assertNotIn('structs', self.m.struct_by_name('Use').to_dic())

    def test_errors(self):
        """A definition without its "}" or without a member name is still an error.

        "}" やメンバー名がない定義は今までどおりエラーになる。
        """
        for idl in ['struct S { struct T { long a; t; };',
                    'struct S { struct T { long a; } ; };',
                    'union U switch (long) { case 1: struct T { long a; } };']:
            with self.subTest(idl):
                with self.assertRaises(InvalidIDLSyntaxError):
                    parser.IDLParser().load(idl)


if __name__ == '__main__':
    unittest.main()
