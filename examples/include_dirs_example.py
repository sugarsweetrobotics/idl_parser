"""Example: read IDL files that ``#include`` each other across several directories.

The IDL files are in ``examples/include_dirs/``::

    common/time.idl          module common     (Time)
    geometry/geometry.idl    module geometry   (Point, Pose)    #include "time.idl"
    geometry/path.idl        module geometry   (PoseList, Path) #include <geometry.idl>, "time.idl"
    navigation/navigator.idl module navigation (Navigator)      #include "path.idl"

Shows how to
- give several include directories (``IDLParser(idl_dirs=[...])``),
- get the files an IDL file includes (``includes``) and follow them into an
  include tree,
- parse one file and get everything it includes, directly or through other
  files (navigator -> path -> geometry -> time), with each file read once,
- use types defined in included files,
- do the same with ``load()`` and ``include_dirs``,
- parse every IDL file in the directories (``parse_dirs``),
- catch an ``#include`` that can not be found.

Run::

    python examples/include_dirs_example.py
"""
import os

import _path  # noqa: F401  (use the idl_parser of this checkout)

from idl_parser import exception, parser

IDL_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'include_dirs')
# Searched in this order for "#include" files. A file in the same directory
# as the including file is found first, without an include directory.
INCLUDE_DIRS = [os.path.join(IDL_ROOT, d) for d in ('common', 'geometry', 'navigation')]
NAVIGATOR_IDL = os.path.join(IDL_ROOT, 'navigation', 'navigator.idl')


def rel(path):
    return os.path.relpath(path, IDL_ROOT).replace(os.sep, '/')


def print_include_tree(p, path, indent=0, seen=None):
    """includes() returns the direct includes only; follow them for the whole tree."""
    seen = set() if seen is None else seen
    again = path in seen
    print('  ' * indent + rel(path) + (' (already shown)' if again else ''))
    if again:
        return
    seen.add(path)
    for included in p.includes(path):
        print_include_tree(p, included, indent + 1, seen)


def print_definitions(global_module):
    for m in sorted(global_module.modules, key=lambda m: m.name):
        names = [s.name for s in m.structs] + [t.name for t in m.typedefs] + \
                [i.name for i in m.interfaces]
        print('  module %-10s %s' % (m.name, ', '.join(names)))


def main():
    p = parser.IDLParser(idl_dirs=INCLUDE_DIRS)

    # Direct includes of each file, resolved through the include directories
    print('includes():')
    for path in (NAVIGATOR_IDL, os.path.join(IDL_ROOT, 'geometry', 'path.idl')):
        print('  %s -> %s' % (rel(path), [rel(i) for i in p.includes(path)]))
    print()

    print('include tree:')
    print_include_tree(p, NAVIGATOR_IDL, 1)
    print()

    # Parse one file: the files it includes are read too, directly or
    # through other files, and each of them only once.
    p.parse(idls=[NAVIGATOR_IDL])
    g = p.global_module
    print('parse(idls=[navigation/navigator.idl]) defines:')
    print_definitions(g)
    print()

    # Types from included files are resolved across the files.
    pose = g.module_by_name('geometry').struct_by_name('Pose')
    print('Pose.stamp type:', pose.member_by_name('stamp').type.full_path)
    path_struct = g.module_by_name('geometry').struct_by_name('Path')
    poses = path_struct.member_by_name('poses').type
    print('Path.poses type: %s (%s)' % (poses.full_path, poses.type))
    nav = g.module_by_name('navigation').interface_by_name('Navigator')
    plan = nav.method_by_name('plan')
    print('Navigator.plan(%s) returns %s raises %s' % (
        plan.argument_by_name('goal').type.obj.full_path, plan.returns.obj.full_path,
        [x.full_path for x in plan.exceptions]))
    print('Navigator.now returns', nav.method_by_name('now').returns.obj.full_path)
    print()

    # load() with include_dirs gives the same result. Pass filepath too, so
    # that "#include" is also looked up next to the file.
    with open(NAVIGATOR_IDL) as f:
        g2 = parser.IDLParser().load(f.read(), include_dirs=INCLUDE_DIRS, filepath=NAVIGATOR_IDL)
    print('load() defines the same modules:',
          sorted(m.name for m in g2.modules) == sorted(m.name for m in g.modules))
    print()

    # Every IDL file in the directories. parse_dirs() lists the *.idl files
    # (parse(idl_dirs=...) only adds include directories and parses nothing).
    # A file already read through an #include is not read again.
    p_all = parser.IDLParser()
    all_idls = p_all.parse_dirs(INCLUDE_DIRS)
    print('parse_dirs() parsed %d files:' % len(all_idls), [rel(f) for f in all_idls])
    print_definitions(p_all.global_module)
    print()

    # Without the directory of time.idl, its #include can not be found.
    try:
        parser.IDLParser(idl_dirs=INCLUDE_DIRS[1:]).parse(idls=[NAVIGATOR_IDL])
    except exception.IDLCanNotFindException:
        print('without common/: IDLCanNotFindException')


if __name__ == '__main__':
    main()
