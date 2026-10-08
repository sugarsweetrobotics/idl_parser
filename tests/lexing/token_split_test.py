"""split_tokens(): string and char literals stay single tokens (issue #52)."""
import unittest
from idl_parser.token_buffer import split_tokens


class SplitTokensTest(unittest.TestCase):

    def test_plain(self):
        self.assertEqual(split_tokens('  long  x ;\n'), ['long', 'x', ';'])

    def test_string_literal_with_spaces(self):
        self.assertEqual(split_tokens('S = "hello  world" ;'),
                         ['S', '=', '"hello  world"', ';'])

    def test_char_literal_space(self):
        self.assertEqual(split_tokens("C = ' ' ;"), ['C', '=', "' '", ';'])

    def test_escaped_quote(self):
        self.assertEqual(split_tokens(r'S = "a \" b" ;'), ['S', '=', r'"a \" b"', ';'])

    def test_prefix_stays_with_literal(self):
        self.assertEqual(split_tokens('W = L"x y" ;'), ['W', '=', 'L"x y"', ';'])


if __name__ == '__main__':
    unittest.main()
