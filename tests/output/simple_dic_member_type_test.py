"""to_simple_dic() with struct / enum / typedef / bitmask / bitset members (issues #30, #43).

A member's ``type`` resolves to the definition node (IDLStruct, IDLEnum, ...),
which used to have neither ``obj`` nor a type-name ``__str__``.
"""
import unittest

from idl_parser import parser

IDL = '''
module M {
  struct T { long s; };
  enum E { A, B };
  bitmask F { F1, F2 };
  bitset BS { bitfield<3> b; };
  typedef sequence<double> DSeq;
  typedef T TAlias;
  struct P { long x; };
  struct WithStruct { T t; };
  struct WithEnum { E e; };
  struct WithBitmask { F f; };
  struct WithBitset { BS bs; };
  struct WithSeqTypedef { DSeq d; };
  struct WithStructTypedef { TAlias a; };
  struct WithSeqInline { sequence<long> q; };
  struct WithSeqOfStruct { sequence<T> ts; };
  struct WithArray { long a[3]; };
  union U switch (E) { case A: T t; case B: long l; };
};
'''


class MemberTypeSimpleDicTest(unittest.TestCase):
    """Category: Dictionary output and code generation / カテゴリ: 辞書出力・コード生成

    Member type names in to_simple_dic() / to_dic() (issues #30, #43).
    to_simple_dic()/to_dic() のメンバー型名(#30, #43)。
    """

    def setUp(self):
        self.m = parser.IDLParser().load(IDL).module_by_name('M')

    def test_type_name_not_object_repr(self):
        """to_simple_dic(): struct / enum / bitmask / bitset / typedef members show type names, not object reprs.

        to_simple_dic(): struct/enum/bitmask/bitset/typedef 型メンバーがオブジェクト表現でなく型名で出る。
        """
        cases = {
            'WithStruct': {'t': 'T'},
            'WithEnum': {'e': 'E'},
            'WithBitmask': {'f': 'F'},
            'WithBitset': {'bs': 'BS'},
            'WithSeqTypedef': {'d': 'DSeq'},
            'WithStructTypedef': {'a': 'TAlias'},
            'WithSeqOfStruct': {'ts': 'sequence<T>'},
        }
        for name, member in cases.items():
            with self.subTest(struct=name):
                self.assertEqual(self.m.struct_by_name(name).to_simple_dic(),
                                 {'struct %s' % name: [member]})

    def test_union_type_name(self):
        """to_simple_dic(): union members also show type names.

        to_simple_dic(): union メンバーも型名で出る。
        """
        self.assertEqual(self.m.union_by_name('U').to_simple_dic(),
                         {'union U': [{'t': 'T'}, {'l': 'long'}]})

    def test_to_dic_type_name(self):
        """to_dic(): type of a struct-typed member is the type name.

        to_dic(): struct 型メンバーの type が型名。
        """
        member = self.m.struct_by_name('WithStruct').to_dic()['members'][0]
        self.assertEqual(member['type'], 'T')

    def test_typedef_of_struct(self):
        """to_simple_dic(): a typedef of a struct.

        to_simple_dic(): struct の typedef。
        """
        self.assertEqual(self.m.typedef_by_name('TAlias').to_simple_dic(),
                         'typedef T TAlias')

    def test_recursive(self):
        """to_simple_dic(recursive=True) expands each kind of member type.

        to_simple_dic(recursive=True) で各種メンバー型が展開される。
        """
        cases = {
            'P': ['long x'],
            'WithSeqInline': [{'sequence<long> q': {'sequence<long>': 'long'}}],
            'WithArray': [{'long[3] a': 'long[3]'}],
            'WithStruct': [{'T t': ['long s']}],
            'WithEnum': [{'E e': [{'A': 0}, {'B': 1}]}],
            'WithBitmask': [{'F f': [{'F1': 0}, {'F2': 1}]}],
            'WithBitset': [{'BS bs': [{'b': 'bitfield<3, octet>'}]}],
            'WithSeqTypedef': [{'DSeq d': {'typedef sequence<double> DSeq':
                                           {'sequence<double>': 'double'}}}],
            'WithStructTypedef': [{'TAlias a': {'typedef T TAlias': ['long s']}}],
            'WithSeqOfStruct': [{'sequence<T> ts': {'sequence<T>': ['long s']}}],
        }
        for name, members in cases.items():
            with self.subTest(struct=name):
                self.assertEqual(self.m.struct_by_name(name).to_simple_dic(recursive=True),
                                 {'struct %s' % name: members})

    def test_union_recursive(self):
        """to_simple_dic(recursive=True) of a union.

        union の to_simple_dic(recursive=True)。
        """
        self.assertEqual(self.m.union_by_name('U').to_simple_dic(recursive=True),
                         {'union U': [{'T t': ['long s']}, 'long l']})


if __name__ == '__main__':
    unittest.main()
