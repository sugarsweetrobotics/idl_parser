"""Regression tests for issue #91.

IDLNode.pathname checked ``name.find('::') > 0``, so a name with a leading
"::" ('::A::B') returned '' even when it had a scope part. Like basename
(issue #81), it now drops the leading "::" first.
"""
import unittest
from idl_parser.node import IDLNode


def pathname(name):
    return IDLNode('IDLNode', name, None).pathname


class PathnameTest(unittest.TestCase):
    """Category: Scopes / カテゴリ: スコープ

    IDLNode.pathname returns the scope part of a scoped name.
    IDLNode.pathname はスコープ付きの名前のスコープ部分を返す。
    """

    def test_plain_name(self):
        """A name without scope has no scope part. / スコープのない名前は ''。"""
        self.assertEqual(pathname('A'), '')

    def test_scoped_name(self):
        """'A::B' -> 'A'."""
        self.assertEqual(pathname('A::B'), 'A')
        self.assertEqual(pathname('A::B::C'), 'A::B')

    def test_leading_scope(self):
        """A leading '::' is dropped: '::A::B' -> 'A'. / 先頭の '::' は落とす。"""
        self.assertEqual(pathname('::A'), '')
        self.assertEqual(pathname('::A::B'), 'A')
        self.assertEqual(pathname('::A::B::C'), 'A::B')


if __name__ == '__main__':
    unittest.main()
