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

  enum UNION_DESCRIMINATOR_KIND
  {
      DESCRIMINATOR_UNKNOWN,
      DESCRIMINATOR_ULONGLONG,
      DESCRIMINATOR_LONGLONG,
      DESCRIMINATOR_DOUBLE,
      DESCRIMINATOR_STRING,
      DESCRIMINATOR_KIND_COUNT
  };

  union UnionType switch( UNION_DESCRIMINATOR_KIND )
  {
      case DESCRIMINATOR_UNKNOWN:
      case DESCRIMINATOR_KIND_COUNT:
      case DESCRIMINATOR_ULONGLONG:
          unsigned long long      ull_value;
      case DESCRIMINATOR_LONGLONG:
          long long               ll_value;
      case DESCRIMINATOR_DOUBLE:
          double                  d_value;
      case DESCRIMINATOR_STRING:
          sequence<char>     str_value;
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

    unionType = my_module.union_by_name('UnionType')
    print 'descriminator kind: %s' % unionType.descriminator_kind
    for m in unionType.members:
        print '- member:'
        print '  name:', m.name
        print '  type:', m.type.name
        print 'descriminator value associations:'
        for a in m.descriminator_value_associations:
            print '    %s' % a

    timedDoubleSeq = my_module.struct_by_name('TimedDoubleSeq')
    print 'TimedDoubleSeq'
    for m in timedDoubleSeq.members:
      print '- member:'
      print '  name:', m.name
      print '  type:', m.type.name


if __name__ == '__main__':
    test()
