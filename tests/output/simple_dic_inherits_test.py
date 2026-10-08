"""Interface to_simple_dic(): the first entry is always {'inherits': [...]} (issue #5)."""
import os
import unittest
from idl_parser import parser
from tests import support

IDL_DIR = support.IDL_DIR


extended_idl_path = os.path.join(IDL_DIR, 'generalization_extended.idl')


class GeneralizationSimpleDicTestFunctions(unittest.TestCase):
    """Category: Dictionary output and code generation / カテゴリ: 辞書出力・コード生成

    Interface to_simple_dic(): the first entry is always {'inherits': [...]}.
    interface の to_simple_dic(): 先頭は常に {'inherits': [...]}。
    """

    @classmethod
    def setUpClass(cls):
        with open(extended_idl_path, 'r') as idlf:
            cls.m = parser.IDLParser().load(idlf.read())
        cls.moduleP = cls.m.module_by_name('moduleP')

    def test_no_inheritance_has_empty_inherits(self):
        """to_simple_dic(): {'inherits': []} comes first even without inheritance.

        to_simple_dic(): 継承なしでも先頭に {'inherits': []}。
        """
        self.assertEqual(self.moduleP.interface_by_name('Base').to_simple_dic(),
                         {'interface Base': [
                             {'inherits': []},
                             {'methodBase': {'returns': 'void', 'params': []}}]})

    def test_empty_interface(self):
        """to_simple_dic(): an empty interface has only the inherits entry.

        to_simple_dic(): 空の interface は inherits だけ。
        """
        m = parser.IDLParser().load('module M { interface Empty {}; };')
        self.assertEqual(m.module_by_name('M').interface_by_name('Empty').to_simple_dic(),
                         {'interface Empty': [{'inherits': []}]})

    def test_inherits_entry_comes_first(self):
        """to_simple_dic(): inherits comes before the methods.

        to_simple_dic(): inherits がメソッドより前に来る。
        """
        self.assertEqual(self.moduleP.interface_by_name('Derived').to_simple_dic(),
                         {'interface Derived': [
                             {'inherits': ['moduleP::Base']},
                             {'methodDerived': {'returns': 'void', 'params': []}}]})

    def test_multiple_inheritance_keeps_order(self):
        """to_simple_dic(): the order of multiple bases is kept.

        to_simple_dic(): 多重継承の順序が保たれる。
        """
        entries = self.moduleP.interface_by_name('Multi').to_simple_dic()['interface Multi']
        self.assertEqual(entries[0], {'inherits': ['moduleP::Base', 'moduleP::Other']})
        self.assertEqual([list(e)[0] for e in entries[1:]], ['methodMulti'])

    def test_global_base(self):
        """to_simple_dic(): a base at global scope is shown as ::GlobalBase.

        to_simple_dic(): グローバルの継承元は ::GlobalBase と出る。
        """
        entries = self.moduleP.interface_by_name('FromGlobal').to_simple_dic()['interface FromGlobal']
        self.assertEqual(entries[0], {'inherits': ['::GlobalBase']})

    def test_key_is_unchanged(self):
        """to_simple_dic(): the key is still 'interface <name>'.

        to_simple_dic(): キーは従来どおり 'interface 名'。
        """
        self.assertIn('interface Multi', self.moduleP.interface_by_name('Multi').to_simple_dic())

    def test_quiet_is_unchanged(self):
        """to_simple_dic(quiet=True) output is unchanged.

        to_simple_dic(quiet=True) の出力は従来どおり。
        """
        self.assertEqual(self.moduleP.interface_by_name('Multi').to_simple_dic(quiet=True), 'interface Multi')

    def test_module_output(self):
        """to_simple_dic() of a module gives every interface an inherits entry.

        module の to_simple_dic() で全 interface に inherits が付く。
        """
        dic = self.moduleP.to_simple_dic()
        interfaces = {list(e)[0]: e[list(e)[0]] for e in dic['module moduleP'] if list(e)[0].startswith('interface ')}
        for name, entries in interfaces.items():
            with self.subTest(interface=name):
                self.assertIn('inherits', entries[0])
        self.assertEqual(interfaces['interface Base'][0], {'inherits': []})
        self.assertEqual(interfaces['interface Grandchild'][0], {'inherits': ['moduleP::Derived']})


if __name__ == '__main__':
    unittest.main()
