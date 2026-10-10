"""Exceptions raised while parsing."""



class IDLParserException(Exception):
    """Base class of the exceptions of idl_parser.

    :param line_number: Line where the error was found, if known.
    :param file_name: File where the error was found, if known.
    :param message: Description of the error.
    """
    def __init__(self, line_number=None, file_name=None, message='IDLParserException occurred.'):
        super(IDLParserException, self).__init__(message)
        self._className = type(self).__name__
        self._line_number = line_number
        self._file_name = file_name
        self._message = message

    @property
    def message(self):
        """The message with the file name, line number and exception class:
        ``File "a.idl", line 3, (InvalidIDLSyntaxError):"..."``.

        The file name and the line number are left out when they are not known.
        """
        text = ''
        if self.file_name is not None:
            text += 'File "%s", ' % self.file_name
        if self.line_number is not None:
            text += 'line %s, ' % self.line_number
        return text + '(%s):"%s"' % (self._className, '' if self._message is None else self._message)

    def __str__(self):
        return self.message

    @property
    def line_number(self):
        """Line where the error was found, or None."""
        return self._line_number

    @property
    def file_name(self):
        """File where the error was found, or None."""
        return self._file_name



class InvalidIDLSyntaxError(IDLParserException):
    """The input is not valid IDL (a missing ``{``, ``;``, ...)."""
    pass

class InvalidDataTypeException(IDLParserException):
    """A type name does not name a defined type, or an array size is not an integer."""
    pass

class IDLCanNotFindException(IDLParserException):
    """An ``#include`` file or a base interface / bitset can not be found."""
    pass
