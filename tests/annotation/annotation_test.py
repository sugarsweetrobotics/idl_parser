"""IDL 4 annotations (issue #39).

Annotations are kept on the definition, member, value or argument they are
written before, and no longer leak into type names.
"""
import unittest
from idl_parser import parser, node
from idl_parser.exception import InvalidIDLSyntaxError


def load(idl):
    return parser.IDLParser().load(idl)


IDL = '''
@topic module M {
  struct A { long y; };

  @extensibility(FINAL) @nested(FALSE)
  struct S {
    @key long id;
    @key A a;
    @range(min=0, max=10) @default(5) long v;
    @optional sequence<long> o;
    @unit("m/s") double speed;
    long plain;
  };

  @extensibility(APPENDABLE)
  union U switch (long) {
    case 1: @key long a;
    case 2: @external A b;
  };

  enum E { @value(1) ONE, @value(2) TWO, @foo(1, 2) THREE };

  @verbatim(language="c++", text="x") const long C = 3;
  @range(min=0, max=9) typedef long Small;

  @service(platform="DDS")
  interface I {
    @oneway_hint void f(@range(min=0, max=9) in long x, in A y);
    long g();
  };
};
'''


class AnnotationParseTest(unittest.TestCase):
    """Category: Annotations / カテゴリ: アノテーション

    parse_annotations(): splitting annotation tokens and their arguments.
    parse_annotations() によるアノテーションと引数の分解。
    """

    def test_arguments(self):
        """parse_annotations() splits annotations with no, named, positional and nested-parenthesis arguments and returns the remaining tokens.

        parse_annotations() が引数なし・名前付き引数・位置引数・入れ子括弧のアノテーションを分解し、残りのトークンを返す。
        """
        anns, rest = node.parse_annotations(
            '@key @range ( min = 0 , max = 9 ) @bit_bound ( 8 ) @foo ( 1 , ( 2 ) ) long x'.split())
        self.assertEqual(rest, ['long', 'x'])
        self.assertEqual([a.name for a in anns], ['key', 'range', 'bit_bound', 'foo'])
        key, rng, bb, foo = anns
        self.assertEqual((key.args, key.params, key.value), ([], {}, None))
        self.assertEqual(rng.params, {'min': '0', 'max': '9'})
        self.assertIsNone(rng.value)
        self.assertEqual(bb.value, '8')
        self.assertEqual(foo.args, ['1', '( 2 )'])
        self.assertEqual(str(rng), '@range(min=0, max=9)')
        self.assertEqual(str(key), '@key')

    def test_named_value_param(self):
        """An argument written as value= (e.g. @bit_bound(value = 8)) is available as .value.

        @bit_bound(value = 8) のように value= で書いた引数が .value で取れる。
        """
        anns, _ = node.parse_annotations('@bit_bound ( value = 8 )'.split())
        self.assertEqual(anns[0].value, '8')

    def test_unclosed(self):
        """An annotation with an unclosed parenthesis raises InvalidIDLSyntaxError.

        括弧が閉じていないアノテーションで InvalidIDLSyntaxError。
        """
        with self.assertRaises(InvalidIDLSyntaxError):
            node.parse_annotations('@range ( min = 0 long x'.split())


class AnnotationTest(unittest.TestCase):
    """Category: Annotations / カテゴリ: アノテーション

    Annotations kept on definitions, members, enum values, methods and arguments (issue #39).
    定義・メンバー・enum 値・メソッド・引数に付いたアノテーションの保持(#39)。
    """

    def setUp(self):
        self.g = load(IDL)
        self.m = self.g.module_by_name('M')

    def test_definitions(self):
        """Annotations on module / struct / union / const and other definitions are kept.

        module/struct/union/const などの定義に付いたアノテーションが保持される。
        """
        self.assertTrue(self.m.has_annotation('topic'))
        s = self.m.struct_by_name('S')
        self.assertEqual([str(a) for a in s.annotations], ['@extensibility(FINAL)', '@nested(FALSE)'])
        self.assertEqual(s.annotation_by_name('extensibility').value, 'FINAL')
        self.assertEqual(self.m.union_by_name('U').annotation_by_name('extensibility').value, 'APPENDABLE')
        self.assertEqual(self.m.const_by_name('C').annotation_by_name('verbatim').params,
                         {'language': '"c++"', 'text': '"x"'})
        self.assertEqual(self.m.const_by_name('C').value, '3')
        t = self.m.typedef_by_name('Small')
        self.assertEqual(t.annotation_by_name('range').params, {'min': '0', 'max': '9'})
        self.assertEqual(str(t.type), 'long')
        self.assertEqual(self.m.interface_by_name('I').annotation_by_name('service').params,
                         {'platform': '"DDS"'})

    def test_struct_members_types_are_clean(self):
        """Annotations on struct members do not leak into the member type names.

        アノテーション付きメンバーの型名にアノテーションが混入しない。
        """
        s = self.m.struct_by_name('S')
        expected = {'id': 'long', 'v': 'long', 'o': 'sequence<long>', 'speed': 'double', 'plain': 'long'}
        for name, typ in expected.items():
            self.assertEqual(str(s.member_by_name(name).type), typ, name)
        # A non-primitive member with an annotation used to raise InvalidDataTypeException
        self.assertEqual(s.member_by_name('a').type.full_path, 'M::A')

    def test_struct_members_annotations(self):
        """@key / @range / @default / @optional and others on struct members are kept.

        struct メンバーの @key/@range/@default/@optional などが保持される。
        """
        s = self.m.struct_by_name('S')
        self.assertTrue(s.member_by_name('id').has_annotation('key'))
        self.assertTrue(s.member_by_name('a').has_annotation('key'))
        v = s.member_by_name('v')
        self.assertEqual([a.name for a in v.annotations], ['range', 'default'])
        self.assertEqual(v.annotation_by_name('default').value, '5')
        self.assertTrue(s.member_by_name('o').has_annotation('optional'))
        self.assertEqual(s.member_by_name('speed').annotation_by_name('unit').value, '"m/s"')
        self.assertEqual(s.member_by_name('plain').annotations, [])

    def test_union_members(self):
        """Union member annotations and case labels are read correctly.

        union メンバーのアノテーションと case ラベルが正しく取れる。
        """
        u = self.m.union_by_name('U')
        a = u.member_by_name('a')
        self.assertTrue(a.has_annotation('key'))
        self.assertEqual(a.type.name, 'long')
        self.assertEqual(a.descriminator_value_associations, ['1'])
        self.assertTrue(u.member_by_name('b').has_annotation('external'))

    def test_enum_values(self):
        """Annotations on each enum value (such as @value) are kept.

        enum 値ごとのアノテーション(@value など)が保持される。
        """
        e = self.m.enum_by_name('E')
        self.assertEqual([v.name for v in e.values], ['ONE', 'TWO', 'THREE'])
        self.assertEqual(e.value_by_name('TWO').annotation_by_name('value').value, '2')
        self.assertEqual(e.value_by_name('THREE').annotation_by_name('foo').args, ['1', '2'])

    def test_interface(self):
        """Annotations on methods and arguments are kept, and argument directions and types are correct.

        メソッドと引数に付いたアノテーションが保持され、引数の向き・型も正しい。
        """
        f = self.m.interface_by_name('I').method_by_name('f')
        self.assertTrue(f.has_annotation('oneway_hint'))
        self.assertEqual(str(f.returns), 'void')
        self.assertEqual([(a.name, a.direction, str(a.type)) for a in f.arguments],
                         [('x', 'in', 'long'), ('y', 'in', 'A')])
        self.assertEqual(f.argument_by_name('x').annotation_by_name('range').params, {'min': '0', 'max': '9'})

    def test_to_dic(self):
        """to_dic() outputs annotations, and leaves the key out when there are none.

        to_dic() にアノテーションが出力され、無いときはキー自体が出ない。
        """
        s = self.m.struct_by_name('S').to_dic()
        self.assertEqual(s['annotations'][0], {'name': 'extensibility', 'args': ['FINAL'], 'params': {}})
        members = {m['name']: m for m in s['members']}
        self.assertEqual(members['id']['annotations'], [{'name': 'key', 'args': [], 'params': {}}])
        self.assertEqual(members['id']['type'], 'long')
        # no 'annotations' key when there are none, so existing output does not change
        self.assertNotIn('annotations', members['plain'])
        self.assertNotIn('annotations', self.m.struct_by_name('A').to_dic())

    def test_reopened_module_collects_annotations(self):
        """Annotations of a reopened module are collected from both definitions.

        再オープンした module のアノテーションが両方とも集約される。
        """
        g = load('@a module M { struct S { long x; }; };\n@b module M { struct T { long x; }; };')
        self.assertEqual([a.name for a in g.module_by_name('M').annotations], ['a', 'b'])

    def test_annotation_definition_is_skipped(self):
        """An @annotation definition block is skipped, and uses of that annotation are parsed.

        @annotation 定義ブロックは読み飛ばし、その注釈の使用は解析できる。
        """
        g = load('@annotation MyAnn { long value default 0; };\nmodule M { @MyAnn(3) struct S { long x; }; };')
        s = g.module_by_name('M').struct_by_name('S')
        self.assertEqual(s.annotation_by_name('MyAnn').value, '3')


if __name__ == '__main__':
    unittest.main()
