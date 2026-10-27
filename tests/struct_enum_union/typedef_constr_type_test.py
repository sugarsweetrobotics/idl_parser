"""Types declared inside a typedef (issue #121).

IDL 4.2 lets a typedef declare the struct, union, enum, bitmask or bitset it
names (``typedef enum E { A, B } EE;``). This raised
InvalidDataTypeException ("Can not find Data Type (enum E { A , B })").
"""
import unittest
from idl_parser import parser
from idl_parser.exception import InvalidIDLSyntaxError


def load(idl):
    return parser.IDLParser().load(idl)


class TypedefConstrTypeTest(unittest.TestCase):
    """Category: Structs, enums and unions / カテゴリ: struct・enum・union

    A struct, union, enum, bitmask or bitset declared inside a typedef (issue #121).
    typedef の中で宣言した struct・union・enum・bitmask・bitset(#121)。
    """

    def test_enum(self):
        """"typedef enum E { A, B } EE;" defines the enum E and the typedef EE of it.

        "typedef enum E { A, B } EE;" で enum E と、それを指す typedef EE が定義される。
        """
        m = load('module M { typedef enum E { A, B } EE; };').module_by_name('M')
        e = m.enum_by_name('E')
        self.assertEqual(e.full_path, 'M::E')
        self.assertEqual([v.name for v in e.values], ['A', 'B'])
        t = m.typedef_by_name('EE')
        self.assertIs(t.type, e)
        self.assertEqual(t.to_simple_dic(), 'typedef E EE')

    def test_each_kind(self):
        """struct, union, bitmask and bitset are defined too, and the typedef names each of them.

        struct・union・bitmask・bitset も定義され、typedef がそれぞれを指す。
        """
        m = load('''module M {
          typedef struct S { long a; } SS;
          typedef union U switch (long) { case 1: long a; default: double b; } UU;
          typedef bitmask BM { F1, F2 } BB;
          typedef bitset BS { bitfield<3> x; } BSS;
        };''').module_by_name('M')
        for name, by_name, classname in (('SS', m.struct_by_name('S'), 'IDLStruct'),
                                         ('UU', m.union_by_name('U'), 'IDLUnion'),
                                         ('BB', m.bitmask_by_name('BM'), 'IDLBitmask'),
                                         ('BSS', m.bitset_by_name('BS'), 'IDLBitset')):
            with self.subTest(name):
                self.assertIsNotNone(by_name)
                self.assertIs(m.typedef_by_name(name).type, by_name)
                self.assertEqual(by_name.classname, classname)
        self.assertEqual([x.name for x in m.union_by_name('U').members], ['a', 'b'])

    def test_struct_with_base(self):
        """A struct with a base struct ("typedef struct D : B { ... } DD;").

        基底 struct を持つ struct("typedef struct D : B { ... } DD;")。
        """
        m = load('module M { struct B { long b; }; typedef struct D : B { long d; } DD; };').module_by_name('M')
        d = m.struct_by_name('D')
        self.assertEqual(d.base.name, 'B')
        self.assertEqual([x.name for x in d.all_members], ['b', 'd'])
        self.assertIs(m.typedef_by_name('DD').type, d)

    def test_multiple_declarators(self):
        """Several declarators, with array sizes, after the body ("} EE, EA[2];").

        本体の後に複数の宣言子と配列サイズを書ける("} EE, EA[2];")。
        """
        m = load('typedef enum E { A, B } EE, EA[2];')
        self.assertEqual([t.name for t in m.typedefs], ['EE', 'EA'])
        self.assertEqual(m.typedef_by_name('EE').type.name, 'E')
        ea = m.typedef_by_name('EA').type
        self.assertTrue(ea.is_array)
        self.assertEqual(ea.size, 2)
        self.assertIs(ea.inner_type, m.enum_by_name('E'))

    def test_used_by_later_definitions(self):
        """Both the declared type and the typedef can be used by the definitions after them.

        宣言した型と typedef の両方を後の定義で使える。
        """
        m = load('''module M {
          typedef struct Point { double x; double y; } PointT;
          struct Line { Point a; PointT b; };
        };''').module_by_name('M')
        a, b = m.struct_by_name('Line').members
        self.assertIs(a.type, m.struct_by_name('Point'))
        self.assertIs(b.type, m.typedef_by_name('PointT'))
        self.assertIs(b.type.type, m.struct_by_name('Point'))

    def test_forward_declared_struct(self):
        """"typedef struct F FF;" forward-declares F; FF names F once it is defined.

        "typedef struct F FF;" は F の前方宣言になり、F の定義後に FF が F を指す。
        """
        m = load('typedef struct F FF; struct F { long a; };')
        self.assertEqual(m.forward_structs, ['F'])
        self.assertIs(m.typedef_by_name('FF').type, m.struct_by_name('F'))

    def test_in_interface(self):
        """A typedef with a type declaration inside an interface.

        interface の中の、型宣言を含む typedef。
        """
        i = load('interface I { typedef enum Mode { ON, OFF } ModeT; void set(in ModeT m); };').interface_by_name('I')
        self.assertEqual(i.enum_by_name('Mode').full_path, '::I::Mode')
        self.assertIs(i.typedef_by_name('ModeT').type, i.enum_by_name('Mode'))

    def test_annotations_apply_to_typedef(self):
        """Annotations before "typedef" apply to the typedef.

        "typedef" の前のアノテーションは typedef に付く。
        """
        m = load('@final typedef struct S { long a; } SS;')
        self.assertEqual([a.name for a in m.typedef_by_name('SS').annotations], ['final'])

    def test_definitions_after_it_keep_their_scope(self):
        """The "}" of the declared type does not end the enclosing module.

        宣言した型の "}" で外側の module が閉じない。
        """
        g = load('module M { typedef enum E { A } EE; struct S { EE e; }; }; struct T { long t; };')
        self.assertEqual([s.full_path for s in g.module_by_name('M').structs], ['M::S'])
        self.assertEqual([s.full_path for s in g.structs], ['::T'])

    def test_invalid(self):
        """Invalid declarations inside a typedef raise InvalidIDLSyntaxError.

        typedef の中の不正な宣言で InvalidIDLSyntaxError。
        """
        for idl in ('typedef enum E EE;',                 # an enum needs its body
                    'typedef struct { long a; } S;',      # no name (C style)
                    'typedef struct S { long a; ',        # no "}"
                    'typedef enum E { A };',              # no typedef name
                    'typedef union U switch (long) EE;'): # no body
            with self.subTest(idl):
                with self.assertRaises(InvalidIDLSyntaxError):
                    load(idl)


if __name__ == '__main__':
    unittest.main()
