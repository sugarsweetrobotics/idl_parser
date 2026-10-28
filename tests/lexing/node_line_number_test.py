"""Tests for issue #141: definition nodes have line numbers.

Nodes had a filepath but no line number, so the position of a definition
in the IDL (for #pragma prefix, or for messages of a generator) could not be
known. Every definition node now has ``line_number``: the line of its name,
or, for a member, an operation, an attribute and the like, the line where
its declaration starts.
"""
import os
import shutil
import tempfile
import unittest

from idl_parser import parser


IDL = '''module M {
  struct S {
    long a;
    long
      b;
  };
  typedef long T;
  const long C = 1;
  enum E {
    X,
    Y };
  interface I {
    void f(
      in long x);
    attribute long at;
    struct Inner { long i; };
  };
  union U switch (long) {
    case 1:
      long u;
    default: short d;
  };
  valuetype V { public
     long v; factory
     mk(); };
  native N;
  exception Err { long code; };
  bitmask BM { b0,
    b1 };
  bitset BS {
    bitfield<3> f; };
  typedef struct TS {
    long t; } TT;
};
module M { struct Again { long r; }; };
'''


class NodeLineNumberTest(unittest.TestCase):
    """Category: Lexing and preprocessing / カテゴリ: 字句解析・前処理

    Definition nodes have line numbers (issue #141).
    定義ノードが行番号を持つ(#141)。
    """

    @classmethod
    def setUpClass(cls):
        cls.g = parser.IDLParser().load(IDL)
        cls.m = cls.g.module_by_name('M')

    def test_definitions(self):
        """Definitions have the line of their name. / 定義は名前の行を持つ。"""
        m = self.m
        self.assertEqual(m.line_number, 1)
        self.assertEqual(m.struct_by_name('S').line_number, 2)
        self.assertEqual(m.typedef_by_name('T').line_number, 7)
        self.assertEqual(m.const_by_name('C').line_number, 8)
        self.assertEqual(m.enum_by_name('E').line_number, 9)
        self.assertEqual(m.interface_by_name('I').line_number, 12)
        self.assertEqual(m.union_by_name('U').line_number, 18)
        self.assertEqual(m.valuetype_by_name('V').line_number, 23)
        self.assertEqual(m.native_by_name('N').line_number, 26)
        self.assertEqual(m.exception_by_name('Err').line_number, 27)
        self.assertEqual(m.bitmask_by_name('BM').line_number, 28)
        self.assertEqual(m.bitset_by_name('BS').line_number, 30)
        self.assertEqual(m.struct_by_name('TS').line_number, 32)
        self.assertEqual(m.typedef_by_name('TT').line_number, 33)

    def test_members(self):
        """Members and enumerators have the line where they start. / メンバーと列挙子は宣言の始まりの行を持つ。"""
        s = self.m.struct_by_name('S')
        self.assertEqual([x.line_number for x in s.members], [3, 4])
        self.assertEqual([v.line_number for v in self.m.enum_by_name('E').values], [10, 11])
        u = self.m.union_by_name('U')
        self.assertEqual([x.line_number for x in u.members], [19, 21])
        self.assertEqual([v.line_number for v in self.m.bitmask_by_name('BM').values], [28, 29])

    def test_interface_body(self):
        """Operations, arguments, attributes and nested definitions. / operation・引数・attribute・入れ子の定義。"""
        i = self.m.interface_by_name('I')
        self.assertEqual(i.methods[0].line_number, 13)
        self.assertEqual(i.methods[0].arguments[0].line_number, 13)
        self.assertEqual(i.attributes[0].line_number, 15)
        self.assertEqual(i.struct_by_name('Inner').line_number, 16)

    def test_valuetype_body(self):
        """State members and factories. / state member と factory。"""
        v = self.m.valuetype_by_name('V')
        self.assertEqual(v.state_members[0].line_number, 23)
        self.assertEqual(v.factories[0].line_number, 24)

    def test_reopened_module(self):
        """A reopened module keeps the line where it is first opened. / 再オープンしたモジュールは最初に開いた行を持つ。"""
        self.assertEqual(self.m.struct_by_name('Again').line_number, 35)
        self.assertEqual(self.m.line_number, 1)

    def test_no_line_number(self):
        """The global scope and type nodes have None. / グローバルスコープと型ノードは None。"""
        self.assertIsNone(self.g.line_number)
        self.assertIsNone(self.m.struct_by_name('S').members[0].type.line_number)

    def test_included_file(self):
        """Nodes of an included file have its line numbers and file. / include 先のノードはそのファイルの行番号とファイルを持つ。"""
        d = tempfile.mkdtemp()
        try:
            with open(os.path.join(d, 'base.idl'), 'w') as f:
                f.write('\n\nstruct B { long b; };\n')
            main = os.path.join(d, 'main.idl')
            with open(main, 'w') as f:
                f.write('#include "base.idl"\nstruct A {\n  B b;\n};\n')
            p = parser.IDLParser()
            p.parse_idl(main)
            b = p.global_module.struct_by_name('B')
            a = p.global_module.struct_by_name('A')
            self.assertEqual((os.path.basename(b.filepath), b.line_number), ('base.idl', 3))
            self.assertEqual((os.path.basename(a.filepath), a.line_number), ('main.idl', 2))
            self.assertEqual(a.members[0].line_number, 3)
        finally:
            shutil.rmtree(d)

    def test_line_numbers_do_not_leak(self):
        """Nodes made after parsing have no line number. / 解析の後に作ったノードは行番号を持たない。"""
        from idl_parser import module
        self.assertIsNone(module.IDLModule('Z', self.g).line_number)


if __name__ == '__main__':
    unittest.main()
