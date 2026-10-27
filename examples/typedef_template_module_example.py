"""Example: types declared inside a typedef, and template modules.

Shows that
- ``typedef enum Mode { ... } ModeT;`` (and the same with ``struct``,
  ``union``, ``bitmask`` and ``bitset``) defines both the type and the
  typedef, so either name can be used afterwards,
- a template module (``module Buffer <typename T> { ... };``) and its
  instantiation (``module LongBuffer = Buffer<long>;``) are not supported
  yet: they are skipped with an ``UnsupportedIDLSyntaxWarning`` and the rest
  of the file is read as usual.

Run::

    python examples/typedef_template_module_example.py
"""
import warnings

import _path  # noqa: F401  (use the idl_parser of this checkout)

from idl_parser import parser
from idl_parser.exception import UnsupportedIDLSyntaxWarning

IDL = '''
module Buffer <typename T> {          // a template module: skipped
  struct Item { T value; };
};
module LongBuffer = Buffer<long>;     // its instantiation: skipped

module robot {
  typedef enum Mode { IDLE, RUNNING, ERROR } ModeT;
  typedef struct Point { double x; double y; } PointT, Polygon[4];
  typedef bitmask Flags { BRAKE, LIGHT } FlagsT;

  struct Status {
    ModeT mode;           // the typedef
    Point position;       // the struct declared in the typedef
    Polygon area;         // an array of Point
    FlagsT flags;
  };
};
'''


def describe_type(t):
    """Return a short description of a member type."""
    if t.is_typedef:
        return 'typedef %s of %s' % (t.name, describe_type(t.type))
    if t.is_array:
        return 'array[%s] of %s' % (t.size, describe_type(t.inner_type))
    return '%s %s' % (t.classname[3:].lower(), t.full_path)


def main():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        global_module = parser.IDLParser().load(IDL)
    for w in caught:
        if issubclass(w.category, UnsupportedIDLSyntaxWarning):
            print('warning:', w.message)
    print('modules:', [m.name for m in global_module.modules])
    print()

    robot = global_module.module_by_name('robot')
    print('enums:   ', [e.name for e in robot.enums])
    print('structs: ', [s.name for s in robot.structs])
    print('bitmasks:', [b.name for b in robot.bitmasks])
    print('typedefs:', [t.to_simple_dic() for t in robot.typedefs])
    print()

    for m in robot.struct_by_name('Status').members:
        print('  %-9s %s' % (m.name, describe_type(m.type)))
    print()

    # The typedef and the enum are the same type
    mode = robot.typedef_by_name('ModeT')
    print('ModeT is Mode:', mode.type is robot.enum_by_name('Mode'))
    print('Mode values:', [v.name for v in mode.type.values])


if __name__ == '__main__':
    main()
