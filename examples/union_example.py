"""Example: read IDL unions (discriminated unions).

Shows how to get
- the discriminator type of a union (enum, integer, boolean),
- which case labels select each member (including several labels for one member),
- the ``default:`` member (``is_default`` / ``default_member``),
- each member's type: primitive, struct, typedef of a sequence, or array,
- a union used as a struct member,
- the union as a plain dict (``to_dic``).

Run::

    python examples/union_example.py
"""
import json

import _path  # noqa: F401  (use the idl_parser of this checkout)

from idl_parser import parser

IDL = '''
module shapes {
  enum ShapeKind { CIRCLE, RECTANGLE, POLYGON, POINT };

  struct Point2D {
    double x;
    double y;
  };

  typedef sequence<Point2D> PointSeq;

  struct Rectangle {
    Point2D top_left;
    double width;
    double height;
  };

  // Discriminator is an enum. One member can be selected by several labels.
  union Shape switch (ShapeKind) {
    case CIRCLE:
      double radius;
    case RECTANGLE:
      Rectangle rect;
    case POLYGON:
      PointSeq vertices;
    case POINT:
      Point2D point;
  };

  // Discriminator is an integer type; labels are numbers (negative is fine).
  union Value switch (long) {
    case -1:
    case 0:
      string error_message;
    case 1:
      long long integer_value;
    case 2:
      double matrix[3][3];
    default:
      PointSeq raw_points;
  };

  // "default" can share a member with "case" labels.
  union Reading switch (ShapeKind) {
    case CIRCLE:
      double radius;
    case POINT:
    default:
      Point2D position;
  };

  // Discriminator is boolean.
  union OptionalDouble switch (boolean) {
    case TRUE:
      double value;
  };

  // A union can be a member of a struct.
  struct ShapeMessage {
    ShapeKind kind;
    Shape shape;
  };
};
'''


def describe_type(t):
    """Return a short human readable description of a member type."""
    if t.is_primitive:
        return 'primitive %s' % t.name
    if t.is_array:
        return 'array %s' % t.name
    if t.is_typedef:
        # Follow the typedef to see what it stands for.
        inner = t.type
        if inner.is_sequence:
            return 'typedef %s = sequence of %s' % (t.full_path, inner.inner_type.name)
        return 'typedef %s = %s' % (t.full_path, inner.name)
    if t.is_struct:
        return 'struct %s (members: %s)' % (t.full_path, ', '.join(m.name for m in t.members))
    if t.is_union:
        return 'union %s' % t.full_path
    if t.is_enum:
        return 'enum %s' % t.full_path
    return t.name


def print_union(union):
    print('union %s switch (%s)' % (union.full_path, union.descriminator_kind))
    for member in union.members:
        labels = []
        if member.descriminator_value_associations:
            labels.append('case ' + ', '.join(member.descriminator_value_associations))
        if member.is_default:
            labels.append('default')
        print('  %s -> %s: %s' % (' / '.join(labels), member.name, describe_type(member.type)))


def main():
    global_module = parser.IDLParser().load(IDL)
    shapes = global_module.module_by_name('shapes')

    # All unions in a module
    print('unions in module shapes:', [u.name for u in shapes.unions])
    print()

    for union in shapes.unions:
        print_union(union)
        print()

    # Look up a member by name, and find the member for a discriminator value.
    shape = shapes.union_by_name('Shape')
    rect = shape.member_by_name('rect')
    print('Shape.rect full path:', rect.full_path)
    print('Shape.rect.top_left type:', rect.type.member_by_name('top_left').type.full_path)

    value = shapes.union_by_name('Value')
    for label in ('-1', '0', '1', '2'):
        selected = [m.name for m in value.members if label in m.descriminator_value_associations]
        print('Value with discriminator %s holds: %s' % (label, selected[0]))
    # Any other discriminator value selects the default member (if there is one).
    print('Value with any other discriminator holds: %s' % value.default_member.name)
    print('Shape default member:', shape.default_member)
    print()

    # The discriminator kind is a name; resolve it to its enum to list the labels.
    kind = shapes.enum_by_name(shape.descriminator_kind)
    print('%s values: %s' % (kind.name, [v.name for v in kind.values]))
    print()

    # A union used inside a struct
    message = shapes.struct_by_name('ShapeMessage')
    for m in message.members:
        print('ShapeMessage.%s: %s' % (m.name, describe_type(m.type)))
    print()

    # The whole union as a dict (handy for JSON or code generators)
    print(json.dumps(shapes.union_by_name('OptionalDouble').to_dic(), indent=2))


if __name__ == '__main__':
    main()
