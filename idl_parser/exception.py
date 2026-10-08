"""Exceptions raised while parsing."""



class IDLParserException(Exception):
    """Base class of the exceptions of idl_parser.

    :param line_number: Line where the error was found, if known.
    :param file_name: File where the error was found, if known.
    :param message: Description of the error.
    """
    def __init__(self, line_number=None, file_name=None, message='IDLParserException occurred.'):
        self._className = 'IDLParserException'
        self._line_number = line_number
        self._file_name = file_name
        self._message = message

    @property
    def message(self):
        """The message with the file name, line number and exception class:
        ``File "a.idl", line 3, (InvalidIDLSyntaxError):"...``.
        """
        return 'File "' + self.file_name + '", line %s, ' % self.line_number + '(' + self._className + '):"' + self._message

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
    def __init__(self, line_number=None, file_name=None, message='IDLParserException occurred.'):
        super(InvalidIDLSyntaxError, self).__init__(line_number, file_name, message)
        self._className = 'InvalidIDLSyntaxError'
    pass

class InvalidDataTypeException(IDLParserException):
    """A type name does not name a defined type, or an array size is not an integer."""
    pass

class IDLCanNotFindException(IDLParserException):
    """An ``#include`` file or a base interface / bitset can not be found."""
    pass
