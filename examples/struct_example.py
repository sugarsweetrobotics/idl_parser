"""Example: read structs and their members.

Shows how to get
- the structs in a module (``structs``, ``struct_by_name``),
- each member's name and type (primitive, struct, sequence, array),
- a member by name (``member_by_name``) and a nested struct's members.

Run::

    python examples/struct_example.py
"""
import _path  # noqa: F401  (use the idl_parser of this checkout)

from idl_parser import parser

IDL = '''
module my_module {
  struct Time {
    long sec;
    long nsec;
  };

  struct Pose {
    double position[3];
    double orientation[4];
  };

  struct Odometry {
    Time stamp;
    string frame_id;
    Pose pose;
    sequence<double> covariance;
  };
};
'''


def describe_type(t):
    """Return a short description of a member type."""
    if t.is_primitive:
        return t.name
    if t.is_sequence:
        return 'sequence of %s' % t.inner_type.name
    if t.is_array:
        return 'array %s' % t.name
    if t.is_struct:
        return 'struct %s' % t.full_path
    return t.name


def main():
    global_module = parser.IDLParser().load(IDL)
    my_module = global_module.module_by_name('my_module')

    print('structs in my_module:', [s.name for s in my_module.structs])
    print()

    for struct in my_module.structs:
        print('struct %s' % struct.full_path)
        for m in struct.members:
            print('  %-12s %s' % (m.name, describe_type(m.type)))
        print()

    odometry = my_module.struct_by_name('Odometry')

    # A member whose type is a struct: follow it to read its members.
    stamp = odometry.member_by_name('stamp')
    print('Odometry.stamp members:', [(m.name, m.type.name) for m in stamp.type.members])


if __name__ == '__main__':
    main()
