"""Regression tests for issue #49.

A union case label written as a character literal (``case 'a':``) was not
split from its ":", so loading failed with InvalidDataTypeException.
"""
import unittest
from idl_parser import parser


def load(idl):
    return parser.IDLParser().load(idl)


def labels(union):
    return [m.descriminator_value_associations for m in union.members]


class Issue49Test(unittest.TestCase):

    def test_char_literal_case_labels(self):
        g = load('''module M {
  union W switch (char) {
    case 'a': long x;
    case 'b': octet o;
  };
};''')
        u = g.module_by_name('M').union_by_name('W')
        self.assertEqual(labels(u), [["'a'"], ["'b'"]])
        self.assertEqual([m.name for m in u.members], ['x', 'o'])

    def test_symbols_and_escapes_in_char_literal(self):
        g = load(r'''module M {
  union W switch (char) {
    case ':': long colon;
    case '\n': long newline;
    case '\'': long quote;
    case '\\': long backslash;
    case ';': long semicolon;
    case '/': long slash;
  };
};''')
        u = g.module_by_name('M').union_by_name('W')
        self.assertEqual(labels(u), [["':'"], [r"'\n'"], [r"'\''"],
                                     [r"'\\'"], ["';'"], ["'/'"]])
        self.assertEqual([m.name for m in u.members],
                         ['colon', 'newline', 'quote', 'backslash', 'semicolon', 'slash'])

    def test_wide_char_literal(self):
        g = load('''module M {
  union V switch (wchar) {
    case L'a': long x;
    default: short y;
  };
};''')
        u = g.module_by_name('M').union_by_name('V')
        self.assertEqual(labels(u)[0], ["L'a'"])

    def test_space_before_colon_and_several_labels(self):
        g = load('''module M {
  union W switch (char) {
    case 'a' : case 'b':
      long x;
  };
};''')
        u = g.module_by_name('M').union_by_name('W')
        self.assertEqual(labels(u), [["'a'", "'b'"]])

    def test_other_labels_still_work(self):
        g = load('''module M {
  enum E { A, B };
  union U switch (E) { case M::A: long a; case B: long b; };
  union N switch (long) { case -1: long m; case 2: long p; };
};''')
        m = g.module_by_name('M')
        self.assertEqual(labels(m.union_by_name('U')), [['M::A'], ['B']])
        self.assertEqual(labels(m.union_by_name('N')), [['-1'], ['2']])


if __name__ == '__main__':
    unittest.main()
