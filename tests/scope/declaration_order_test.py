"""Tests for issue #134: definitions keep the order they are written in.

A module or an interface kept its definitions in one list per kind
(structs, enums, typedefs, consts, interfaces, ...), so the order across
kinds could not be known. A generator that writes the definitions before
their use (C++ headers, Python modules) needs it. IDLModule, IDLInterface
and IDLValueType now have ``definitions``: every definition in the order it
is written, nested modules and forward declarations included.
"""
import unittest
from idl_parser import parser
from idl_parser.exception import InvalidIDLSyntaxError


IDL = '''
const long A = 1;
struct S { long a; };
typedef S T;
enum E { X };
struct S2 { E e; T t; };
interface I;
struct F;
union FU;
module M { const long B = 2; };
typedef struct G { long g; } GG, GH;
native N;
exception Ex { long code; };
bitmask BM { b0 };
bitset BS { bitfield<3> f; };
interface I {
  void f();
  attribute long x, y;
  struct In { long a; };
  const long K = 1;
  long g();
};
module M { const long C = 3; struct MS { long m; }; };
struct F { long f; };
union FU switch (long) { case 1: long a; };
valuetype V { public long a; factory create(in long a); void op(); typedef long VL; };
valuetype VF;
eventtype EV { public long e; };
'''


def names(nodes):
    return [(n.classname, n.name) for n in nodes]


class DeclarationOrderTest(unittest.TestCase):
    """Category: Scopes and modules / カテゴリ: スコープ・モジュール

    Definitions keep the order they are written in (issue #134).
    定義の宣言順を保持する(#134)。
    """

    @classmethod
    def setUpClass(cls):
        cls.g = parser.IDLParser().load(IDL)

    def test_global_scope(self):
        """The global scope lists every kind in the written order. / グローバルスコープは種類をまたいで書いた順に並ぶ。"""
        self.assertEqual(names(self.g.definitions), [
            ('IDLConst', 'A'), ('IDLStruct', 'S'), ('IDLTypedef', 'T'),
            ('IDLEnum', 'E'), ('IDLStruct', 'S2'),
            ('IDLInterface', 'I'), ('IDLStruct', 'F'), ('IDLUnion', 'FU'),
            ('IDLModule', 'M'),
            ('IDLStruct', 'G'), ('IDLTypedef', 'GG'), ('IDLTypedef', 'GH'),
            ('IDLNative', 'N'), ('IDLException', 'Ex'), ('IDLBitmask', 'BM'),
            ('IDLBitset', 'BS'), ('IDLInterface', 'I'),
            ('IDLStruct', 'F'), ('IDLUnion', 'FU'),
            ('IDLValueType', 'V'), ('IDLValueType', 'VF'), ('IDLEventType', 'EV')])

    def test_same_nodes_as_lists_by_kind(self):
        """The entries are the nodes of the lists by kind. / 種類別のリストと同じノードが入る。"""
        defs = self.g.definitions
        self.assertIs(defs[1], self.g.struct_by_name('S'))
        self.assertIs(defs[16], self.g.interface_by_name('I'))
        self.assertIs(defs[8], self.g.module_by_name('M'))

    def test_forward_declarations(self):
        """Forward declarations are listed as forward nodes. / 前方宣言は is_forward のノードとして入る。"""
        defs = self.g.definitions
        self.assertTrue(defs[5].is_forward)    # interface I;
        self.assertTrue(defs[6].is_forward)    # struct F;
        self.assertTrue(defs[7].is_forward)    # union FU;
        self.assertFalse(defs[16].is_forward)  # interface I { ... };
        self.assertFalse(defs[17].is_forward)  # struct F { ... };
        self.assertTrue(defs[20].is_forward)   # valuetype VF;
        self.assertNotIn(defs[6], self.g.structs)

    def test_reopened_module(self):
        """A reopened module is listed once, and its definitions are joined in order. / 再オープンしたモジュールは一度だけ並び、定義は出現順に連結される。"""
        self.assertEqual([n.name for n in self.g.definitions].count('M'), 1)
        self.assertEqual(names(self.g.module_by_name('M').definitions),
                         [('IDLConst', 'B'), ('IDLConst', 'C'), ('IDLStruct', 'MS')])

    def test_interface(self):
        """An interface lists operations, attributes and definitions in order. / interface は operation・attribute・定義を順に並べる。"""
        i = self.g.interface_by_name('I')
        self.assertEqual(names(i.definitions), [
            ('IDLValue', 'f'), ('IDLAttribute', 'x'), ('IDLAttribute', 'y'),
            ('IDLStruct', 'In'), ('IDLConst', 'K'), ('IDLValue', 'g')])

    def test_valuetype(self):
        """A value type lists state members, factories, operations and definitions in order. / valuetype は state member・factory・operation・定義を順に並べる。"""
        v = self.g.valuetype_by_name('V')
        self.assertEqual([n.name for n in v.definitions], ['a', 'create', 'op', 'VL'])
        self.assertEqual([n.name for n in self.g.eventtype_by_name('EV').definitions], ['e'])

    def test_duplicate_is_an_error(self):
        """A repeated definition is an error since issue #143. / 重複した定義は #143 からエラーになる。"""
        with self.assertRaises(InvalidIDLSyntaxError):
            parser.IDLParser().load('typedef long L; typedef long L; const long C = 1;')

    def test_returns_copy(self):
        """Changing the returned list does not change the node. / 返したリストを変えてもノードは変わらない。"""
        self.g.definitions.clear()
        self.assertEqual(len(self.g.definitions), 22)


if __name__ == '__main__':
    unittest.main()
