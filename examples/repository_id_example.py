"""Example: repository IDs (``IDL:omg.org/CosNaming/NamingContext:1.0``).

Shows that
- each definition has ``repository_id``,
- ``#pragma prefix`` adds a prefix to the definitions after it, up to the
  end of its scope,
- ``#pragma version`` changes the version, and ``#pragma ID`` / ``typeid``
  give the whole ID,
- ``typeprefix`` adds a prefix to a scope and everything in it.

Run::

    python examples/repository_id_example.py
"""
import _path  # noqa: F401  (use the idl_parser of this checkout)

from idl_parser import parser

IDL = '''
#pragma prefix "omg.org"
module CosNaming {
  typedef string Istring;
  interface NamingContext {
    exception NotFound { long why; };
    void unbind(in Istring n) raises (NotFound);
  };
#pragma version NamingContext 1.1
};

module Legacy {
  struct Point { long x; long y; };
  typeid Point "DCE:9e2f5c1a-0001:1";
  struct Size { long w; long h; };
};

module Robot {
  typeprefix Robot "example.com";
  interface Arm { void move(in long x); };
};
'''


def main():
    g = parser.IDLParser().load(IDL)
    naming = g.module_by_name('CosNaming')
    nc = naming.interface_by_name('NamingContext')
    legacy = g.module_by_name('Legacy')
    arm = g.module_by_name('Robot').interface_by_name('Arm')
    for node, label in [(naming, 'CosNaming'),
                        (naming.typedef_by_name('Istring'), 'CosNaming::Istring'),
                        (nc, 'CosNaming::NamingContext'),
                        (nc.exceptions[0], 'CosNaming::NamingContext::NotFound'),
                        (nc.method_by_name('unbind'), 'CosNaming::NamingContext::unbind'),
                        (legacy.struct_by_name('Point'), 'Legacy::Point'),
                        (legacy.struct_by_name('Size'), 'Legacy::Size'),
                        (arm, 'Robot::Arm'),
                        (arm.method_by_name('move'), 'Robot::Arm::move')]:
        print('%-36s %s' % (label, node.repository_id))


if __name__ == '__main__':
    main()
