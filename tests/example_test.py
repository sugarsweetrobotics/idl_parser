"""Keep example.py runnable on Python 3 and cover to_simple_dic(member_only=True)."""
import contextlib
import io
import unittest

import example
from idl_parser import parser


class ExampleTest(unittest.TestCase):

    def test_example_runs(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            example.test()
        text = out.getvalue()
        self.assertIn('DataGetter interface', text)
        self.assertIn('  name: getData', text)
        self.assertIn('    direction: out', text)
        self.assertIn('descriminator kind: UNION_DESCRIMINATOR_KIND', text)
        self.assertIn('TimedDoubleSeq', text)


class SimpleDicMemberOnlyTest(unittest.TestCase):

    def setUp(self):
        idl = '''
module M {
  enum K { A, B };
  struct S { long x; double y; };
  union U switch (K) { case A: long a; case B: double b; };
};
'''
        self.m = parser.IDLParser().load(idl).module_by_name('M')

    def test_struct_member_only(self):
        s = self.m.struct_by_name('S')
        self.assertEqual(list(s.to_simple_dic(member_only=True)),
                         [{'x': 'long'}, {'y': 'double'}])

    def test_union_member_only(self):
        u = self.m.union_by_name('U')
        # Must not raise TypeError ('dict_values' object is not subscriptable)
        self.assertEqual(len(list(u.to_simple_dic(member_only=True))), 2)


if __name__ == '__main__':
    unittest.main()
