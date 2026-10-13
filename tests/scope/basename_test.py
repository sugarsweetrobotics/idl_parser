"""Regression tests for issue #81.

IDLNode.basename was defined twice, and the second definition returned
names with a leading "::" ('::A') unchanged. It now returns the last part
of the name in every case.
"""
import unittest
from idl_parser.node import IDLNode


def basename(name):
    return IDLNode('IDLNode', name, None).basename


class BasenameTest(unittest.TestCase):
    """Category: Scopes / カテゴリ: スコープ

    IDLNode.basename returns the last part of a scoped name.
    IDLNode.basename はスコープ付きの名前の最後の部分を返す。
    """

    def test_plain_name(self):
        """A name without scope is returned as is. / スコープのない名前はそのまま。"""
        self.assertEqual(basename('A'), 'A')

    def test_scoped_name(self):
        """'A::B' -> 'B'."""
        self.assertEqual(basename('A::B'), 'B')
        self.assertEqual(basename('A::B::C'), 'C')

    def test_leading_scope(self):
        """A leading '::' is dropped: '::A' -> 'A'. / 先頭の '::' は落とす。"""
        self.assertEqual(basename('::A'), 'A')
        self.assertEqual(basename('::A::B'), 'B')


if __name__ == '__main__':
    unittest.main()
