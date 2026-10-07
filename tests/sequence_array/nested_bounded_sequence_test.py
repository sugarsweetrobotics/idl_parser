"""Nested and bounded sequences (issue #31).

``sequence<string<8>>``, ``sequence<sequence<long>>`` and ``sequence<long, 10>``
used to be cut at the first ``>``, which silently broke the element type.
As with bounded strings (#26, #27), the type name has no bound and the
bound is available via ``.bound`` (None when unbounded).
"""
import unittest

from idl_parser import parser, exception
from idl_parser import type as idl_type


def member_type(decl):
    g = parser.IDLParser().load('module M { struct S { %s }; };' % decl)
    return g.module_by_name('M').struct_by_name('S').member_by_name('a').type


def typedef_type(decl):
    g = parser.IDLParser().load('module M { typedef %s; };' % decl)
    return g.module_by_name('M').typedef_by_name('X').type


class NestedBoundedSequenceTest(unittest.TestCase):

    def _check_all(self, get, decl_fmt):
        cases = [
            # (declaration of type, str(type), element name, element bound, sequence bound)
            ('sequence<long>', 'sequence<long>', 'long', None, None),
            ('sequence<string<8>>', 'sequence<string>', 'string', 8, None),
            ('sequence<string<8> >', 'sequence<string>', 'string', 8, None),
            ('sequence<long, 10>', 'sequence<long>', 'long', None, 10),
            ('sequence<long,10>', 'sequence<long>', 'long', None, 10),
            ('sequence< long , 10 >', 'sequence<long>', 'long', None, 10),
            ('sequence<string<8>, 10>', 'sequence<string>', 'string', 8, 10),
        ]
        for decl, s, elem, elem_bound, bound in cases:
            with self.subTest(decl=decl):
                t = get(decl_fmt % decl)
                self.assertTrue(t.is_sequence)
                self.assertEqual(str(t), s)
                self.assertEqual(t.bound, bound)
                self.assertEqual(t.is_bounded_sequence, bound is not None)
                self.assertEqual(t.inner_type.name, elem)
                self.assertTrue(t.inner_type.is_primitive)
                self.assertEqual(t.inner_type.bound, elem_bound)

    def test_member(self):
        self._check_all(member_type, '%s a;')

    def test_typedef(self):
        self._check_all(typedef_type, '%s X')

    def test_type_name_has_no_bound(self):
        self.assertEqual(member_type('sequence<long, 10> a;').name, 'sequence < long >')
        self.assertEqual(member_type('sequence<string<8>> a;').name, 'sequence < string >')

    def test_nested_sequence(self):
        for get, decl in ((member_type, 'sequence<sequence<long>> a;'),
                          (member_type, 'sequence<sequence<long> > a;'),
                          (typedef_type, 'sequence<sequence<long>> X')):
            with self.subTest(decl=decl):
                t = get(decl)
                self.assertEqual(str(t), 'sequence<sequence<long>>')
                self.assertIsNone(t.bound)
                inner = t.inner_type
                self.assertTrue(inner.is_sequence)
                self.assertFalse(inner.is_primitive)
                self.assertEqual(inner.inner_type.name, 'long')
                self.assertTrue(inner.inner_type.is_primitive)

    def test_nested_bounded_sequence(self):
        t = member_type('sequence<sequence<string<4>, 3>, 5> a;')
        self.assertEqual(str(t), 'sequence<sequence<string>>')
        self.assertEqual(t.bound, 5)
        self.assertEqual(t.inner_type.bound, 3)
        self.assertEqual(t.inner_type.inner_type.name, 'string')
        self.assertEqual(t.inner_type.inner_type.bound, 4)

    def test_nested_sequence_of_struct(self):
        g = parser.IDLParser().load(
            'module M { struct T { long x; }; struct S { sequence<sequence<T>, 2> a; }; };')
        t = g.module_by_name('M').struct_by_name('S').member_by_name('a').type
        self.assertEqual(t.bound, 2)
        self.assertEqual(t.inner_type.inner_type.obj.full_path, 'M::T')

    def test_const_bound_is_kept_as_written(self):
        g = parser.IDLParser().load(
            'module M { const long N = 5; struct S { sequence<long, N> a; }; };')
        t = g.module_by_name('M').struct_by_name('S').member_by_name('a').type
        self.assertEqual(t.bound, 'N')

    def test_array_of_sequence(self):
        t = member_type('sequence<long, 4> a[3];')
        self.assertTrue(t.is_array)
        self.assertEqual(t.size, 3)
        self.assertTrue(t.inner_type.is_sequence)
        self.assertEqual(t.inner_type.bound, 4)
        self.assertEqual(t.inner_type.inner_type.name, 'long')

    def test_operation_argument(self):
        g = parser.IDLParser().load(
            'module M { interface I { void f(in sequence<long, 10> a, in sequence<string<8>> b, in long c); }; };')
        args = g.module_by_name('M').interface_by_name('I').method_by_name('f').arguments
        self.assertEqual([a.name for a in args], ['a', 'b', 'c'])
        self.assertEqual(args[0].type.bound, 10)
        self.assertEqual(args[0].type.inner_type.name, 'long')
        self.assertEqual(args[1].type.inner_type.bound, 8)

    def test_unmatched_brackets(self):
        for name in ('sequence<long', 'sequence<sequence<long>', 'sequence<>',
                     'sequence<long, >', 'sequence<long, 1, 2>'):
            with self.subTest(name=name):
                with self.assertRaises(exception.InvalidIDLSyntaxError):
                    idl_type.parse_sequence(name)

    def test_parse_sequence(self):
        self.assertEqual(idl_type.parse_sequence('sequence<string<8>, 10>'), ('string<8>', 10))
        self.assertEqual(idl_type.parse_sequence('sequence < sequence<long> >'), ('sequence<long>', None))
        self.assertIsNone(idl_type.parse_sequence('long'))
        self.assertIsNone(idl_type.parse_sequence('my_sequence'))


if __name__ == '__main__':
    unittest.main()
