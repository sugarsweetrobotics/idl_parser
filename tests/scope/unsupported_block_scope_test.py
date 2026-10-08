"""Regression tests for issue #39.

An unsupported construct with a "{ ... }" body (bitmask, bitset, CORBA
exception, ...) used to have its closing "}" taken as the end of the
enclosing module, so later definitions went to the wrong scope or were lost
without any error.
"""
import unittest
from idl_parser import parser
from idl_parser.exception import InvalidIDLSyntaxError


def load(idl):
    return parser.IDLParser().load(idl)


TRAILER = '''
  struct S { long x; };
};
module N { struct T { long x; }; };
'''

UNSUPPORTED = {
    'bitmask': 'bitmask F { X, Y };',
    'bitmask_annotated': '@bit_bound(8) bitmask F { X, Y };',
    'bitset': 'bitset B { bitfield<3> a; };',
    'exception': 'exception E { string msg; };',
    'nested_braces': 'bitset B { bitfield<3> a; }; exception E { string msg; };',
}


class Issue39Test(unittest.TestCase):

    def test_following_definitions_keep_their_scope(self):
        for label, decl in UNSUPPORTED.items():
            with self.subTest(label):
                g = load('module M {\n  struct A { long a; };\n  ' + decl + TRAILER)
                self.assertEqual([m.name for m in g.modules], ['M', 'N'])
                self.assertEqual(g.structs, [])
                m = g.module_by_name('M')
                self.assertEqual([s.name for s in m.structs], ['A', 'S'])
                self.assertEqual(m.struct_by_name('S').full_path, 'M::S')
                n = g.module_by_name('N')
                self.assertEqual([s.full_path for s in n.structs], ['N::T'])

    def test_unsupported_block_at_global_scope(self):
        g = load('bitmask F { X, Y };\nstruct S { long x; };\nmodule N { struct T { long x; }; };')
        self.assertEqual([s.full_path for s in g.structs], ['::S'])
        self.assertEqual([m.name for m in g.modules], ['N'])

    def test_unclosed_unsupported_block_raises(self):
        with self.assertRaises(InvalidIDLSyntaxError):
            load('module M { bitmask F { X, Y ;\n struct S { long x; }; ')


if __name__ == '__main__':
    unittest.main()
