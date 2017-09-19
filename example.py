"""

"""

def  test():    
    from idl_parser import parser
    _parser = parser.IDLParser()
    idl_str = '''
module my_module {
  struct Time {
    long sec;
    long usec;
  };

  enum union_descriminator_kind
  {
      PARAMETER_VALUE_UNKNOWN,
      PARAMETER_VALUE_ULONGLONG,
      PARAMETER_VALUE_LONGLONG,
      PARAMETER_VALUE_DOUBLE,
      PARAMETER_VALUE_STRING,
      PARAMETER_VALUE_KIND_COUNT
  };

  union union_value switch( union_descriminator_kind )
  {
      case PARAMETER_VALUE_UNKNOWN:
      case PARAMETER_VALUE_KIND_COUNT:
      case PARAMETER_VALUE_ULONGLONG:
          unsigned long long      ull_value;
      case PARAMETER_VALUE_LONGLONG:
          long long               ll_value;
      case PARAMETER_VALUE_DOUBLE:
          double                  d_value;
      case PARAMETER_VALUE_STRING:
          sequence<char>          str_value;
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
'''    
    
    global_module = _parser.load(idl_str)
    my_module = global_module.module_by_name('my_module')
    dataGetter = my_module.interface_by_name('DataGetter')
    print 'DataGetter interface'
    for m in dataGetter.methods:
      print '- method:'
      print '  name:', m.name
      print '  returns:', m.returns.name
      print '  arguments:'
      for a in m.arguments:
        print '    name:', a.name
        print '    type:', a.type
        print '    direction:', a.direction
        
    doubleSeq = my_module.typedef_by_name('DoubleSeq')
    print 'typedef %s %s' % (doubleSeq.type.name, doubleSeq.name)

    timedDoubleSeq = my_module.struct_by_name('TimedDoubleSeq')
    print 'TimedDoubleSeq'
    for m in timedDoubleSeq.members:
      print '- member:'
      print '  name:', m.name
      print '  type:', m.type.name    


if __name__ == '__main__':
    test()
