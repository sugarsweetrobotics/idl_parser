"""Annotations before definitions, and @bit_bound applying to the next one only (issue #39)."""
import unittest
from idl_parser import parser
from idl_parser.exception import InvalidIDLSyntaxError


def load(idl):
    return parser.IDLParser().load(idl)


class AnnotationTest(unittest.TestCase):
    """@bit_bound only affects the bitmask it is written before."""

    def test_other_definitions_parse_with_annotations(self):
        g = load('@bit_bound(8) enum E { A, B };\n@nested(FALSE) @extensibility(FINAL) struct S { long x; };')
        self.assertEqual([v.name for v in g.enum_by_name('E').values], ['A', 'B'])
        self.assertIsNotNone(g.struct_by_name('S'))

    def test_annotation_applies_to_next_definition_only(self):
        g = load('@bit_bound(8) struct S { long x; };\nbitmask F { A };')
        self.assertEqual(g.bitmask_by_name('F').bit_bound, 32)

    def test_unclosed_annotation_raises(self):
        with self.assertRaises(InvalidIDLSyntaxError):
            load('@bit_bound(8 bitmask F { A };')


if __name__ == '__main__':
    unittest.main()
