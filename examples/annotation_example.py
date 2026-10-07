"""Example: read IDL 4 annotations (``@key``, ``@range(min=0, max=10)``, ...).

Annotations are kept on whatever they are written before: a module, struct,
union, enum, typedef, const, interface, struct/union member, enum value,
method or method argument. They never leak into type names.

Shows how to
- list annotations and look one up by name (``annotations``,
  ``annotation_by_name``, ``has_annotation``),
- read annotation arguments (``args``, ``params``, ``value``),
- get struct keys from ``@key`` (combined with ``#pragma keylist``),
- read annotations that change parsing (``@bit_bound``, ``@position``),
- get annotations in ``to_dic()`` output,
- use your own annotations (``@annotation`` definitions are skipped).

Run::

    python examples/annotation_example.py
"""
import json

import _path  # noqa: F401  (use the idl_parser of this checkout)

from idl_parser import parser

IDL = '''
// A user-defined annotation. The definition itself is skipped by the parser,
// but uses of it (@unit_system(...)) are kept like any other annotation.
@annotation unit_system { string name default "SI"; };

@unit_system(name="SI")
module robot {

  @extensibility(APPENDABLE) @topic
  struct JointState {
    @key long joint_id;
    @key string robot_name;
    @range(min=-180, max=180) @unit("deg") double position;
    @unit("deg/s") @default(0) double velocity;
    @optional double effort;
    long sequence_number;
  };

  struct Command {
    long target_id;
    long priority;
    @key long command_id;
  };

  enum Mode {
    @value(10) IDLE,
    @value(20) RUNNING,
    @value(99) @deprecated ERROR
  };

  @extensibility(FINAL)
  union Setpoint switch (Mode) {
    case IDLE:
      @unit("deg") double hold_position;
    case RUNNING:
      @unit("deg/s") double target_velocity;
  };

  @bit_bound(8)
  bitmask Status {
    @position(0) POWERED,
    MOVING,
    @position(7) FAULT
  };

  @range(min=0, max=100) typedef long Percent;

  @verbatim(language="c++", text="constexpr") const long MAX_JOINTS = 7;

  @service(platform="DDS")
  interface Controller {
    @oneway_hint void setMode(in Mode mode);
    long move(@range(min=0, max=6) in long joint_id, in double position);
  };
};

#pragma keylist robot::Command target_id
'''


def show(label, node):
    anns = ' '.join(str(a) for a in node.annotations) or '(none)'
    print('%-28s %s' % (label, anns))


def main():
    global_module = parser.IDLParser().load(IDL)
    robot = global_module.module_by_name('robot')

    print('== Annotations on each kind of definition')
    show('module robot', robot)
    joint_state = robot.struct_by_name('JointState')
    show('struct JointState', joint_state)
    for m in joint_state.members:
        # Annotations never become part of the type name.
        show('  %s %s' % (m.type, m.name), m)
    mode = robot.enum_by_name('Mode')
    for v in mode.values:
        show('enum value %s' % v.name, v)
    setpoint = robot.union_by_name('Setpoint')
    show('union Setpoint', setpoint)
    for m in setpoint.members:
        show('  case %s: %s' % (','.join(m.descriminator_value_associations), m.name), m)
    show('typedef Percent', robot.typedef_by_name('Percent'))
    show('const MAX_JOINTS', robot.const_by_name('MAX_JOINTS'))
    controller = robot.interface_by_name('Controller')
    show('interface Controller', controller)
    for method in controller.methods:
        show('  method %s' % method.name, method)
        for a in method.arguments:
            show('    arg %s' % a.name, a)
    print()

    print('== Reading annotation arguments')
    position = joint_state.member_by_name('position')
    rng = position.annotation_by_name('range')
    print('str:    ', str(rng))                      # @range(min=-180, max=180)
    print('name:   ', rng.name)                      # range
    print('params: ', rng.params)                    # {'min': '-180', 'max': '180'}
    print('min/max:', int(rng.params['min']), int(rng.params['max']))
    unit = position.annotation_by_name('unit')
    print('unit:   ', unit.args, unit.value)         # ['"deg"'] "deg" (quotes are kept)
    print('unit without quotes:', unit.value.strip('"'))
    print('IDLE value:', int(mode.value_by_name('IDLE').annotation_by_name('value').value))
    print('ERROR deprecated?', mode.value_by_name('ERROR').has_annotation('deprecated'))
    print('effort optional?', joint_state.member_by_name('effort').has_annotation('optional'))
    print('sequence_number annotation:', joint_state.member_by_name('sequence_number').annotation_by_name('range'))
    print('module unit system:', robot.annotation_by_name('unit_system').params['name'])
    print()

    print('== Keys from @key and #pragma keylist')
    print('JointState keys:', joint_state.keys)
    print('JointState key members:', [m.name for m in joint_state.members if m.is_key])
    command = robot.struct_by_name('Command')
    # Keys from #pragma keylist come first, then members marked @key.
    print('Command keys:', command.keys,
          '(pragma: %s, @key: %s)' % (command.pragma_keys, command.annotated_keys))
    print()

    print('== Annotations that change parsing')
    status = robot.bitmask_by_name('Status')
    print('Status bit_bound:', status.bit_bound)
    print('Status positions:', [(v.name, v.position) for v in status.values])
    print()

    print('== to_dic() includes annotations')
    dic = robot.struct_by_name('JointState').to_dic()
    print(json.dumps({'annotations': dic['annotations'],
                      'members': [{k: m[k] for k in ('name', 'type', 'annotations') if k in m}
                                  for m in dic['members'][:3]]},
                     indent=2))


if __name__ == '__main__':
    main()
