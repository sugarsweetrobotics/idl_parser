"""Example: resolve type names across modules (relative and absolute names).

When several modules define a type with the same name, a type name is
resolved with the IDL scoping rules (issues #69, #72):

- a relative name (``X``, ``C::X``) is looked up from the scope where it is
  written, innermost first, then in the outer scopes;
- an absolute name (``::B::X``) is looked up from the global scope only.

Shows how to get
- the definition a member, argument or return type refers to (``obj`` / ``type``),
- the name as written (``ref_name``) and the name of the definition (``name``),
- a typedef resolved in the scope where it is defined,
- ``find_types()`` with and without a scope.

Run::

    python examples/scoped_name_example.py
"""
import _path  # noqa: F401  (use the idl_parser of this checkout)

from idl_parser import parser

IDL = '''
// A global Point, and a Point in each module
struct Point { long id; };

module geometry {
  struct Point { double x; double y; };
  typedef Point Origin;       // geometry::Point (the scope of the typedef)

  module d3 {
    struct Point { double x; double y; double z; };
  };
};

module robot {
  struct Point { long joint; };

  module arm {
    struct Point { double angle; };

    interface Controller {
      // relative names: looked up from robot::arm, then robot, then global
      Point            current();                    // robot::arm::Point
      void             move_joint(in robot::Point p);  // robot::Point
      void             move_to(in geometry::Point p);  // geometry::Point
      void             move_to_3d(in geometry::d3::Point p);
      // absolute names: from the global scope only
      void             mark(in ::Point p);           // the global Point
      void             move_arm(in ::robot::arm::Point p);
      geometry::Origin origin();                     // typedef of geometry::Point
    };
  };

  struct Pose {
    Point                    joint;     // robot::Point
    arm::Point               arm;       // relative name with a scope: robot::arm::Point
    sequence<geometry::Point> path;     // element type is resolved too
    ::Point                  marker;    // the global Point
  };
};
'''


def path(node):
    """Full path of a definition ('' for the global scope is shown as '::')."""
    p = node.full_path.lstrip(':')
    return p if '::' in p else '::' + p


def show(label, written, definition):
    print('  %-22s %-24s -> %s' % (label, written, path(definition)))


def main():
    global_module = parser.IDLParser().load(IDL)
    robot = global_module.module_by_name('robot')
    arm = robot.module_by_name('arm')

    print('robot::arm::Controller (name as written -> definition)')
    controller = arm.interface_by_name('Controller')
    for method in controller.methods:
        if method.returns.name != 'void':
            show(method.name + '() returns', method.returns.ref_name, method.returns.obj)
        for a in method.arguments:
            show(method.name + '(' + a.name + ')', a.type.ref_name, a.type.obj)
    print()

    # For a struct member, .type is the definition itself
    print('robot::Pose members (member -> definition)')
    pose = robot.struct_by_name('Pose')
    for m in pose.members:
        t = m.type
        if t.is_sequence:
            print('  %-22s -> sequence of %s' % (m.name, path(t.inner_type.obj)))
        else:
            print('  %-22s -> %s' % (m.name, path(t)))
    print()

    # The typedef is resolved where it is defined (module geometry),
    # not where it is used (module robot::arm).
    typedef = controller.method_by_name('origin').returns.obj
    print('typedef %s -> %s' % (path(typedef), path(typedef.type)))
    print()

    # type.name is the name of the definition, without its scope
    t = controller.method_by_name('move_to').arguments[0].type
    print('name: %s, ref_name: %s, full path: %s' % (t.name, t.ref_name, path(t.obj)))
    print()

    # find_types(): with a scope the IDL scoping rules are used;
    # without one, every definition with that name is returned.
    print('find_types("Point", scope=robot::arm):', [path(n) for n in global_module.find_types('Point', scope=arm)])
    print('find_types("Point", scope=robot):     ', [path(n) for n in global_module.find_types('Point', scope=robot)])
    print('find_types("::Point"):                ', [path(n) for n in global_module.find_types('::Point')])
    print('find_types("Point") (no scope):       ', sorted(path(n) for n in global_module.find_types('Point')))


if __name__ == '__main__':
    main()
