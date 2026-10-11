"""Example: read enums and their values.

Shows how to get
- the enums in a module (``enums``, ``enum_by_name``),
- each enumerator's name and ordinal (``values``, ``value``),
- an enumerator by name (``value_by_name``),
- an enum used as a struct member and as a method return type.

Run::

    python examples/enum_example.py
"""
import _path  # noqa: F401  (use the idl_parser of this checkout)

from idl_parser import parser

IDL = '''
module my_module {
  enum Color {
    RED,
    GREEN,
    BLUE
  };

  enum ReturnCode {
    RETURN_OK,
    RETURN_ERROR,
    RETURN_TIMEOUT
  };

  struct Light {
    Color color;
    double brightness;
  };

  interface LightController {
    ReturnCode setColor(in Color color);
  };
};
'''


def main():
    global_module = parser.IDLParser().load(IDL)
    my_module = global_module.module_by_name('my_module')

    print('enums in my_module:', [e.name for e in my_module.enums])
    print()

    color = my_module.enum_by_name('Color')
    print('enum %s' % color.full_path)
    for v in color.values:
        print('  %s = %d' % (v.name, v.value))
    print('BLUE is', color.value_by_name('BLUE').value)
    print()

    # A struct member whose type is an enum
    light = my_module.struct_by_name('Light')
    member = light.member_by_name('color')
    print('Light.color is enum? %s (%s)' % (member.type.is_enum, member.type.full_path))

    # An enum as a method return type
    method = my_module.interface_by_name('LightController').method_by_name('setColor')
    print('setColor returns %s' % method.returns.name)


if __name__ == '__main__':
    main()
