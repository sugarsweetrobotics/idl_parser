# idl_parser

[![Test](https://github.com/sugarsweetrobotics/idl_parser/actions/workflows/test.yml/badge.svg?branch=main)](https://github.com/sugarsweetrobotics/idl_parser/actions/workflows/test.yml)
[![Documentation Status](https://readthedocs.org/projects/idl-parser/badge/?version=latest)](https://idl-parser.readthedocs.io/en/latest/)


## Description 

OMG IDL file parser. This library just parse IDL files, and output intermidiate type objects.

## Documentation

API reference and usage: https://idl-parser.readthedocs.io/

## Example
```
"""
    
"""
    
from idl_parser import parser
parser_ = parser.IDLParser()
idl_str = """
module my_module {
  struct Time {
    long sec;
    long usec;
  };

  typedef sequence<double> DoubleSeq;
  
  struct TimedDoubleSeq {
    Time tm;
    DoubleSeq data;
  };

  enum RETURN_VALUE {
    RETURN_OK,
    RETURN_FAILED,
  };

  interface DataGetter {
    RETURN_VALUE getData(out TimedDoubleSeq data);
  };

};
"""
    
global_module = parser_.load(idl_str)
my_module = global_module.module_by_name('my_module')
dataGetter = my_module.interface_by_name('DataGetter')
print('DataGetter interface')
for m in dataGetter.methods:
  print('- method:')
  print('  name:', m.name)
  print('  returns:', m.returns.name)
  print('  arguments:')
  for a in m.arguments:
    print('    name:', a.name)
    print('    type:', a.type)
    print('    direction:', a.direction)
    
doubleSeq = my_module.typedef_by_name('DoubleSeq')
print('typedef %s %s' % (doubleSeq.type.name, doubleSeq.name))

timedDoubleSeq = my_module.struct_by_name('TimedDoubleSeq')
print('TimedDoubleSeq')
for m in timedDoubleSeq.members:
  print('- member:')
  print('  name:', m.name)
  print('  type:', m.type.name)
```
More examples are in the [examples](examples/) folder:

| File | Shows |
|---|---|
| [`example.py`](examples/example.py) | interfaces, typedefs, unions and structs |
| [`union_example.py`](examples/union_example.py) | unions: discriminator kinds, case and `default` labels, member types |
| [`annotation_example.py`](examples/annotation_example.py) | IDL 4 annotations (`@key`, `@range`, ...) and struct keys |
| [`scoped_name_example.py`](examples/scoped_name_example.py) | same-named types in several modules: relative (`X`, `C::X`) and absolute (`::B::X`) names |

Run them with e.g. `python examples/union_example.py` (in a source checkout no install is needed).

## How to install
    sudo pip install idl_parser

## Copyright
* author: Yuki Suga
* copyright: Yuki Suga
* contact: please open an issue on [GitHub Issues](https://github.com/sugarsweetrobotics/idl_parser/issues)
* license: GPLv3 or later (GPL-3.0-or-later, see [LICENSE](LICENSE))

