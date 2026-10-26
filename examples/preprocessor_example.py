"""Example: #if / #elif / #else and macros.

Shows how
- ``#define N 5`` sets the size of arrays and bounds of sequences,
- ``#if`` / ``#elif`` / ``#else`` with ``defined(X)``, ``!``, ``&&``,
  ``||`` and comparisons select the definitions that are read,
- ``IDLParser(defines=...)`` defines macros from outside, like ``-D`` of
  a C preprocessor, so that one IDL gives several variants.

Run::

    python examples/preprocessor_example.py
"""
import _path  # noqa: F401  (use the idl_parser of this checkout)

from idl_parser import parser

IDL = '''
#ifndef SENSOR_IDL
#define SENSOR_IDL

#ifndef MAX_POINTS
#define MAX_POINTS 16
#endif

#define VERSION 2

module sensor {
#if VERSION >= 2 && !defined(LEGACY)
  struct Point { double x; double y; double z; };
#else
  struct Point { double x; double y; };
#endif

  struct Scan {
    Point points[MAX_POINTS];
    sequence<double, MAX_POINTS> intensities;
  };

#if defined(USE_TIMESTAMP) || defined(DEBUG)
  struct StampedScan { unsigned long long stamp; Scan scan; };
#elif VERSION == 1
  struct OldScan { Scan scan; };
#endif
};

#endif // SENSOR_IDL
'''


def describe(defines):
    global_module = parser.IDLParser(defines=defines).load(IDL)
    sensor = global_module.module_by_name('sensor')
    print('defines=%r' % (defines,))
    for struct in sensor.structs:
        members = ', '.join('%s %s' % (m.type.name, m.name) for m in struct.members)
        print('  struct %s { %s }' % (struct.name, members))
    bound = sensor.struct_by_name('Scan').member_by_name('intensities').type.bound
    print('  intensities bound: %s' % bound)
    print()


def main():
    describe({})
    describe({'LEGACY': ''})
    describe({'USE_TIMESTAMP': '1', 'MAX_POINTS': '4'})


if __name__ == '__main__':
    main()
