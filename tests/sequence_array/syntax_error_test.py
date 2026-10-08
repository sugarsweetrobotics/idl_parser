"""IDLSequence / IDLArray built from a name that is not a sequence / array
raise InvalidIDLSyntaxError (it used to be NameError).
"""
import unittest
from idl_parser import parser, type as idl_type
from idl_parser.exception import InvalidIDLSyntaxError


class SyntaxErrorTest(unittest.TestCase):
    """Category: Sequences, arrays and typedefs / カテゴリ: sequence・array・typedef

    IDLSequence / IDLArray from invalid names raise InvalidIDLSyntaxError.
    不正な名前からの IDLSequence/IDLArray は InvalidIDLSyntaxError になる。
    """

    def test_invalid_sequence_and_array_names(self):
        """IDLSequence / IDLArray built from a non-sequence / non-array name raise an error.

        sequence/array でない名前から IDLSequence/IDLArray を作るとエラー。
        """
        g = parser.IDLParser().load('module M { struct S { long x; }; };')
        with self.assertRaises(InvalidIDLSyntaxError):
            idl_type.IDLSequence('long', g)
        with self.assertRaises(InvalidIDLSyntaxError):
            idl_type.IDLArray('long', g)


if __name__ == '__main__':
    unittest.main()
