"""Forward-declared types used as sequence / array element types (issue #67).

Forward-declared interfaces, structs and unions may be used as element types
before their definition.
"""
import contextlib
import io
import unittest
from idl_parser import parser


def load(idl):
    with contextlib.redirect_stdout(io.StringIO()):
        return parser.IDLParser().load(idl)


class DeclaredElementTypeTestFunctions(unittest.TestCase):

    def test_forward_struct(self):
        M = load('module M { struct F; struct G { sequence<F> fs; F arr[2]; };'
                 ' struct F { long x; }; };').module_by_name('M')
        fs = M.struct_by_name('G').members[0].type
        self.assertIs(fs.inner_type.obj, M.struct_by_name('F'))

    def test_forward_union(self):
        M = load('module M { union U; typedef sequence<U> US;'
                 ' union U switch (long) { case 1: long x; }; };').module_by_name('M')
        self.assertIs(M.typedef_by_name('US').type.inner_type.obj, M.union_by_name('U'))

    def test_forward_interface(self):
        M = load('module M { interface I; struct S { sequence<I> is_; };'
                 ' interface I { void f(); }; };').module_by_name('M')
        self.assertIs(M.struct_by_name('S').members[0].type.inner_type.obj,
                      M.interface_by_name('I'))

    def test_forward_without_definition(self):
        # Unchanged: a forward-declared type that is never defined is accepted
        M = load('module M { struct F; struct G { sequence<F> fs; }; };').module_by_name('M')
        self.assertEqual(M.undefined_forward_structs, ['F'])


if __name__ == '__main__':
    unittest.main()
