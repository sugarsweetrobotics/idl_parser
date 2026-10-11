"""Example: read the direction of interface method arguments (in / out / inout).

In IDL each argument of a method has a direction:

- ``in``: the caller passes a value to the method,
- ``out``: the method returns a value to the caller through the argument,
- ``inout``: the caller passes a value and the method may change it.

Shows how to
- read each argument's direction (``direction``),
- pick the arguments the caller sends and the ones it receives,
- build a simple call signature from the directions.

Run::

    python examples/argument_direction_example.py
"""
import _path  # noqa: F401  (use the idl_parser of this checkout)

from idl_parser import parser

IDL = '''
module my_module {
  interface Counter {
    // in: the value is only passed to the method
    void set(in long value);

    // out: the value is only returned from the method
    void get(out long value);

    // inout: the value is passed, changed and returned
    void increment(inout long value);

    // directions can be mixed in one method
    boolean divide(in double a, in double b, out double quotient, inout long count);
  };
};
'''


def main():
    global_module = parser.IDLParser().load(IDL)
    counter = global_module.module_by_name('my_module').interface_by_name('Counter')

    print('== Direction of each argument')
    for m in counter.methods:
        for a in m.arguments:
            print('  %-10s %-9s %-6s %s' % (m.name, a.name, a.direction, a.type.name))
    print()

    # in and inout arguments are sent by the caller,
    # out and inout arguments (and the return value) come back to the caller.
    print('== What the caller sends and receives')
    for m in counter.methods:
        sends = [a.name for a in m.arguments if a.direction in ('in', 'inout')]
        receives = [a.name for a in m.arguments if a.direction in ('out', 'inout')]
        if m.returns.name != 'void':
            receives.insert(0, '(return %s)' % m.returns.name)
        print('  %-10s sends: %-14s receives: %s' % (m.name, ', '.join(sends) or '-', ', '.join(receives) or '-'))
    print()

    # For example, a Python-like signature: in/inout become parameters,
    # out/inout and the return value become results.
    print('== Python-like signatures')
    for m in counter.methods:
        params = [a.name for a in m.arguments if a.direction in ('in', 'inout')]
        results = [a.name for a in m.arguments if a.direction in ('out', 'inout')]
        if m.returns.name != 'void':
            results.insert(0, 'result')
        call = '%s(%s)' % (m.name, ', '.join(params))
        print('  %s' % ('%s = %s' % (', '.join(results), call) if results else call))


if __name__ == '__main__':
    main()
