"""Example: enumerator values set with ``@value(n)``.

Shows that
- ``@value(n)`` sets the value of an enumerator (``value``),
- an enumerator without ``@value`` takes the previous value plus 1
  (0 for the first one),
- ``n`` can be a decimal, hex or octal literal, a negative number, or the
  name of a ``const``,
- a value used twice in the same enum is an ``InvalidIDLSyntaxError``.

Run::

    python examples/enum_value_example.py
"""
import _path  # noqa: F401  (use the idl_parser of this checkout)

from idl_parser import parser
from idl_parser.exception import InvalidIDLSyntaxError

IDL = '''
module robot {
  const long ERROR_BASE = 100;

  enum Mode {
    @value(10) IDLE,
    RUNNING,                  // 11: the previous value plus 1
    @value(0x20) PAUSED,      // 32
    @value(-1) UNKNOWN,
    @value(ERROR_BASE) ERROR, // the value of a const
    FATAL                     // 101
  };
};
'''

DUPLICATE_IDL = 'enum E { @value(1) A, @value(1) B };'


def main():
    robot = parser.IDLParser().load(IDL).module_by_name('robot')

    mode = robot.enum_by_name('Mode')
    print('enum %s' % mode.full_path)
    for v in mode.values:
        print('  %-8s = %d' % (v.name, v.value))
    print('FATAL is', mode.value_by_name('FATAL').value)
    print('to_simple_dic:', mode.to_simple_dic())
    print()

    try:
        parser.IDLParser().load(DUPLICATE_IDL)
    except InvalidIDLSyntaxError as e:
        print('duplicate value:', e)


if __name__ == '__main__':
    main()
