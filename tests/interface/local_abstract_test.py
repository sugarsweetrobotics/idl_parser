"""Tests for issue #93: "local interface" and "abstract interface".

The "local" and "abstract" modifiers were dropped, so IDLInterface did not
tell a local or abstract interface from a plain one. They are now kept as
IDLInterface.is_local and IDLInterface.is_abstract. Annotations written
before the modifier ("@a local interface I") were lost too, and now apply
to the interface.
"""
import unittest
import warnings
from idl_parser import parser
from idl_parser.exception import IDLParserWarning


IDL = '''
module M {
  interface Plain { void f(); };
  local interface Local { void f(); };
  abstract interface Abstract { void f(); };
  local interface Derived : Plain { void g(); };
  @service("x") local interface Annotated { void f(); };
  local interface Forward;
  local interface Forward { void f(); };
};
'''


def load(idl):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        g = parser.IDLParser().load(idl)
    return g, [w for w in caught if issubclass(w.category, IDLParserWarning)]


class LocalAbstractInterfaceTest(unittest.TestCase):
    """Category: Interfaces, operations and inheritance / カテゴリ: interface・operation・継承

    local and abstract interfaces (issue #93).
    local / abstract interface(#93)。
    """

    @classmethod
    def setUpClass(cls):
        cls.g, cls.warnings = load(IDL)
        cls.m = cls.g.module_by_name('M')

    def flags(self, name):
        i = self.m.interface_by_name(name)
        return (i.is_local, i.is_abstract)

    def test_no_warning(self):
        """The modifiers give no warning.

        修飾子で警告は出ない。
        """
        self.assertEqual(self.warnings, [])

    def test_flags(self):
        """is_local and is_abstract tell the modifier.

        is_local と is_abstract で修飾子がわかる。
        """
        self.assertEqual(self.flags('Plain'), (False, False))
        self.assertEqual(self.flags('Local'), (True, False))
        self.assertEqual(self.flags('Abstract'), (False, True))
        self.assertEqual(self.flags('Derived'), (True, False))
        self.assertEqual(self.flags('Forward'), (True, False))

    def test_interfaces_are_parsed(self):
        """The interfaces after the modifiers are parsed as before.

        修飾子の後ろの interface はこれまでどおり解析される。
        """
        self.assertEqual([i.name for i in self.m.interfaces],
                         ['Plain', 'Local', 'Abstract', 'Derived', 'Annotated', 'Forward'])
        self.assertEqual([b.name for b in self.m.interface_by_name('Derived').inheritances], ['Plain'])

    def test_annotation_before_modifier(self):
        """An annotation before "local" applies to the interface.

        "local" の前の注釈が interface に付く。
        """
        i = self.m.interface_by_name('Annotated')
        self.assertTrue(i.is_local)
        self.assertEqual(i.annotation_by_name('service').value, '"x"')

    def test_to_dic(self):
        """to_dic() has 'local' / 'abstract' only when they are written.

        to_dic() の 'local' / 'abstract' は書かれたときだけ入る。
        """
        self.assertNotIn('local', self.m.interface_by_name('Plain').to_dic())
        self.assertNotIn('abstract', self.m.interface_by_name('Plain').to_dic())
        self.assertIs(self.m.interface_by_name('Local').to_dic()['local'], True)
        self.assertNotIn('abstract', self.m.interface_by_name('Local').to_dic())
        self.assertIs(self.m.interface_by_name('Abstract').to_dic()['abstract'], True)

    def test_modifier_does_not_leak(self):
        """A modifier applies only to the next definition.

        修飾子は直後の定義にだけ付く。
        """
        g, _ = load('local interface A { void f(); }; interface B { void f(); };')
        self.assertTrue(g.interface_by_name('A').is_local)
        self.assertFalse(g.interface_by_name('B').is_local)


if __name__ == '__main__':
    unittest.main()
