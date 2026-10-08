"""Annotation arguments keep the spaces inside string literals (issue #52)."""
import unittest
from idl_parser import parser


def load(idl):
    return parser.IDLParser().load(idl)


class AnnotationStringWithSpacesTest(unittest.TestCase):
    """Category: Annotations / カテゴリ: アノテーション

    Annotation arguments keep the spaces inside string literals (issue #52).
    アノテーション引数の文字列リテラル内の空白が保持される(#52)。
    """

    def annotation(self, idl):
        g = load(idl)
        return g.module_by_name('M').struct_by_name('X').members[0].annotations[0]

    def test_param_keeps_spaces(self):
        """Spaces inside a string in a named annotation argument are kept.

        アノテーションの名前付き引数の文字列内の空白が保持される。
        """
        a = self.annotation('module M { struct X { @verbatim(text="a  b c") long v; }; };')
        self.assertEqual(a.params, {'text': '"a  b c"'})

    def test_arg_keeps_spaces(self):
        """Spaces inside a string in a positional annotation argument are kept.

        アノテーションの位置引数の文字列内の空白が保持される。
        """
        a = self.annotation('module M { struct X { @doc("x   y") long v; }; };')
        self.assertEqual(a.args, ['"x   y"'])


if __name__ == '__main__':
    unittest.main()
