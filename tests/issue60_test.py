"""to_simple_dic(recursive=True) expands enum members like other types (issue #60).

A direct enum member used to become ``'enum <member name>'`` (no type name,
no values), while ``sequence<E>`` / typedef of an enum expanded the values.
Enum members now expand the same way as struct and bitmask members.
"""
import unittest

from idl_parser import parser

IDL = '''
module M {
  enum E { A, B };
  bitmask F { F1, F2 };
  typedef E EAlias;
  typedef sequence<E> ESeq;
  struct S { E e; sequence<E> se; EAlias ea; ESeq es; F f; };
  union U switch (E) { case A: E ue; case B: long l; };
};
'''

VALUES = [{'A': 0}, {'B': 1}]


class EnumMemberSimpleDicTest(unittest.TestCase):

    def setUp(self):
        self.m = parser.IDLParser().load(IDL).module_by_name('M')

    def _members(self):
        return self.m.struct_by_name('S').to_simple_dic(recursive=True)['struct S']

    def test_direct_member(self):
        self.assertEqual(self._members()[0], {'E e': VALUES})

    def test_sequence_of_enum(self):
        self.assertEqual(self._members()[1], {'sequence<E> se': {'sequence<E>': VALUES}})

    def test_typedef_of_enum(self):
        self.assertEqual(self._members()[2], {'EAlias ea': {'typedef E EAlias': VALUES}})

    def test_typedef_of_sequence_of_enum(self):
        self.assertEqual(self._members()[3],
                         {'ESeq es': {'typedef sequence<E> ESeq': {'sequence<E>': VALUES}}})

    def test_same_shape_as_bitmask(self):
        self.assertEqual(self._members()[4], {'F f': [{'F1': 0}, {'F2': 1}]})

    def test_union_member(self):
        self.assertEqual(self.m.union_by_name('U').to_simple_dic(recursive=True),
                         {'union U': [{'E ue': VALUES}, 'long l']})

    def test_enum_itself_unchanged(self):
        e = self.m.enum_by_name('E')
        self.assertEqual(e.to_simple_dic(), {'enum E': VALUES})
        self.assertEqual(e.to_simple_dic(member_only=True), VALUES)
        self.assertEqual(e.to_simple_dic(quiet=True), 'enum E')

    def test_non_recursive_unchanged(self):
        self.assertEqual(self.m.struct_by_name('S').to_simple_dic()['struct S'][0], {'e': 'E'})


if __name__ == '__main__':
    unittest.main()
