"""Regression tests for issue #18 (IDL 4.2 integer types were rejected).

int8/int16/int32/int64 and uint8/uint16/uint32/uint64 used to raise
InvalidDataTypeException because they were not known primitive types.
"""
import os
import unittest
from idl_parser import parser, type as idl_type
from tests import support

IDL_DIR = support.IDL_DIR


INT_TYPES = ['int8', 'int16', 'int32', 'int64',
             'uint8', 'uint16', 'uint32', 'uint64']


def load(path):
    with open(path, 'r') as f:
        return parser.IDLParser().load(f.read())


class Issue18Test(unittest.TestCase):
    """Category: Primitive types and constants / カテゴリ: 基本型・定数

    IDL 4.2 integer types int8 … uint64 (issue #18).
    IDL 4.2 の整数型 int8〜uint64(#18)。
    """

    def setUp(self):
        self.m = load(os.path.join(IDL_DIR, 'issue18_idl42_int_types.idl')).module_by_name('Issue18')

    def test_is_primitive(self):
        """int8 … uint64 are primitive types.

        int8〜uint64 がプリミティブ型と判定される。
        """
        for t in INT_TYPES:
            self.assertTrue(idl_type.is_primitive(t), t)

    def test_struct_members(self):
        """Struct members of int8 … uint64, and sequence<int32>.

        int8〜uint64 の struct メンバーと sequence<int32>。
        """
        s = self.m.struct_by_name('AllIntTypes')
        expected = {
            'i8': 'int8', 'i16': 'int16', 'i32': 'int32', 'i64': 'int64',
            'u8': 'uint8', 'u16': 'uint16', 'u32': 'uint32', 'u64': 'uint64',
        }
        for name, typ in expected.items():
            t = s.member_by_name(name).type
            self.assertEqual(str(t), typ, name)
            self.assertTrue(t.is_primitive, name)

        self.assertEqual(str(s.member_by_name('int32_seq').type), 'sequence<int32>')
        self.assertEqual(str(s.member_by_name('u8_array').type), 'uint8[4]')

    def test_typedefs(self):
        """Typedefs of uint8 and int64.

        uint8/int64 の typedef。
        """
        self.assertEqual(str(self.m.typedef_by_name('ByteSeq').type), 'sequence<uint8>')
        stamp = self.m.typedef_by_name('Timestamp').type
        self.assertEqual(str(stamp), 'int64')
        self.assertTrue(stamp.is_primitive)

    def test_consts(self):
        """Consts of int32 and uint8.

        int32/uint8 の const。
        """
        consts = {c.name: (c.typename, c.value) for c in self.m.consts}
        self.assertEqual(consts, {
            'MAX_COUNT': ('int32', '10'),
            'FLAG': ('uint8', '1'),
        })

    def test_interface(self):
        """Return values and arguments of methods using the int types.

        int 型を使ったメソッドの戻り値・引数。
        """
        i = self.m.interface_by_name('IntService')
        add = i.method_by_name('add')
        self.assertEqual(str(add.returns), 'int64')
        self.assertEqual([(a.direction, str(a.type)) for a in add.arguments],
                         [('in', 'int32'), ('in', 'int32')])
        get = i.method_by_name('get')
        self.assertEqual([(a.direction, str(a.type)) for a in get.arguments],
                         [('out', 'uint16'), ('inout', 'uint32')])


if __name__ == '__main__':
    unittest.main()
