"""Annotations before definitions, and @bit_bound applying to the next one only (issue #39)."""
import unittest
from idl_parser import parser
from idl_parser.exception import InvalidIDLSyntaxError


def load(idl):
    return parser.IDLParser().load(idl)


class AnnotationTest(unittest.TestCase):
    """Category: Annotations / カテゴリ: アノテーション

    @bit_bound only affects the bitmask it is written before.
    @bit_bound は直後の bitmask にだけ効く。
    """

    def test_other_definitions_parse_with_annotations(self):
        """Enums and structs with annotations before them are parsed correctly.

        enum/struct の前のアノテーションがあっても正しく解析される。
        """
        g = load('@bit_bound(8) enum E { A, B };\n@nested(FALSE) @extensibility(FINAL) struct S { long x; };')
        self.assertEqual([v.name for v in g.enum_by_name('E').values], ['A', 'B'])
        self.assertIsNotNone(g.struct_by_name('S'))

    def test_annotation_applies_to_next_definition_only(self):
        """@bit_bound applies only to the next definition and does not leak into a later bitmask.

        @bit_bound は直後の定義にだけ効き、後続の bitmask には漏れない。
        """
        g = load('@bit_bound(8) struct S { long x; };\nbitmask F { A };')
        self.assertEqual(g.bitmask_by_name('F').bit_bound, 32)

    def test_unclosed_annotation_raises(self):
        """An unclosed "@bit_bound(" raises InvalidIDLSyntaxError.

        閉じていない @bit_bound( で InvalidIDLSyntaxError。
        """
        with self.assertRaises(InvalidIDLSyntaxError):
            load('@bit_bound(8 bitmask F { A };')


if __name__ == '__main__':
    unittest.main()
