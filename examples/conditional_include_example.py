"""Example: #include in #if / #elif / #else branches.

Shows how
- ``#if`` / ``#elif`` / ``#else`` select the IDL file that is included,
  so that one IDL reads the types of the platform given with
  ``IDLParser(defines=...)``,
- a file named in a branch that is skipped is not read, so it does not have
  to exist (``vendor/extension.idl`` is not in the folder),
- macros defined in an included file (``HAS_LIDAR``) select the branches
  after the ``#include``.

The IDL files are in ``examples/conditional_include/``.

Run::

    python examples/conditional_include_example.py
"""
import os

import _path  # noqa: F401  (use the idl_parser of this checkout)

from idl_parser import parser

IDL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'conditional_include')


def describe(defines):
    p = parser.IDLParser(defines=defines)
    p.parse_idl(os.path.join(IDL_DIR, 'robot.idl'))
    global_module = p.global_module
    handle = global_module.module_by_name('platform').typedef_by_name('Handle')
    robot = global_module.module_by_name('robot')
    print('defines=%r' % (defines,))
    print('  Handle is %s (%s)' % (handle.type.name, os.path.basename(handle.filepath)))
    print('  robot structs: %s' % ', '.join(s.name for s in robot.structs))
    print()


def main():
    describe({})
    describe({'PLATFORM_A': ''})
    describe({'PLATFORM_B': ''})


if __name__ == '__main__':
    main()
