"""split_tokens(): string and char literals stay single tokens (issue #52)."""
import unittest
from idl_parser.token_buffer import split_tokens


class SplitTokensTest(unittest.TestCase):
    """Category: Lexing, preprocessing and error line numbers / カテゴリ: 字句解析・前処理・エラー行番号

    split_tokens() keeps string and char literals as single tokens (issue #52).
    split_tokens() が文字列・文字リテラルを1トークンに保つ(#52)。
    """

    def test_plain(self):
        """split_tokens(): plain whitespace-separated tokens.

        split_tokens(): 通常の空白区切り。
        """
        self.assertEqual(split_tokens('  long  x ;\n'), ['long', 'x', ';'])

    def test_string_literal_with_spaces(self):
        """split_tokens(): a string literal with spaces stays one token.

        split_tokens(): 空白を含む文字列リテラルを1トークンに保つ。
        """
        self.assertEqual(split_tokens('S = "hello  world" ;'),
                         ['S', '=', '"hello  world"', ';'])

    def test_char_literal_space(self):
        """split_tokens(): the char literal ' '.

        split_tokens(): ' ' の文字リテラル。
        """
        self.assertEqual(split_tokens("C = ' ' ;"), ['C', '=', "' '", ';'])

    def test_escaped_quote(self):
        """split_tokens(): a string with an escaped ".

        split_tokens(): エスケープした " を含む文字列。
        """
        self.assertEqual(split_tokens(r'S = "a \" b" ;'), ['S', '=', r'"a \" b"', ';'])

    def test_prefix_stays_with_literal(self):
        """split_tokens(): the L prefix of L"..." stays with the literal.

        split_tokens(): L"..." の接頭辞がリテラルと分かれない。
        """
        self.assertEqual(split_tokens('W = L"x y" ;'), ['W', '=', 'L"x y"', ';'])


if __name__ == '__main__':
    unittest.main()
