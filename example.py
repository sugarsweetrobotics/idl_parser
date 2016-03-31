"""

"""

def  test():    
    import idl_parser
    parser = idl_parser.IDLParser()
    idl_str = '''
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
'''    
    
    global_module = parser.load(idl_str)
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
