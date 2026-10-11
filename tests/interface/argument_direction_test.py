"""Directions of operation arguments (in / out / inout).

The basic parsing of each direction is checked in basic_module_test.py.
These tests cover what it does not: an argument written without a
direction is ``in``, and the direction appears in ``to_dic()`` and
``to_simple_dic()``.
"""
import unittest
from idl_parser import parser


IDL = '''
module M {
  struct S { long x; };
  interface I {
    void f(long a, in long b, out double c, inout S d);
    void g(S s, sequence<long> seq);
  };
};
'''


def method(g, name):
    return g.module_by_name('M').interface_by_name('I').method_by_name(name)


class ArgumentDirectionTest(unittest.TestCase):
    """Category: Interfaces, operations and inheritance / カテゴリ: interface・operation・継承

    Directions of operation arguments.
    オペレーション引数の向き(in/out/inout)。
    """

    @classmethod
    def setUpClass(cls):
        cls.g = parser.IDLParser().load(IDL)

    def test_each_direction(self):
        """Each argument has the direction written before it.

        各引数に書かれた向きが direction になる。
        """
        f = method(self.g, 'f')
        self.assertEqual([(a.name, a.direction) for a in f.arguments],
                         [('a', 'in'), ('b', 'in'), ('c', 'out'), ('d', 'inout')])

    def test_omitted_direction_is_in(self):
        """An argument without a direction is 'in', and its type and name are read correctly.

        向きを省略した引数は 'in' になり、型と名前も正しく読まれる。
        """
        g = method(self.g, 'g')
        self.assertEqual([(a.direction, a.type.name, a.name) for a in g.arguments],
                         [('in', 'S', 's'), ('in', 'sequence<long>', 'seq')])
        self.assertEqual(g.argument_by_name('s').type.obj.full_path, 'M::S')

    def test_to_dic(self):
        """to_dic() has the direction of each argument.

        to_dic() に各引数の向きが含まれる。
        """
        dic = method(self.g, 'f').to_dic()
        self.assertEqual([(a['name'], a['direction']) for a in dic['arguments']],
                         [('a', 'in'), ('b', 'in'), ('c', 'out'), ('d', 'inout')])

    def test_to_simple_dic(self):
        """to_simple_dic() writes each argument as 'direction type name'.

        to_simple_dic() は各引数を 'direction type name' の形で出力する。
        """
        dic = method(self.g, 'f').to_simple_dic()
        self.assertEqual(dic['f']['params'],
                         ['in long a', 'in long b', 'out double c', 'inout S d'])


if __name__ == '__main__':
    unittest.main()
