"""Malformed enum / union definitions must raise InvalidIDLSyntaxError.

These error paths used to raise NameError instead, because
InvalidIDLSyntaxError was not imported in enum.py, union.py and type.py.
No existing test reached them, since the test IDLs are all valid.
"""
import unittest
from idl_parser import parser
from idl_parser.exception import InvalidIDLSyntaxError


INVALID_IDLS = {
    'enum without "{"': 'enum E A, B };',
    'enum without "}"': 'enum E { A, B ;',
    'enum without ";" after "}"': 'enum E { A } struct S { long x; };',
    'union without "switch"': 'union U long',
    'union without "("': 'union U switch long',
    'union without ")"': 'union U switch ( long ] {',
    'union without "{"': 'union U switch ( long ) case',
    'union without "}"': 'union U switch ( long ) { case 1 : long a ;',
    'union without ";" after "}"': 'union U switch ( long ) { case 1 : long a ; } struct',
}


class SyntaxErrorTest(unittest.TestCase):
    """Category: Structs, enums and unions / カテゴリ: struct・enum・union

    Malformed enum / union definitions raise InvalidIDLSyntaxError.
    不正な enum/union 定義は InvalidIDLSyntaxError になる。
    """

    def test_invalid_enum_and_union(self):
        """Malformed enum / union definitions raise InvalidIDLSyntaxError (not NameError).

        不正な enum/union 定義で(NameError でなく)InvalidIDLSyntaxError。
        """
        for label, idl in INVALID_IDLS.items():
            with self.subTest(label):
                with self.assertRaises(InvalidIDLSyntaxError):
                    parser.IDLParser().load(idl)


if __name__ == '__main__':
    unittest.main()
