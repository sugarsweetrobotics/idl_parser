"""Tests for issue #99: valuetype and eventtype.

"valuetype" and "eventtype" were skipped with an UnsupportedIDLSyntaxWarning,
so they were missing from IDLModule, to_dic() and to_simple_dic(), and a
member or an argument of such a type failed with "Can not find Data Type".
They are now IDLValueType / IDLEventType objects in IDLModule.valuetypes and
IDLModule.eventtypes, with state members, factories, operations, attributes,
base value types, supported interfaces, modifiers, boxed value types and
forward declarations.
"""
import unittest
import warnings
from idl_parser import parser
from idl_parser.exception import (IDLCanNotFindException, IDLParserWarning,
                                  InvalidDataTypeException, InvalidIDLSyntaxError)


IDL = '''
module M {
  interface I { void ping(); };
  exception X { string why; };
  struct S { long a; };
  valuetype V {
    public long x;
    private string y;
    public sequence<long, 10> values, others;
    public long arr[3];
    factory create(in long x) raises (X);
    long get();
    attribute long z;
    struct Inner { long b; };
    public Inner nested;
  };
  abstract valuetype A { void f(); };
  custom valuetype C { public long z; };
  valuetype D : V supports I { };
  valuetype T : truncatable V, A { public T next; public sequence<T> kids; };
  valuetype Boxed long;
  valuetype BoxedS S;
  valuetype BoxedSeq sequence<long, 10>;
  @final eventtype E { public long x; };
  abstract eventtype AE { };
  eventtype E2 : E supports I { };
  valuetype F;
  struct Holder { V v; Boxed b; E e; F f; V::Inner i; };
  valuetype F { public long q; };
  interface J { V op(in E e, in Boxed b); };
};
'''


def load(idl):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        g = parser.IDLParser().load(idl)
    return g, [w for w in caught if issubclass(w.category, IDLParserWarning)]


class ValueTypeTest(unittest.TestCase):
    """Category: Value types and event types / カテゴリ: valuetype・eventtype

    valuetype definitions (issue #99).
    valuetype の定義(#99)。
    """

    @classmethod
    def setUpClass(cls):
        cls.g, cls.warnings = load(IDL)
        cls.m = cls.g.module_by_name('M')

    def test_no_warning(self):
        """valuetype and eventtype give no UnsupportedIDLSyntaxWarning any more.

        valuetype と eventtype で UnsupportedIDLSyntaxWarning が出なくなる。
        """
        self.assertEqual(self.warnings, [])

    def test_listed_in_module(self):
        """Value types and event types are listed in their module, in order.

        valuetype と eventtype は module に定義順で入る。
        """
        self.assertEqual([v.name for v in self.m.valuetypes],
                         ['V', 'A', 'C', 'D', 'T', 'Boxed', 'BoxedS', 'BoxedSeq', 'F'])
        self.assertEqual([e.name for e in self.m.eventtypes], ['E', 'AE', 'E2'])
        self.assertEqual(self.m.valuetype_by_name('V').full_path, 'M::V')
        self.assertIsNone(self.m.valuetype_by_name('E'))
        self.assertEqual(self.m.eventtype_by_name('E').full_path, 'M::E')
        self.assertEqual(self.m.for_each_valuetype(lambda v: v.name)[:2], ['V', 'A'])

    def test_kind(self):
        """is_valuetype is True for both; is_eventtype only for an eventtype.

        is_valuetype はどちらでも True、is_eventtype は eventtype だけ True。
        """
        v = self.m.valuetype_by_name('V')
        e = self.m.eventtype_by_name('E')
        self.assertEqual((v.classname, v.is_valuetype, v.is_eventtype, v.is_interface),
                         ('IDLValueType', True, False, False))
        self.assertEqual((e.classname, e.is_valuetype, e.is_eventtype),
                         ('IDLEventType', True, True))

    def test_state_members(self):
        """public / private state members, with declarator lists and arrays.

        public / private の状態メンバー(複数宣言・配列を含む)。
        """
        v = self.m.valuetype_by_name('V')
        self.assertEqual([(s.visibility, s.name, str(s.type)) for s in v.state_members],
                         [('public', 'x', 'long'), ('private', 'y', 'string'),
                          ('public', 'values', 'sequence<long>'),
                          ('public', 'others', 'sequence<long>'),
                          ('public', 'arr', 'long[3]'), ('public', 'nested', 'Inner')])
        self.assertFalse(v.state_member_by_name('y').is_public)
        self.assertEqual(v.state_member_by_name('nested').type.full_path, 'M::V::Inner')
        self.assertIsNone(v.state_member_by_name('nope'))

    def test_factory(self):
        """A factory has arguments and raises, and no return type.

        factory は引数と raises を持ち、戻り値型はない。
        """
        f = self.m.valuetype_by_name('V').factory_by_name('create')
        self.assertEqual(f.classname, 'IDLFactory')
        self.assertEqual([a.to_simple_dic() for a in f.arguments], ['in long x'])
        self.assertEqual([x.full_path for x in f.exceptions], ['M::X'])
        self.assertIsNone(f.returns)
        self.assertNotIn('returns', f.to_dic())

    def test_operations_attributes_definitions(self):
        """Operations, attributes and definitions are read as in an interface.

        operation、attribute、型定義は interface と同じように読む。
        """
        v = self.m.valuetype_by_name('V')
        self.assertEqual([m.name for m in v.methods], ['get'])
        self.assertEqual([a.name for a in v.attributes], ['z'])
        self.assertEqual([s.full_path for s in v.structs], ['M::V::Inner'])
        self.assertEqual(self.m.struct_by_name('Holder').member_by_name('i').type.full_path,
                         'M::V::Inner')

    def test_inheritance_and_supports(self):
        """Base value types (with truncatable) and supported interfaces are resolved.

        基底 valuetype(truncatable を含む)と supports の interface を解決する。
        """
        d = self.m.valuetype_by_name('D')
        self.assertEqual([b.full_path for b in d.inheritances], ['M::V'])
        self.assertEqual([i.full_path for i in d.supports], ['M::I'])
        self.assertFalse(d.is_truncatable)
        t = self.m.valuetype_by_name('T')
        self.assertTrue(t.is_truncatable)
        self.assertEqual([b.full_path for b in t.inheritances], ['M::V', 'M::A'])
        e2 = self.m.eventtype_by_name('E2')
        self.assertEqual([b.full_path for b in e2.inheritances], ['M::E'])
        self.assertEqual([i.full_path for i in e2.supports], ['M::I'])

    def test_recursive_member(self):
        """A value type can refer to itself.

        valuetype は自分自身を参照できる。
        """
        t = self.m.valuetype_by_name('T')
        self.assertIs(t.state_member_by_name('next').type, t)
        self.assertEqual(str(t.state_member_by_name('kids').type), 'sequence<T>')

    def test_modifiers(self):
        """abstract and custom are kept; annotations apply too.

        abstract と custom を保持し、アノテーションも付く。
        """
        flags = lambda v: (v.is_abstract, v.is_custom)
        self.assertEqual(flags(self.m.valuetype_by_name('V')), (False, False))
        self.assertEqual(flags(self.m.valuetype_by_name('A')), (True, False))
        self.assertEqual(flags(self.m.valuetype_by_name('C')), (False, True))
        self.assertEqual(flags(self.m.eventtype_by_name('AE')), (True, False))
        self.assertTrue(self.m.eventtype_by_name('E').has_annotation('final'))

    def test_boxed(self):
        """A boxed value type wraps a single type.

        boxed value は一つの型を包む。
        """
        b = self.m.valuetype_by_name('Boxed')
        self.assertTrue(b.is_boxed)
        self.assertEqual(str(b.boxed_type), 'long')
        self.assertIs(self.m.valuetype_by_name('BoxedS').boxed_type, self.m.struct_by_name('S'))
        self.assertTrue(self.m.valuetype_by_name('BoxedSeq').boxed_type.is_sequence)
        self.assertFalse(self.m.valuetype_by_name('V').is_boxed)
        self.assertIsNone(self.m.valuetype_by_name('V').boxed_type)

    def test_forward_declaration(self):
        """A forward-declared value type can be used before its definition.

        前方宣言した valuetype は定義の前に使える。
        """
        self.assertEqual(self.m.forward_valuetypes, ['F'])
        self.assertEqual(self.m.undefined_forward_valuetypes, [])
        f = self.m.struct_by_name('Holder').member_by_name('f')
        self.assertIs(f.type, self.m.valuetype_by_name('F'))

    def test_used_as_type(self):
        """Value types and event types are found as member, argument and return types.

        valuetype と eventtype はメンバー・引数・戻り値の型として見つかる。
        """
        h = self.m.struct_by_name('Holder')
        self.assertIs(h.member_by_name('v').type, self.m.valuetype_by_name('V'))
        self.assertIs(h.member_by_name('e').type, self.m.eventtype_by_name('E'))
        op = self.m.interface_by_name('J').method_by_name('op')
        self.assertIs(op.returns.obj, self.m.valuetype_by_name('V'))
        self.assertIs(op.arguments[0].type.obj, self.m.eventtype_by_name('E'))
        self.assertIs(op.arguments[1].type.obj, self.m.valuetype_by_name('Boxed'))

    def test_to_dic(self):
        """to_dic() has the value types and event types.

        to_dic() に valuetype と eventtype が入る。
        """
        dic = self.g.to_dic()['modules'][0]
        self.assertEqual([v['name'] for v in dic['eventtypes']], ['E', 'AE', 'E2'])
        v = dic['valuetypes'][0]
        self.assertEqual(v['classname'], 'IDLValueType')
        self.assertEqual(v['state_members'][1],
                         {'name': 'y', 'filepath': None, 'classname': 'IDLStateMember',
                          'type': 'string', 'visibility': 'private'})
        self.assertEqual(v['factories'][0]['name'], 'create')
        self.assertEqual([m['name'] for m in v['methods']], ['get'])
        self.assertEqual(dic['valuetypes'][1]['abstract'], True)
        self.assertEqual(dic['valuetypes'][3]['supports'], ['M::I'])
        self.assertEqual(dic['valuetypes'][4]['truncatable'], True)
        self.assertEqual(dic['valuetypes'][5],
                         {'name': 'Boxed', 'filepath': None, 'classname': 'IDLValueType',
                          'boxed_type': 'long'})
        self.assertEqual(self.g.to_dic()['valuetypes'], [])

    def test_to_simple_dic(self):
        """to_simple_dic() lists them after the interfaces.

        to_simple_dic() では interface の後に並ぶ。
        """
        entries = self.m.to_simple_dic()['module M']
        self.assertIn({'valuetype Boxed': 'long'}, entries)
        self.assertIn({'valuetype D': [{'inherits': ['M::V']}, {'supports': ['M::I']}]}, entries)
        self.assertIn({'eventtype E': [{'inherits': []}, {'public x': 'long'}]}, entries)
        v = self.m.valuetype_by_name('V').to_simple_dic()['valuetype V']
        self.assertEqual(v[:3], [{'inherits': []}, {'public x': 'long'}, {'private y': 'string'}])
        self.assertIn({'factory create': ['in long x']}, v)
        self.assertEqual(self.m.valuetype_by_name('V').to_simple_dic(quiet=True), 'valuetype V')

    def test_constructor_python(self):
        """generate_constructor_python() gives None for a value type.

        generate_constructor_python() は valuetype に None を出す。
        """
        p = parser.IDLParser()
        self.assertEqual(p.generate_constructor_python(self.m.struct_by_name('Holder')),
                         'M.Holder(None, None, None, None, M.V.Inner(0))')

    def test_global_scope(self):
        """A value type at the global scope is found with or without "::".

        グローバルスコープの valuetype は "::" の有無によらず見つかる。
        """
        g, _ = load('valuetype V { public long x; }; valuetype W : ::V { }; struct S { V v; };')
        self.assertEqual(g.valuetypes[0].full_path, '::V')
        self.assertIs(g.valuetypes[1].inheritances[0], g.valuetypes[0])
        self.assertIs(g.structs[0].member_by_name('v').type, g.valuetypes[0])


class ValueTypeErrorTest(unittest.TestCase):
    """Category: Value types and event types / カテゴリ: valuetype・eventtype

    Invalid valuetype and eventtype definitions (issue #99).
    正しくない valuetype / eventtype の定義(#99)。
    """

    def assertError(self, exc, idl, text):
        with self.assertRaises(exc) as cm:
            load('module M {\n' + idl + '\n};')
        self.assertIn(text, str(cm.exception))

    def test_unknown_base_and_interface(self):
        """An unknown base value type or supported interface is an error.

        未定義の基底 valuetype や supports の interface はエラーになる。
        """
        self.assertError(IDLCanNotFindException, 'valuetype D : X { };',
                         '"X" valuetype which is a base of "D"')
        self.assertError(IDLCanNotFindException, 'valuetype D supports X { };',
                         '"X" interface supported by "D"')
        self.assertError(IDLCanNotFindException, 'valuetype B { }; valuetype D supports B { };',
                         '"B" interface supported by "D"')
        self.assertError(IDLCanNotFindException, 'valuetype B; valuetype D : B { };',
                         '"B" is only forward-declared')

    def test_invalid_declarations(self):
        """Declarations that IDL does not allow are errors.

        IDL で許されない宣言はエラーになる。
        """
        cases = [
            ('eventtype E long;', 'only a valuetype can be boxed'),
            ('abstract valuetype A { public long x; };', 'can not have state members'),
            ('abstract valuetype A { factory c(); };', 'can not have factories'),
            ('abstract custom valuetype A { };', 'both abstract and custom'),
            ('valuetype B { }; abstract valuetype A : truncatable B { };', 'can not be truncatable'),
            ('custom valuetype B long;', 'can not be abstract or custom'),
            ('valuetype B { public x; };', 'Invalid state member declaration'),
            ('valuetype B { }; valuetype D : B, B { };', 'inherited more than once'),
            ('valuetype D : { };', 'Name of a base valuetype is expected'),
            ('valuetype D { public long x; }', 'No ";" after "}"'),
        ]
        for idl, text in cases:
            with self.subTest(idl):
                self.assertError(InvalidIDLSyntaxError, idl, text)

    def test_unknown_boxed_type(self):
        """A boxed value type of an unknown type is an error.

        未定義の型の boxed value はエラーになる。
        """
        self.assertError(InvalidDataTypeException, 'valuetype B Nope;', 'Nope')


if __name__ == '__main__':
    unittest.main()
