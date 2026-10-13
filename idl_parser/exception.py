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


class IDLParserWarning(UserWarning):
    """Base class of the warnings of idl_parser."""
    pass

class UnknownIDLSyntaxWarning(IDLParserWarning):
    """A word that starts no known definition was found in a module or the
    global scope (a misspelled keyword such as ``strcut``), and the definition
    it starts was skipped (issue #76).

    This will become an :class:`InvalidIDLSyntaxError` in a future release.
    To get the error now, turn the warning into an exception::

        warnings.simplefilter('error', UnknownIDLSyntaxWarning)
    """
    pass

class UnsupportedIDLSyntaxWarning(IDLParserWarning):
    """A valid IDL definition that idl_parser does not support yet
    (``exception``, ``valuetype``, ``component``, ...) was skipped (issue #76)."""
    pass
