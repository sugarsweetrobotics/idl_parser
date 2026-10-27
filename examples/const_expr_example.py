"""Example: constant expressions in array sizes, bounds and const values.

Shows that
- the value of an integer ``const`` is evaluated (``value``), also when it
  uses other constants, while ``value_string`` keeps it as written,
- array sizes and the bounds of ``string<>``, ``sequence<>`` and ``map<>``
  can be expressions such as ``N * 2`` or ``(1 << 3)``,
- a size that is not a positive integer is an
  ``InvalidConstExpressionError``.

Run::

    python examples/const_expr_example.py
"""
import _path  # noqa: F401  (use the idl_parser of this checkout)

from idl_parser import parser
from idl_parser.exception import InvalidConstExpressionError

IDL = '''
module robot {
  const long JOINTS = 6;
  const long AXES = JOINTS * 2;          // 12
  const unsigned long MASK = (1 << 4) - 1; // 15
  const long NAME_LEN = 0x10;           // 16

  struct Arm {
    double angles[JOINTS];
    double limits[AXES][2];
    string<NAME_LEN * 2> name;
    sequence<double, JOINTS + 1> history;
    map<string<8>, double, (JOINTS << 1)> params;
  };
};
'''

INVALID_IDL = 'const long N = 3; struct S { long a[N - 3]; };'


def main():
    robot = parser.IDLParser().load(IDL).module_by_name('robot')

    for c in robot.consts:
        print('const %-8s = %-3s (written as: %s)' % (c.name, c.value, c.value_string))
    print()

    arm = robot.struct_by_name('Arm')
    for name in ('angles', 'limits'):
        print('%-8s %s' % (name, arm.member_by_name(name).type))
    for name in ('name', 'history', 'params'):
        print('%-8s bound %s' % (name, arm.member_by_name(name).type.bound))
    print()

    try:
        parser.IDLParser().load(INVALID_IDL)
    except InvalidConstExpressionError as e:
        print('invalid size:', e)


if __name__ == '__main__':
    main()
