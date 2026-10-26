"""Example: struct inheritance and map types (IDL 4).

Shows how to get
- the base struct of ``struct B : A`` (``base``),
- a struct's own members (``members``) and the members it inherits
  (``all_members``, base members first),
- the key and value types of ``map<K, V>`` (``key_type``, ``value_type``)
  and the bound of ``map<K, V, N>`` (``bound``).

Run::

    python examples/struct_inheritance_map_example.py
"""
import _path  # noqa: F401  (use the idl_parser of this checkout)

from idl_parser import parser

IDL = '''
module robot {
  struct Header {
    @key string frame_id;
    long long stamp;
  };

  struct Joint {
    double position;
    double velocity;
  };

  // A struct that inherits the members of Header
  struct JointState : Header {
    map<string, Joint> joints;           // unbounded map
  };

  // Inheritance can go on: Header -> JointState -> LimitedJointState
  struct LimitedJointState : JointState {
    map<string, double, 16> max_effort;  // bounded map: at most 16 entries
  };

  typedef map<long, string> IdNames;
};
'''


def describe_type(t):
    """Return a short description of a member type."""
    if t.is_map:
        text = 'map from %s to %s' % (describe_type(t.key_type), describe_type(t.value_type))
        if t.is_bounded_map:
            text += ' (at most %s entries)' % t.bound
        return text
    if t.is_struct:
        return 'struct %s' % t.full_path
    return t.name


def main():
    global_module = parser.IDLParser().load(IDL)
    robot = global_module.module_by_name('robot')

    for struct in robot.structs:
        base = struct.base.full_path if struct.base else None
        print('struct %s (base: %s)' % (struct.full_path, base))
        print('  own members:', [m.name for m in struct.members])
        print('  all members:', [m.name for m in struct.all_members])
        print()

    limited = robot.struct_by_name('LimitedJointState')

    # The chain of base structs
    chain = []
    s = limited
    while s is not None:
        chain.append(s.name)
        s = s.base
    print('LimitedJointState inherits:', ' -> '.join(reversed(chain)))

    # Inherited members are found by name, and keys are inherited too
    print('frame_id comes from the base:', limited.member_by_name('frame_id').type.name)
    print('keys of LimitedJointState:', limited.keys)
    print()

    # Map members: key and value types, and the bound of a bounded map
    for m in limited.all_members:
        print('  %-12s %s' % (m.name, describe_type(m.type)))
    print()

    id_names = robot.typedef_by_name('IdNames')
    print('typedef IdNames:', describe_type(id_names.type))
    print()

    # to_dic() writes the struct's own members and the name of its base
    print('to_dic():', limited.to_dic())


if __name__ == '__main__':
    main()
