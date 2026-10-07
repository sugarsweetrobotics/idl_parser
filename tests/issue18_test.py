"""Regression tests for issue #18 (IDL 4.2 integer types were rejected).

int8/int16/int32/int64 and uint8/uint16/uint32/uint64 used to raise
InvalidDataTypeException because they were not known primitive types.
"""
import unittest
from idl_parser import parser, type as idl_type


INT_TYPES = ['int8', 'int16', 'int32', 'int64',
             'uint8', 'uint16', 'uint32', 'uint64']


def load(path):
    with open(path, 'r') as f:
        return parser.IDLParser().load(f.read())


class Issue18Test(unittest.TestCase):

    def setUp(self):
        self.m = load('idls/issue18_idl42_int_types.idl').module_by_name('Issue18')

    def test_is_primitive(self):
        for t in INT_TYPES:
            self.assertTrue(idl_type.is_primitive(t), t)

    def test_struct_members(self):
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
        self.assertEqual(str(self.m.typedef_by_name('ByteSeq').type), 'sequence<uint8>')
        stamp = self.m.typedef_by_name('Timestamp').type
        self.assertEqual(str(stamp), 'int64')
        self.assertTrue(stamp.is_primitive)

    def test_consts(self):
        consts = {c.name: (c.typename, c.value) for c in self.m.consts}
        self.assertEqual(consts, {
            'MAX_COUNT': ('int32', '10'),
            'FLAG': ('uint8', '1'),
        })

    def test_interface(self):
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
