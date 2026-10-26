"""Struct inheritance: struct B : A (issue #118)."""
import unittest
from idl_parser import parser, exception


IDL = '''
module M {
  struct A { @key long id; };
  struct B : A { double y; };
};
struct C : M::B { string z; };
'''


class StructInheritanceTest(unittest.TestCase):
    """Category: Structs, enums and unions / カテゴリ: struct・enum・union

    A struct with a base struct (issue #118).
    基底 struct を持つ struct(#118)。
    """

    def setUp(self):
        self.m = parser.IDLParser().load(IDL)
        self.a = self.m.find_types('M::A')[0]
        self.b = self.m.find_types('M::B')[0]
        self.c = self.m.find_types('C')[0]

    def test_base(self):
        """base gives the base struct, or None.

        base は基底 struct を返し、なければ None。
        """
        self.assertIsNone(self.a.base)
        self.assertIs(self.b.base, self.a)
        self.assertIs(self.c.base, self.b)

    def test_members(self):
        """members are the struct's own; all_members start with the base's.

        members は自身のメンバー、all_members は基底のメンバーから並ぶ。
        """
        self.assertEqual([m.name for m in self.c.members], ['z'])
        self.assertEqual([m.name for m in self.c.all_members], ['id', 'y', 'z'])
        self.assertEqual(self.c.member_by_name('id').type.name, 'long')

    def test_keys(self):
        """Keys of the base struct are keys of the derived struct.

        基底 struct のキーは派生 struct のキーにもなる。
        """
        self.assertEqual(self.c.keys, ['id'])

    def test_to_dic(self):
        """to_dic() has 'base' only for a struct with a base.

        to_dic() は基底がある struct にだけ 'base' を持つ。
        """
        dic = self.b.to_dic()
        self.assertEqual(dic['base'], 'M::A')
        self.assertEqual([m['name'] for m in dic['members']], ['y'])
        self.assertNotIn('base', self.a.to_dic())

    def test_to_simple_dic(self):
        """to_simple_dic() lists all members.

        to_simple_dic() は全メンバーを並べる。
        """
        self.assertEqual(self.c.to_simple_dic(),
                         {'struct C': [{'id': 'long'}, {'y': 'double'}, {'z': 'string'}]})

    def test_constructor(self):
        """generate_constructor_python() takes the base members first.

        generate_constructor_python() は基底のメンバーから引数にする。
        """
        self.assertEqual(parser.IDLParser().generate_constructor_python(self.c), 'C(0, 0, 0)')

    def test_unknown_base(self):
        """A base that is not defined is an error.

        定義されていない基底はエラー。
        """
        with self.assertRaises(exception.IDLCanNotFindException):
            parser.IDLParser().load('struct B : X { long y; };')

    def test_base_not_struct(self):
        """A base that is not a struct is an error.

        struct でない基底はエラー。
        """
        with self.assertRaises(exception.IDLCanNotFindException):
            parser.IDLParser().load('typedef long T; struct B : T { long y; };')

    def test_no_base_name(self):
        """":" without a base name is a syntax error.

        ":" の後に基底名がないのは構文エラー。
        """
        with self.assertRaises(exception.InvalidIDLSyntaxError):
            parser.IDLParser().load('struct B : { long y; };')


if __name__ == '__main__':
    unittest.main()
