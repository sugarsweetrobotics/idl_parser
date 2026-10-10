"""The text of a parse exception (message / str), with or without the file name and line number (#80)."""
import unittest
from idl_parser import exception


class ExceptionMessageTestFunctions(unittest.TestCase):
    """Category: Lexing, preprocessing and error line numbers / カテゴリ: 字句解析・前処理・エラー行番号

    The text of a parse exception can always be built, even when the file name
    or line number is not known.
    ファイル名や行番号が分からない例外でも、メッセージを組み立てられる。
    """

    def test_message_with_file_and_line(self):
        """With a file name and line number, the message names both.

        ファイル名と行番号があれば、メッセージに両方が入る。
        """
        e = exception.InvalidIDLSyntaxError(3, 'a.idl', 'x')
        self.assertEqual(e.message, 'File "a.idl", line 3, (InvalidIDLSyntaxError):"x"')

    def test_message_without_file_and_line(self):
        """Without a file name and line number, those parts are left out (no TypeError).

        ファイル名と行番号がなければ、その部分を省く（TypeError にならない）。
        """
        e = exception.InvalidIDLSyntaxError(message='x')
        self.assertEqual(e.message, '(InvalidIDLSyntaxError):"x"')

    def test_message_without_file(self):
        """Without a file name, only the line number is shown.

        ファイル名がなければ、行番号だけを表示する。
        """
        e = exception.InvalidIDLSyntaxError(5, None, 'x')
        self.assertEqual(e.message, 'line 5, (InvalidIDLSyntaxError):"x"')

    def test_message_without_line(self):
        """Without a line number, only the file name is shown.

        行番号がなければ、ファイル名だけを表示する。
        """
        e = exception.InvalidIDLSyntaxError(None, 'a.idl', 'x')
        self.assertEqual(e.message, 'File "a.idl", (InvalidIDLSyntaxError):"x"')

    def test_message_line_zero(self):
        """Line number 0 is kept, not treated as unknown.

        行番号 0 は「不明」扱いにせず表示する。
        """
        e = exception.InvalidIDLSyntaxError(0, 'a.idl', 'x')
        self.assertEqual(e.message, 'File "a.idl", line 0, (InvalidIDLSyntaxError):"x"')

    def test_message_none(self):
        """A None message gives an empty description (no TypeError).

        メッセージが None でも空の説明になる（TypeError にならない）。
        """
        e = exception.InvalidIDLSyntaxError(message=None)
        self.assertEqual(e.message, '(InvalidIDLSyntaxError):""')

    def test_default_message(self):
        """Raised with no arguments, the default description is used.

        引数なしで作ると、既定の説明になる。
        """
        e = exception.InvalidIDLSyntaxError()
        self.assertEqual(e.message, '(InvalidIDLSyntaxError):"IDLParserException occurred."')

    def test_class_name(self):
        """Each exception class shows its own name.

        各例外クラスは自分のクラス名を表示する。
        """
        for cls in (exception.IDLParserException,
                    exception.InvalidIDLSyntaxError,
                    exception.InvalidDataTypeException,
                    exception.IDLCanNotFindException):
            with self.subTest(cls=cls.__name__):
                e = cls(message='x')
                self.assertEqual(e.message, '(%s):"x"' % cls.__name__)

    def test_str(self):
        """str() of the exception is the same text as message.

        例外の str() は message と同じ文字列になる。
        """
        e = exception.IDLCanNotFindException(7, 'b.idl', 'not found')
        self.assertEqual(str(e), 'File "b.idl", line 7, (IDLCanNotFindException):"not found"')
        self.assertEqual(str(e), e.message)
        self.assertEqual(str(exception.InvalidIDLSyntaxError(message='x')), '(InvalidIDLSyntaxError):"x"')

    def test_line_number_and_file_name(self):
        """line_number and file_name are kept as given.

        line_number と file_name は渡した値のまま保持される。
        """
        e = exception.InvalidDataTypeException(4, 'c.idl', 'x')
        self.assertEqual(e.line_number, 4)
        self.assertEqual(e.file_name, 'c.idl')

    def test_raise_and_catch(self):
        """A subclass can be caught as IDLParserException and its text read.

        サブクラスは IDLParserException として捕捉でき、文字列を取り出せる。
        """
        with self.assertRaises(exception.IDLParserException) as cm:
            raise exception.InvalidIDLSyntaxError()
        self.assertIn('InvalidIDLSyntaxError', str(cm.exception))


if __name__ == '__main__':
    unittest.main()
