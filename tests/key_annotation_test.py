"""IDL 4 @key annotation as struct keys (issue #37).

Keys from ``#pragma keylist`` and ``@key`` are combined; when they disagree
the keylist wins.
"""
import unittest
from idl_parser import parser


def struct(idl, name='S'):
    return parser.IDLParser().load(idl).module_by_name('M').struct_by_name(name)


class KeyAnnotationTest(unittest.TestCase):

    def test_single_key(self):
        s = struct('module M { struct S { @key long id; long v; }; };')
        self.assertEqual(s.keys, ['id'])
        self.assertTrue(s.has_keylist)
        self.assertTrue(s.member_by_name('id').is_key)
        self.assertFalse(s.member_by_name('v').is_key)
        self.assertEqual([m.name for m in s.members], ['id', 'v'])

    def test_multiple_keys_in_member_order(self):
        s = struct('module M { struct S { @key long b; long v; @key(TRUE) string a; }; };')
        self.assertEqual(s.keys, ['b', 'a'])

    def test_key_false(self):
        for value in ('FALSE', 'false'):
            with self.subTest(value):
                s = struct('module M { struct S { @key(%s) long id; long v; }; };' % value)
                self.assertEqual(s.keys, [])
                self.assertFalse(s.has_keylist)
                self.assertNotIn('keys', s.to_dic())

    def test_named_value(self):
        s = struct('module M { struct S { @key(value=TRUE) long id; @key(value=FALSE) long v; }; };')
        self.assertEqual(s.keys, ['id'])

    def test_non_primitive_key_member(self):
        s = struct('module M { struct A { long x; }; struct S { @key A a; long v; }; };')
        self.assertEqual(s.keys, ['a'])
        self.assertEqual(s.member_by_name('a').type.full_path, 'M::A')

    def test_no_keys(self):
        s = struct('module M { struct S { long id; }; };')
        self.assertEqual(s.keys, [])
        self.assertFalse(s.has_keylist)
        self.assertIsNone(s.pragma_keys)
        self.assertEqual(s.annotated_keys, [])

    def test_to_dic(self):
        s = struct('module M { struct S { @key long id; long v; }; };')
        self.assertEqual(s.to_dic()['keys'], ['id'])


class KeylistAndKeyAnnotationTest(unittest.TestCase):

    def test_same_keys(self):
        s = struct('module M { struct S { @key long id; long v; }; };\n#pragma keylist M::S id\n')
        self.assertEqual(s.keys, ['id'])

    def test_combined_keylist_first(self):
        s = struct('module M { struct S { @key long a; long b; @key long c; }; };\n#pragma keylist M::S b\n')
        self.assertEqual(s.keys, ['b', 'a', 'c'])
        self.assertEqual(s.pragma_keys, ['b'])
        self.assertEqual(s.annotated_keys, ['a', 'c'])

    def test_keylist_wins_over_key_false(self):
        s = struct('module M { struct S { @key(FALSE) long id; long v; }; };\n#pragma keylist M::S id\n')
        self.assertEqual(s.keys, ['id'])
        self.assertFalse(s.member_by_name('id').is_key)

    def test_keylist_without_keys_and_key(self):
        s = struct('module M { struct S { @key long id; long v; }; };\n#pragma keylist M::S\n')
        self.assertEqual(s.pragma_keys, [])
        self.assertEqual(s.keys, ['id'])

    def test_keylist_before_struct(self):
        s = struct('#pragma keylist M::S v\nmodule M { struct S { @key long id; long v; }; };\n')
        self.assertEqual(s.keys, ['v', 'id'])


if __name__ == '__main__':
    unittest.main()
