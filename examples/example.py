"""Example: parse an IDL string and print the methods of an interface.

Run (no install needed in a checkout)::

    python examples/example.py

See also ``struct_example.py``, ``enum_example.py``, ``union_example.py``,
``annotation_example.py`` and ``scoped_name_example.py`` in this folder.
"""
import _path  # noqa: F401  (use the idl_parser of this checkout)

from idl_parser import parser

IDL = '''
module my_module {
  interface Calculator {
    long add(in long a, in long b);
    void reset();
    boolean divide(in double a, in double b, out double result);
  };
};
'''


def main():
    global_module = parser.IDLParser().load(IDL)
    my_module = global_module.module_by_name('my_module')
    calculator = my_module.interface_by_name('Calculator')

    print('interface %s' % calculator.full_path)
    for m in calculator.methods:
        args = ', '.join('%s %s %s' % (a.direction, a.type.name, a.name) for a in m.arguments)
        print('  %s %s(%s)' % (m.returns.name, m.name, args))


if __name__ == '__main__':
    main()
