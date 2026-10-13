"""Tests for issue #93: exception definitions.

"exception E { ... };" was skipped with an UnsupportedIDLSyntaxWarning, so
the members of an exception named in "raises (E)" could not be read. An
exception is now parsed like a struct (IDLException) and is listed in
IDLModule.exceptions; IDLMethod.exceptions resolves the names in
"raises (...)" to their definitions.
"""
import unittest
import warnings
from idl_parser import parser
from idl_parser.exception import (IDLCanNotFindException, IDLParserWarning,
                                  InvalidIDLSyntaxError)


IDL = '''
module M {
  struct Detail { long code; };
  exception E { string msg; };
  exception F { long x; Detail detail; sequence<long> values; };
  exception Empty { };
  module N { exception G { long y; }; };
  interface I {
    void f() raises (E);
    void g() raises (E, F, N::G);
    void h();
  };
  module N2 {
    exception E { double other; };
    interface J { void f() raises (E); void g() raises (::M::E); };
  };
};
'''


def load(idl):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        g = parser.IDLParser().load(idl)
    return g, [w for w in caught if issubclass(w.category, IDLParserWarning)]


class ExceptionTest(unittest.TestCase):
    """Category: Structs, enums and unions / カテゴリ: struct・enum・union

    exception definitions and raises (issue #93).
    exception の定義と raises(#93)。
    """

    @classmethod
    def setUpClass(cls):
        cls.g, cls.warnings = load(IDL)
        cls.m = cls.g.module_by_name('M')

    def test_no_warning(self):
        """An exception definition gives no UnsupportedIDLSyntaxWarning any more.

        exception の定義で UnsupportedIDLSyntaxWarning が出なくなる。
        """
        self.assertEqual(self.warnings, [])

    def test_exceptions_of_module(self):
        """Exceptions are listed in IDLModule.exceptions, in order.

        exception は IDLModule.exceptions に定義順で入る。
        """
        self.assertEqual([x.name for x in self.m.exceptions], ['E', 'F', 'Empty'])
        self.assertEqual(self.m.module_by_name('N').exception_by_name('G').full_path, 'M::N::G')
        self.assertIsNone(self.m.exception_by_name('G'))

    def test_members(self):
        """Members are read like struct members.

        メンバーは struct と同じように読める。
        """
        f = self.m.exception_by_name('F')
        self.assertEqual([(v.name, str(v.type)) for v in f.members],
                         [('x', 'long'), ('detail', 'Detail'), ('values', 'sequence<long>')])
        self.assertTrue(f.member_by_name('detail').type.is_struct)
        self.assertEqual(self.m.exception_by_name('Empty').members, [])

    def test_kind(self):
        """An exception is not a struct.

        exception は struct ではない。
        """
        e = self.m.exception_by_name('E')
        self.assertEqual(e.classname, 'IDLException')
        self.assertTrue(e.is_exception)
        self.assertFalse(e.is_struct)
        self.assertEqual([s.name for s in self.m.structs], ['Detail'])

    def test_not_a_type(self):
        """An exception is not found as a type by find_types().

        find_types() では exception は型として見つからない。
        """
        self.assertEqual(self.g.find_types('M::E'), [])
        self.assertEqual([x.full_path for x in self.g.find_exceptions('M::E')], ['M::E'])

    def test_raises_resolves_exceptions(self):
        """IDLMethod.exceptions gives the definitions named in raises (...).

        IDLMethod.exceptions で raises (...) の定義をたどれる。
        """
        i = self.m.interface_by_name('I')
        self.assertEqual([x.full_path for x in i.method_by_name('f').exceptions], ['M::E'])
        self.assertEqual([x.full_path for x in i.method_by_name('g').exceptions],
                         ['M::E', 'M::F', 'M::N::G'])
        self.assertEqual(i.method_by_name('h').exceptions, [])
        e = i.method_by_name('f').exceptions[0]
        self.assertEqual([(v.name, str(v.type)) for v in e.members], [('msg', 'string')])

    def test_raises_uses_scoping_rules(self):
        """A name in raises is looked up from the innermost scope first.

        raises の名前は内側のスコープから順に探す。
        """
        j = self.m.module_by_name('N2').interface_by_name('J')
        self.assertEqual([x.full_path for x in j.method_by_name('f').exceptions], ['M::N2::E'])
        self.assertEqual([x.full_path for x in j.method_by_name('g').exceptions], ['M::E'])

    def test_raises_unknown_exception(self):
        """An undefined name in raises gives IDLCanNotFindException.

        raises に未定義の名前があると IDLCanNotFindException になる。
        """
        g, _ = load('interface I { void f() raises (Nothing); };')
        method = g.interface_by_name('I').method_by_name('f')
        self.assertEqual(method.raises, ['Nothing'])
        with self.assertRaises(IDLCanNotFindException):
            method.exceptions

    def test_output(self):
        """to_simple_dic() and to_dic() include exceptions.

        to_simple_dic() と to_dic() に exception が入る。
        """
        g, _ = load('module M { exception E { string msg; }; };')
        self.assertEqual(g.to_simple_dic(),
                         {'module __global__': [{'module M': [{'exception E': [{'msg': 'string'}]}]}]})
        self.assertEqual(g.to_simple_dic(quiet=True),
                         {'module __global__': [{'module M': ['exception E']}]})
        dic = g.to_dic()['modules'][0]
        self.assertEqual(dic['exceptions'],
                         [{'name': 'E', 'classname': 'IDLException',
                           'members': [{'name': 'msg', 'filepath': None,
                                        'classname': 'IDLMember', 'type': 'string'}]}])
        self.assertEqual(g.to_dic()['exceptions'], [])

    def test_annotations(self):
        """Annotations before an exception are kept.

        exception の前の注釈が残る。
        """
        g, _ = load('@final exception E { string msg; };')
        self.assertTrue(g.exception_by_name('E').has_annotation('final'))

    def test_forward_declaration_is_an_error(self):
        """An exception can not be forward-declared.

        exception は前方宣言できない。
        """
        with self.assertRaises(InvalidIDLSyntaxError):
            parser.IDLParser().load('exception E;')

    def test_undefined_member_type(self):
        """A member of an undefined type is an error, as in a struct.

        struct と同じく、未定義の型のメンバーはエラーになる。
        """
        from idl_parser.exception import InvalidDataTypeException
        with self.assertRaises(InvalidDataTypeException):
            parser.IDLParser().load('exception E { Unknown u; };')


if __name__ == '__main__':
    unittest.main()
