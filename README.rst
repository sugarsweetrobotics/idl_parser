idl_parser
============

|Test Status| |Docs Status|

Description 
-----------

OMG IDL file parser. This library just parse IDL files, and output intermidiate type objects.

Documentation
-------------

API reference and usage: https://idl-parser.readthedocs.io/

Example
-----------

.. code:: python

  """
  example for idl_parser package   
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

More examples are in the ``examples`` folder of the repository:

- ``example.py``: interfaces, typedefs, unions and structs
- ``union_example.py``: unions (discriminator kinds, case labels, member types)
- ``annotation_example.py``: IDL 4 annotations (``@key``, ``@range``, ...) and struct keys

https://github.com/sugarsweetrobotics/idl_parser/tree/main/examples

How to install
---------------

    sudo pip install idl_parser


Copyright
------------

- author: Yuki Suga

- copyright: Yuki Suga

- contact: please open an issue on `GitHub Issues <https://github.com/sugarsweetrobotics/idl_parser/issues>`_

- license: GPLv3

.. |Test Status| image:: https://github.com/sugarsweetrobotics/idl_parser/actions/workflows/test.yml/badge.svg?branch=main
   :target: https://github.com/sugarsweetrobotics/idl_parser/actions/workflows/test.yml

.. |Docs Status| image:: https://readthedocs.org/projects/idl-parser/badge/?version=latest
   :target: https://idl-parser.readthedocs.io/en/latest/
   :alt: Documentation Status
