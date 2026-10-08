"""IDLSequence / IDLArray built from a name that is not a sequence / array
raise InvalidIDLSyntaxError (it used to be NameError).
"""
import unittest
from idl_parser import parser, type as idl_type
from idl_parser.exception import InvalidIDLSyntaxError


class SyntaxErrorTest(unittest.TestCase):

    def test_invalid_sequence_and_array_names(self):
        g = parser.IDLParser().load('module M { struct S { long x; }; };')
        with self.assertRaises(InvalidIDLSyntaxError):
            idl_type.IDLSequence('long', g)
        with self.assertRaises(InvalidIDLSyntaxError):
            idl_type.IDLArray('long', g)


if __name__ == '__main__':
    unittest.main()
