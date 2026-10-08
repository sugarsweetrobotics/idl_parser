"""Regression tests for issue #9 (OpenSplice-style IDL failed to parse).

The IDL files are taken from the issue and intentionally keep their
tab characters.
"""
import os
import unittest
from idl_parser import parser
from tests import support

IDL_DIR = support.IDL_DIR


def load(path):
    with open(path, 'r') as f:
        return parser.IDLParser().load(f.read())


class Issue9Test(unittest.TestCase):
    """Category: Lexing, preprocessing and error line numbers / カテゴリ: 字句解析・前処理・エラー行番号

    OpenSplice-style IDL files from issue #9 (tabs and spacing variants).
    issue #9 の OpenSplice 形式の IDL(タブや空白の表記揺れ)。
    """

    def test_tabs_and_bounded_string(self):
        """OpenSplice-style IDL with tabs, bounded strings and arrays.

        タブ区切り・上限付き string・配列を含む OpenSplice 形式の IDL。
        """
        g = load(os.path.join(IDL_DIR, 'issue9_tabs_bounded_string.idl'))
        s = g.module_by_name('Test').struct_by_name('arrays_8dd2d413')
        self.assertEqual(len(s.members), 20)

        expected = {
            'TestID': 'long',
            'private_revCode': 'string',
            'char0': 'string',
            'longLong0': 'long long[5]',
            'unsignedShort0': 'unsigned short[5]',
            'unsignedLong0': 'unsigned long[5]',
            'double0': 'double[5]',
        }
        for name, typ in expected.items():
            self.assertEqual(str(s.member_by_name(name).type), typ, name)

        rev = s.member_by_name('private_revCode').type
        self.assertTrue(rev.is_primitive)
        self.assertTrue(rev.is_bounded_string)
        self.assertEqual(rev.bound, 8)

        char0 = s.member_by_name('char0').type
        self.assertFalse(char0.is_bounded_string)
        self.assertIsNone(char0.bound)

    def test_const_without_spaces_and_pragma(self):
        """OpenSplice-style IDL with consts written without spaces and #pragma.

        空白なしの const と #pragma を含む OpenSplice 形式の IDL。
        """
        g = load(os.path.join(IDL_DIR, 'issue9_const_pragma.idl'))
        self.assertEqual([st.name for st in g.structs],
                         ['logevent_heartbeat_407c55f4', 'logevent_logLevel_df5f83b3'])
        consts = {c.name: (c.typename, c.value) for c in g.consts}
        self.assertEqual(consts, {
            'Watcher_shared_AlarmSeverity_None': ('long', '1'),
            'Watcher_shared_AlarmSeverity_Warning': ('long', '2'),
            'Watcher_shared_AlarmSeverity_Serious': ('long', '3'),
            'Watcher_shared_AlarmSeverity_Critical': ('long', '4'),
        })

    def test_whitespace_variants(self):
        """Consts, typedefs and others written with different spacing.

        空白の入れ方が異なる const/typedef などの表記揺れ。
        """
        g = load(os.path.join(IDL_DIR, 'issue9_whitespace_variants.idl'))
        self.assertEqual(g.const_by_name('MAXLEN').value, '16')

        e = g.module_by_name('E')
        self.assertEqual([(c.name, c.value) for c in e.consts],
                         [('A', '1'), ('B', '2'), ('C', '3')])

        name8 = e.typedef_by_name('Name8').type
        self.assertEqual(name8.name, 'string')
        self.assertEqual(name8.bound, 8)
        # A bound given by a constant name is kept as written
        self.assertEqual(e.typedef_by_name('WName').type.name, 'wstring')
        self.assertEqual(e.typedef_by_name('WName').type.bound, 'MAXLEN')

        s = e.struct_by_name('S')
        # Bounded strings keep the base type name; the bound is separate.
        # Spaces as in 'string <4>' do not matter.
        a = s.member_by_name('a').type
        self.assertEqual(a.name, 'string')
        self.assertEqual(a.bound, 4)
        arr = s.member_by_name('arr').type
        self.assertEqual(arr.size, 3)
        self.assertEqual(arr.inner_type.name, 'string')
        self.assertEqual(arr.inner_type.bound, 2)
        self.assertEqual(str(arr), 'string[3]')

        op = e.interface_by_name('I').method_by_name('op')
        self.assertEqual((op.returns.name, op.returns.bound), ('string', 8))
        self.assertEqual([(a.direction, a.type.name, a.type.bound, a.name) for a in op.arguments],
                         [('in', 'string', 4, 'x'), ('out', 'long', None, 'y')])

        self.assertEqual([v.name for v in e.enum_by_name('Color').values],
                         ['RED', 'GREEN'])


if __name__ == '__main__':
    unittest.main()
