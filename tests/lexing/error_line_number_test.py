"""A parse error reports the line number where it happened (invalid_idl.idl)."""
import os
import unittest
from idl_parser import parser
from idl_parser.exception import IDLParserException
from tests import support

idl_path = os.path.join(support.IDL_DIR, 'invalid_idl.idl')


class InvalidIDLTestFunctions(unittest.TestCase):
    """Category: Lexing, preprocessing and error line numbers / カテゴリ: 字句解析・前処理・エラー行番号

    A parse error reports the line number where it happened.
    解析エラーが発生した行番号を報告する。
    """

    def test_invalid_message(self):
        """The exception for an invalid IDL carries the error line number (line 10).

        不正な IDL の例外にエラー行番号(10行目)が入る。
        """
        parser_ = parser.IDLParser()
        with open(idl_path, 'r') as idlf:
            text = idlf.read()
        # Used to pass even when no exception was raised at all.
        with self.assertRaises(IDLParserException) as cm:
            parser_.load(text, filepath=idl_path)
        self.assertEqual(cm.exception.line_number, 10)


if __name__ == '__main__':
    unittest.main()
