"""Example: any, Object, ValueBase and fixed-point types.

Shows how to tell
- ``any``, ``Object`` and ``ValueBase`` (primitive types, ``is_primitive``),
- ``fixed<d, s>`` decimal types (``is_fixed``) and their total number of
  digits (``digits``) and digits after the decimal point (``scale``),
- the default values that ``generate_constructor_python()`` gives them.

Run::

    python examples/any_fixed_example.py
"""
import _path  # noqa: F401  (use the idl_parser of this checkout)

from idl_parser import parser

IDL = '''
module shop {
  typedef fixed<9, 2> Price;           // up to 9999999.99

  struct Item {
    string name;
    Price price;
    fixed<5, 4> tax_rate;              // e.g. 0.1000
    any extra;                         // a value of any type
  };

  struct Order {
    sequence<Item> items;
    map<string, any> properties;
    Object customer;                   // a reference to any object
    ValueBase note;                    // any value type
  };

  interface Register {
    Price total(in Order order);
    any query(in string key);
  };
};
'''


def describe_type(t):
    """Return a short description of a member, argument or return type."""
    if t.classname == 'IDLBasicType':
        t = t.obj  # a named type in an operation: its definition
    if t.is_typedef:
        return 'typedef %s of %s' % (t.name, describe_type(t.type))
    if t.is_fixed:
        return 'fixed-point, %s digits, %s after the point' % (t.digits, t.scale)
    if t.is_sequence:
        return 'sequence of %s' % describe_type(t.inner_type)
    if t.is_map:
        return 'map from %s to %s' % (describe_type(t.key_type), describe_type(t.value_type))
    if t.is_struct:
        return 'struct %s' % t.full_path
    if t.is_primitive:
        return 'primitive %s' % t.name
    return t.name


def main():
    idl_parser = parser.IDLParser()
    global_module = idl_parser.load(IDL)
    shop = global_module.module_by_name('shop')

    for struct in shop.structs:
        print('struct %s' % struct.full_path)
        for m in struct.members:
            print('  %-11s %s' % (m.name, describe_type(m.type)))
        print()

    register = shop.interface_by_name('Register')
    for method in register.methods:
        args = ', '.join('%s: %s' % (a.name, describe_type(a.type)) for a in method.arguments)
        print('%s(%s) -> %s' % (method.name, args, describe_type(method.returns)))
    print()

    # The type name of a fixed-point type includes its digits and scale
    item = shop.struct_by_name('Item')
    print('tax_rate type name:', item.member_by_name('tax_rate').type.name)
    print('to_dic():', item.member_by_name('tax_rate').type.to_dic())
    print()

    # any, Object and ValueBase default to None, fixed-point types to 0
    for struct in shop.structs:
        print('default %s:' % struct.name, idl_parser.generate_constructor_python(struct))


if __name__ == '__main__':
    main()
