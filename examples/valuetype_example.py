"""Example: read IDL value types (``valuetype``) and event types (``eventtype``).

Shows how to get
- the state members of a value type, with ``public`` / ``private``,
- its initializers (``factory``), operations and attributes,
- base value types (``: truncatable B``) and supported interfaces (``supports I``),
- the ``abstract`` / ``custom`` modifiers,
- a boxed value type (``valuetype V long;``) and the type it wraps,
- an event type, read the same way as a value type,
- value types and event types used as member and argument types,
- a value type as a plain dict (``to_dic``).

Run::

    python examples/valuetype_example.py
"""
import json

import _path  # noqa: F401  (use the idl_parser of this checkout)

from idl_parser import parser

IDL = '''
module sensors {
  exception InvalidRange { string reason; };

  interface Resettable {
    void reset();
  };

  // An abstract value type has operations only (no state).
  abstract valuetype Describable {
    string describe();
  };

  valuetype Reading : Describable {
    public double value;
    public string unit;
    private long long raw;
    factory create(in double value, in string unit) raises (InvalidRange);
    double scaled(in double factor);
    readonly attribute boolean valid;
  };

  // Inherits Reading; "truncatable" lets a receiver that does not know
  // RangedReading use it as a Reading.
  valuetype RangedReading : truncatable Reading supports Resettable {
    public double min, max;
  };

  // A custom value type marshals itself.
  custom valuetype Calibration {
    public sequence<double> coefficients;
  };

  // A value type can refer to itself (a linked list).
  valuetype ReadingNode {
    public Reading item;
    public ReadingNode next;
  };

  // Boxed value types wrap a single type; the value may be null.
  valuetype OptionalName string;
  valuetype OptionalValues sequence<double>;

  // An event type has the same form as a value type.
  eventtype Alarm {
    public string message;
    public long level;
  };
  eventtype CriticalAlarm : Alarm { };

  struct Snapshot {
    Reading latest;
    OptionalName label;
  };

  interface Monitor {
    Reading read();
    void notify(in Alarm alarm);
  };
};
'''


def print_valuetype(v):
    modifiers = [m for m in ('abstract', 'custom') if getattr(v, 'is_' + m)]
    kind = 'eventtype' if v.is_eventtype else 'valuetype'
    print(' '.join(modifiers + [kind, v.full_path]))
    if v.is_boxed:
        print('  boxed type:', v.boxed_type.name)
        return
    if v.inheritances:
        print('  inherits: %s%s' % ('truncatable ' if v.is_truncatable else '',
                                    ', '.join(b.full_path for b in v.inheritances)))
    if v.supports:
        print('  supports:', ', '.join(i.full_path for i in v.supports))
    for m in v.state_members:
        print('  %s %s %s' % (m.visibility, m.type, m.name))
    for f in v.factories:
        params = ', '.join(a.to_simple_dic() for a in f.arguments)
        print('  factory %s(%s) raises %s' % (f.name, params, f.raises))
    for op in v.methods:
        params = ', '.join(a.to_simple_dic() for a in op.arguments)
        print('  operation %s %s(%s)' % (op.returns.name, op.name, params))
    for a in v.attributes:
        print('  %sattribute %s %s' % ('readonly ' if a.readonly else '', a.type, a.name))


def main():
    global_module = parser.IDLParser().load(IDL)
    sensors = global_module.module_by_name('sensors')

    # All value types and event types in a module
    print('valuetypes in module sensors:', [v.name for v in sensors.valuetypes])
    print('eventtypes in module sensors:', [e.name for e in sensors.eventtypes])
    print()

    for v in sensors.valuetypes + sensors.eventtypes:
        print_valuetype(v)
        print()

    # Look up by name; the exceptions of a factory are resolved like those of an operation.
    reading = sensors.valuetype_by_name('Reading')
    create = reading.factory_by_name('create')
    print('Reading.create raises:', [x.full_path for x in create.exceptions])
    print('Reading.raw is public:', reading.state_member_by_name('raw').is_public)

    # A self-referencing member resolves to the value type itself.
    node = sensors.valuetype_by_name('ReadingNode')
    print('ReadingNode.next type is ReadingNode:', node.state_member_by_name('next').type is node)
    print()

    # Value types and event types can be member, return and argument types.
    snapshot = sensors.struct_by_name('Snapshot')
    for m in snapshot.members:
        print('Snapshot.%s: %s %s' % (m.name, m.type.classname, m.type.full_path))
    monitor = sensors.interface_by_name('Monitor')
    print('Monitor.read returns:', monitor.method_by_name('read').returns.obj.full_path)
    alarm = monitor.method_by_name('notify').argument_by_name('alarm')
    print('Monitor.notify(alarm) is an eventtype:', alarm.type.obj.is_eventtype)
    print()

    # The whole value type as a dict (handy for JSON or code generators)
    print(json.dumps(sensors.valuetype_by_name('RangedReading').to_dic(), indent=2))


if __name__ == '__main__':
    main()
