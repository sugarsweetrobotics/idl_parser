"""Return types of operations written in several words (issue #159).

``unsigned short``, ``long long`` and the like were split so that the
second word was taken as the name of the operation.  The name is now the
token just before ``(``, and every word before it is the return type.
"""
import unittest
from idl_parser import parser, exception


MULTIWORD = ['unsigned short', 'unsigned long', 'long long',
             'unsigned long long', 'long double']

IDL = '''
module M {
  interface I {
    unsigned short op_us(in unsigned short v);
    unsigned long op_ul(in unsigned long v);
    long long op_ll(in long long v);
    unsigned long long op_ull(in unsigned long long v);
    long double op_ld(in long double v);
    @deprecated unsigned long op_annotated();
    sequence<long, 10> op_seq();
    long op_single(in long v);
  };
};
'''


def method(g, name):
    return g.module_by_name('M').interface_by_name('I').method_by_name(name)


class MultiwordReturnTypeTest(unittest.TestCase):
    """Category: Interfaces, operations and inheritance / カテゴリ: interface・operation・継承

    Multi-word return types of operations.
    複数語からなるオペレーションの戻り値の型。
    """

    @classmethod
    def setUpClass(cls):
        cls.g = parser.IDLParser().load(IDL)

    def test_multiword_primitive_returns(self):
        """Each multi-word primitive is read as the return type, and the name after it as the name.

        複数語の基本型が戻り値の型になり、その後ろの語が名前になる。
        """
        names = ['op_us', 'op_ul', 'op_ll', 'op_ull', 'op_ld']
        for name, typ in zip(names, MULTIWORD):
            with self.subTest(name=name):
                m = method(self.g, name)
                self.assertEqual(m.name, name)
                self.assertEqual(str(m.returns), typ)
                self.assertTrue(m.returns.is_primitive)
                self.assertEqual([(a.name, str(a.type)) for a in m.arguments], [('v', typ)])

    def test_after_annotation(self):
        """An annotation before the operation does not change how the return type is read.

        アノテーションが前にあっても戻り値の型は同じように読まれる。
        """
        m = method(self.g, 'op_annotated')
        self.assertEqual(str(m.returns), 'unsigned long')
        self.assertEqual(m.arguments, [])

    def test_bounded_sequence_return(self):
        """A bounded sequence (with "," inside "< >") can be a return type.

        上限付き sequence（"< >" の中に "," がある）も戻り値の型になる。
        """
        m = method(self.g, 'op_seq')
        self.assertTrue(m.returns.is_sequence)
        self.assertEqual(m.returns.bound, 10)

    def test_single_word_return(self):
        """A one-word return type is read as before.

        1語の戻り値の型はこれまでどおり読まれる。
        """
        m = method(self.g, 'op_single')
        self.assertEqual((m.name, str(m.returns)), ('op_single', 'long'))

    def test_to_dic(self):
        """to_dic() and to_simple_dic() show the whole return type.

        to_dic() と to_simple_dic() に戻り値の型全体が出る。
        """
        m = method(self.g, 'op_ull')
        self.assertEqual(m.to_dic()['returns'], 'unsigned long long')
        self.assertEqual(m.to_simple_dic()['op_ull']['returns'], 'unsigned long long')

    def test_oneway_multiword_return_is_rejected(self):
        """A oneway operation must still return void, and the message names the whole type.

        oneway は引き続き void 以外を返せず、エラーには型全体が出る。
        """
        idl = 'interface J { oneway unsigned long f(); };'
        with self.assertRaises(exception.InvalidIDLSyntaxError) as cm:
            parser.IDLParser().load(idl)
        self.assertIn('unsigned long', str(cm.exception))
        self.assertIn('"f"', str(cm.exception))

    def test_oneway_void(self):
        """A oneway void operation after an annotation is read with its name.

        アノテーション付きの oneway void も名前が正しく読まれる。
        """
        g = parser.IDLParser().load('interface J { @a oneway void f(in unsigned short v); };')
        m = g.interface_by_name('J').method_by_name('f')
        self.assertTrue(m.oneway)
        self.assertEqual(str(m.returns), 'void')

    def test_keyword_as_name_still_rejected(self):
        """A keyword just before "(" is still rejected as a name (issue #119).

        "(" の直前のキーワードは引き続き名前として拒否される。
        """
        with self.assertRaises(exception.InvalidIDLSyntaxError):
            parser.IDLParser().load('interface J { unsigned long long(); };')


if __name__ == '__main__':
    unittest.main()
