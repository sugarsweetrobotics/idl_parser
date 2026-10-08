"""Annotation arguments keep the spaces inside string literals (issue #52)."""
import unittest
from idl_parser import parser


def load(idl):
    return parser.IDLParser().load(idl)


class AnnotationStringWithSpacesTest(unittest.TestCase):

    def annotation(self, idl):
        g = load(idl)
        return g.module_by_name('M').struct_by_name('X').members[0].annotations[0]

    def test_param_keeps_spaces(self):
        a = self.annotation('module M { struct X { @verbatim(text="a  b c") long v; }; };')
        self.assertEqual(a.params, {'text': '"a  b c"'})

    def test_arg_keeps_spaces(self):
        a = self.annotation('module M { struct X { @doc("x   y") long v; }; };')
        self.assertEqual(a.args, ['"x   y"'])


if __name__ == '__main__':
    unittest.main()
