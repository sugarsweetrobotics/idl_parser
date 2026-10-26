"""Keywords used as identifiers (issue #119).

A keyword such as long, any or Object used as the name of a definition, a
member or an argument was read silently. With any, Object and ValueBase
being primitive types, "struct Object { ... }; struct T { Object o; };"
would silently give o the built-in Object type, so these are errors now.
"""
import unittest
from idl_parser import parser
from idl_parser.exception import InvalidIDLSyntaxError


def error_of(idl):
    try:
        parser.IDLParser().load(idl)
    except InvalidIDLSyntaxError as e:
        return e
    return None


class ReservedWordTest(unittest.TestCase):
    """Category: Lexing, preprocessing and error line numbers / カテゴリ: 字句解析・前処理・エラー行番号

    Keywords can not be used as identifiers (issue #119).
    予約語は識別子として使えない(#119)。
    """

    def test_definition_names(self):
        """A keyword as the name of a definition is an error with its line number.

        予約語を定義名に使うと行番号つきのエラーになる。
        """
        for idl, what in (('module long { };', 'module'),
                          ('interface any { };', 'interface'),
                          ('struct Object { long x; };', 'struct'),
                          ('exception fixed { };', 'exception'),
                          ('enum ValueBase { A };', 'enum'),
                          ('union map switch (long) { case 1: long x; };', 'union'),
                          ('native string;', 'native'),
                          ('const long TRUE = 1;', 'const'),
                          ('@bit_bound(8) bitmask int8 { A };', 'bitmask'),
                          ('bitset octet { bitfield<3> a; };', 'bitset'),
                          ('valuetype any { public long x; };', 'valuetype'),
                          ('eventtype Object { public long x; };', 'eventtype')):
            with self.subTest(idl):
                e = error_of('module M {\n  ' + idl + '\n};')
                self.assertIsNotNone(e)
                self.assertEqual(e.line_number, 2)
                self.assertIn('can not be used as a name (%s)' % what, str(e))

    def test_typedef_and_members(self):
        """A keyword as the name of a typedef, member or attribute is an error.

        予約語を typedef・メンバー・属性の名前に使うとエラーになる。
        """
        for idl, word in (('typedef long ValueBase;', 'ValueBase'),
                          ('typedef long A, string;', 'string'),
                          ('struct S { long any; };', 'any'),
                          ('struct S { long a, fixed[2]; };', 'fixed'),
                          ('union U switch (long) { case 1: long map; };', 'map'),
                          ('valuetype V { public long Object; };', 'Object'),
                          ('interface I { attribute long in; };', 'in')):
            with self.subTest(idl):
                e = error_of(idl)
                self.assertIsNotNone(e)
                self.assertIn('The keyword "%s" can not be used as a name' % word, str(e))

    def test_operations_and_values(self):
        """A keyword as an operation, argument, enumerator or bitfield name is an error.

        予約語をオペレーション・引数・列挙子・ビットフィールドの名前に使うとエラーになる。
        """
        for idl, what in (('interface I { long fixed(); };', 'operation in "I"'),
                          ('interface I { void op(in long any); };', 'argument of operation "op"'),
                          ('enum E { A, Object };', 'enumerator of enum "E"'),
                          ('@bit_bound(8) bitmask B { long };', 'value of bitmask "B"'),
                          ('bitset X { bitfield<3> any; };', 'bitfield of bitset "X"')):
            with self.subTest(idl):
                e = error_of(idl)
                self.assertIsNotNone(e)
                self.assertIn('can not be used as a name (%s)' % what, str(e))

    def test_user_type_named_object(self):
        """A struct named Object is an error rather than being shadowed by the built-in type.

        Object という名前の struct は、組み込み型に置き換わらずにエラーになる。
        """
        e = error_of('struct Object { long x; };\nstruct T { Object o; };')
        self.assertIsNotNone(e)
        self.assertEqual(e.line_number, 1)

    def test_names_that_are_not_keywords(self):
        """Names that only contain or resemble a keyword are accepted.

        予約語を含むだけの名前や、CCM の予約語(port など)は使える。
        """
        g = parser.IDLParser().load('''
        module M {
          struct S { long long_value; any anything; long object; long port; long component; };
          enum Kind { Any, Fixed };
          interface I { void fixed_op(in long in_value); };
        };''')
        s = g.find_types('M::S')[0]
        self.assertEqual([m.name for m in s.members],
                         ['long_value', 'anything', 'object', 'port', 'component'])


if __name__ == '__main__':
    unittest.main()
