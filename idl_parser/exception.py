


class IDLParserException(Exception):

    def __init__(self, line_number=None, file_name=None, message='IDLParserException occurred.'):
        self._className = 'IDLParserException'
        self._line_number = line_number
        self._file_name = file_name
        self._message = message

    @property
    def message(self):
        return 'File "' + self.file_name + '", line %s, ' % self.line_number + '(' + self._className + '):"' + self._message

    @property
    def line_number(self):
        return self._line_number
        
    @property
    def file_name(self):
        return self._file_name



class InvalidIDLSyntaxError(IDLParserException):

    def __init__(self, line_number=None, file_name=None, message='IDLParserException occurred.'):
        super(InvalidIDLSyntaxError, self).__init__(line_number, file_name, message)
        self._className = 'InvalidIDLSyntaxError'
    pass

class InvalidDataTypeException(IDLParserException):
    pass

class IDLCanNotFindException(IDLParserException):
    pass
