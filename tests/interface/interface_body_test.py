"""Tests for issue #101: attributes and definitions inside an interface.

The body of an interface was read as operations only, so an attribute
("attribute long x;") became an operation returning "attribute", and a
struct, enum or exception defined in the interface broke the parsing of the
rest of the interface. Attributes are now IDLAttribute objects
(IDLInterface.attributes), and types and constants defined in an interface
are parsed as in a module and scoped by the interface ("M::I::S").
"""
import unittest
import warnings
from idl_parser import parser
from idl_parser.exception import IDLParserWarning, InvalidIDLSyntaxError


IDL = '''
module M {
  interface I {
    const long N = 3;
    struct S { long a; };
    typedef S SArr[N];
    enum E { A, B };
    exception X { string why; };
    union U switch (long) { case 1: long a; };
    native H;
    struct T { S s; E e; };
    attribute long x;
    readonly attribute string name, label;
    readonly attribute T t raises (X);
    attribute SArr arr getraises (X) setraises (X);
    attribute sequence<long, 10> values;
    T get(in S s, in E e) raises (X);
    @final struct Annotated { long b; };
    void f();
  };
  struct Outer { I::S s; I::E e; };
};
'''


def load(idl):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        g = parser.IDLParser().load(idl)
    return g, [w for w in caught if issubclass(w.category, IDLParserWarning)]


class InterfaceBodyTest(unittest.TestCase):
    """Category: Interfaces, operations and inheritance / カテゴリ: interface・operation・継承

    Attributes and definitions inside an interface (issue #101).
    interface の中の attribute と型定義(#101)。
    """

    @classmethod
    def setUpClass(cls):
        cls.g, cls.warnings = load(IDL)
        cls.m = cls.g.module_by_name('M')
        cls.i = cls.m.interface_by_name('I')

    def test_no_warnings(self):
        """The interface is parsed without warnings. / 警告なしで解析される。"""
        self.assertEqual(self.warnings, [])

    def test_operations(self):
        """Only the operations are methods. / operation だけが methods に入る。"""
        self.assertEqual([m.name for m in self.i.methods], ['get', 'f'])

    def test_attributes(self):
        """Attributes are IDLAttribute objects, one per name. / attribute は名前ごとに IDLAttribute になる。"""
        self.assertEqual([a.name for a in self.i.attributes],
                         ['x', 'name', 'label', 't', 'arr', 'values'])
        x = self.i.attribute_by_name('x')
        self.assertEqual(x.classname, 'IDLAttribute')
        self.assertEqual(str(x.type), 'long')
        self.assertFalse(x.readonly)
        self.assertEqual(x.full_path, 'M::I::x')
        label = self.i.attribute_by_name('label')
        self.assertTrue(label.readonly)
        self.assertEqual(str(label.type), 'string')
        self.assertIsNone(self.i.attribute_by_name('f'))

    def test_attribute_type(self):
        """The type of an attribute is resolved from the interface scope. / attribute の型は interface のスコープから解決される。"""
        self.assertEqual(self.i.attribute_by_name('t').type.obj.full_path, 'M::I::T')
        arr = self.i.attribute_by_name('arr').type.obj
        self.assertEqual(arr.full_path, 'M::I::SArr')
        self.assertEqual(arr.type.size, 3)
        self.assertTrue(self.i.attribute_by_name('values').type.is_sequence)

    def test_attribute_raises(self):
        """raises / getraises / setraises are kept. / raises・getraises・setraises を保持する。"""
        t = self.i.attribute_by_name('t')
        self.assertEqual(t.getraises, ['X'])
        self.assertEqual(t.setraises, [])
        arr = self.i.attribute_by_name('arr')
        self.assertEqual(arr.getraises, ['X'])
        self.assertEqual(arr.setraises, ['X'])

    def test_definitions(self):
        """Types and constants are defined in the interface. / 型と定数が interface に定義される。"""
        self.assertEqual([s.name for s in self.i.structs], ['S', 'T', 'Annotated'])
        self.assertEqual([t.name for t in self.i.typedefs], ['SArr'])
        self.assertEqual([e.name for e in self.i.enums], ['E'])
        self.assertEqual([x.name for x in self.i.exceptions], ['X'])
        self.assertEqual([u.name for u in self.i.unions], ['U'])
        self.assertEqual([n.name for n in self.i.natives], ['H'])
        self.assertEqual([c.name for c in self.i.consts], ['N'])
        self.assertEqual(self.m.structs[0].name, 'Outer')
        self.assertEqual(len(self.m.structs), 1)

    def test_annotation_on_definition(self):
        """Annotations before a definition apply to it. / 定義の前の注釈はその定義に付く。"""
        self.assertEqual([a.name for a in self.i.struct_by_name('Annotated').annotations], ['final'])

    def test_scoped_names(self):
        """Definitions are scoped by the interface. / 定義は interface のスコープに入る。"""
        self.assertEqual(self.i.struct_by_name('S').full_path, 'M::I::S')
        self.assertEqual(self.i.exception_by_name('X').full_path, 'M::I::X')
        # Enumerators belong to the scope enclosing the enum
        self.assertEqual(self.i.enum_by_name('E').values[0].full_path, 'M::I::A')

    def test_resolution_inside_interface(self):
        """Names used inside the interface find its definitions. / interface 内の名前はその定義を見つける。"""
        t = self.i.struct_by_name('T')
        self.assertEqual([m.type.obj.full_path for m in t.members], ['M::I::S', 'M::I::E'])
        get = self.i.method_by_name('get')
        self.assertEqual(get.returns.obj.full_path, 'M::I::T')
        self.assertEqual(get.exceptions[0].full_path, 'M::I::X')

    def test_resolution_outside_interface(self):
        """"I::S" outside the interface finds the definition. / interface の外から "I::S" で参照できる。"""
        outer = self.m.struct_by_name('Outer')
        self.assertEqual([m.type.obj.full_path for m in outer.members], ['M::I::S', 'M::I::E'])
        self.assertEqual([t.full_path for t in self.g.find_types('M::I::S')], ['M::I::S'])

    def test_constructor_python(self):
        """generate_constructor_python() uses the interface scope. / interface のスコープを使う。"""
        p = parser.IDLParser()
        self.assertEqual(p.generate_constructor_python(self.m.struct_by_name('Outer')),
                         'M.Outer(M.I.S(0), M.I.A)')

    def test_to_simple_dic(self):
        """to_simple_dic() lists attributes and definitions after the operations. / operation の後に並ぶ。"""
        g, _ = load('interface I { attribute long x; struct S { long a; }; void f(); };')
        self.assertEqual(g.interface_by_name('I').to_simple_dic(),
                         {'interface I': [{'inherits': []},
                                          {'f': {'returns': 'void', 'params': []}},
                                          {'attribute x': 'long'},
                                          {'struct S': [{'a': 'long'}]}]})

    def test_to_dic(self):
        """to_dic() has "attributes" and the definitions only when there are any. / ある場合だけ入る。"""
        dic = self.i.to_dic()
        self.assertEqual([a['name'] for a in dic['attributes']],
                         ['x', 'name', 'label', 't', 'arr', 'values'])
        self.assertEqual([s['name'] for s in dic['structs']], ['S', 'T', 'Annotated'])
        g, _ = load('interface I { void f(); };')
        dic = g.interface_by_name('I').to_dic()
        self.assertNotIn('attributes', dic)
        self.assertNotIn('structs', dic)

    def test_issue_examples(self):
        """The examples in issue #101 are parsed. / #101 の例が正しく解析される。"""
        for body in ['attribute long x;', 'typedef long T;', 'const long C = 1;',
                     'struct S { long a; };', 'enum E { A, B };',
                     'exception X { long a; };']:
            with self.subTest(body=body):
                g, w = load('interface I { %s void f(); };' % body)
                i = g.interface_by_name('I')
                self.assertEqual(w, [])
                self.assertEqual([m.name for m in i.methods], ['f'])

    def test_invalid_attributes(self):
        """Invalid attribute declarations are errors. / 不正な attribute 宣言はエラーになる。"""
        for body in ['attribute long;',
                     'readonly long x;',
                     'readonly attribute long x getraises (E);',
                     'attribute long x raises (E);',
                     'attribute long a, b setraises (E);']:
            with self.subTest(body=body):
                with self.assertRaises(InvalidIDLSyntaxError):
                    parser.IDLParser().load(
                        'exception E { long a; }; interface I { %s };' % body)


if __name__ == '__main__':
    unittest.main()
