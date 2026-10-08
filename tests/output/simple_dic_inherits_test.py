"""Interface to_simple_dic(): the first entry is always {'inherits': [...]} (issue #5)."""
import os
import unittest
from idl_parser import parser
from tests import support

IDL_DIR = support.IDL_DIR


extended_idl_path = os.path.join(IDL_DIR, 'generalization_extended.idl')


class GeneralizationSimpleDicTestFunctions(unittest.TestCase):
    """to_simple_dic(): the first entry is always {'inherits': [...]}."""

    @classmethod
    def setUpClass(cls):
        with open(extended_idl_path, 'r') as idlf:
            cls.m = parser.IDLParser().load(idlf.read())
        cls.moduleP = cls.m.module_by_name('moduleP')

    def test_no_inheritance_has_empty_inherits(self):
        self.assertEqual(self.moduleP.interface_by_name('Base').to_simple_dic(),
                         {'interface Base': [
                             {'inherits': []},
                             {'methodBase': {'returns': 'void', 'params': []}}]})

    def test_empty_interface(self):
        m = parser.IDLParser().load('module M { interface Empty {}; };')
        self.assertEqual(m.module_by_name('M').interface_by_name('Empty').to_simple_dic(),
                         {'interface Empty': [{'inherits': []}]})

    def test_inherits_entry_comes_first(self):
        self.assertEqual(self.moduleP.interface_by_name('Derived').to_simple_dic(),
                         {'interface Derived': [
                             {'inherits': ['moduleP::Base']},
                             {'methodDerived': {'returns': 'void', 'params': []}}]})

    def test_multiple_inheritance_keeps_order(self):
        entries = self.moduleP.interface_by_name('Multi').to_simple_dic()['interface Multi']
        self.assertEqual(entries[0], {'inherits': ['moduleP::Base', 'moduleP::Other']})
        self.assertEqual([list(e)[0] for e in entries[1:]], ['methodMulti'])

    def test_global_base(self):
        entries = self.moduleP.interface_by_name('FromGlobal').to_simple_dic()['interface FromGlobal']
        self.assertEqual(entries[0], {'inherits': ['::GlobalBase']})

    def test_key_is_unchanged(self):
        self.assertIn('interface Multi', self.moduleP.interface_by_name('Multi').to_simple_dic())

    def test_quiet_is_unchanged(self):
        self.assertEqual(self.moduleP.interface_by_name('Multi').to_simple_dic(quiet=True), 'interface Multi')

    def test_module_output(self):
        dic = self.moduleP.to_simple_dic()
        interfaces = {list(e)[0]: e[list(e)[0]] for e in dic['module moduleP'] if list(e)[0].startswith('interface ')}
        for name, entries in interfaces.items():
            with self.subTest(interface=name):
                self.assertIn('inherits', entries[0])
        self.assertEqual(interfaces['interface Base'][0], {'inherits': []})
        self.assertEqual(interfaces['interface Grandchild'][0], {'inherits': ['moduleP::Derived']})


if __name__ == '__main__':
    unittest.main()
