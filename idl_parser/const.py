import os, sys, traceback

from . import node
sep = '::'


class IDLConst(node.IDLNode):

    def __init__(self, values, parent, filepath=None):
        super(IDLConst, self).__init__('IDLConst', values[values.index('=')-1], parent)
        value_ = values[values.index('=')+1:]
        for i in [',' , '{', '}']:
            while True:
                if i in value_:
                    value_.remove(i)
                else: break
        if len(value_) == 1:
            value_ = value_[0].strip('"')
        else:
            value_ = [v.strip('"') for v in value_]
        name_ = values[values.index('=')-1]
        typename = ''
        for t in values[:values.index(name_)]:
            typename = typename + ' ' + t
        typename = typename.strip()        
        self._typename = typename
        self._verbose = True
        self._value = value_
        self._filepath= filepath

    def to_simple_dic(self, quiet=False, full_path=False, recursive=False, member_only=False):
        name = self.full_path if full_path else self.name
        if quiet:
            return 'const %s %s = %s' % (self.typename, name, self.value)
        dic = { 'const %s' % name : { 'type' : self.typename,
                                      'value' : self.value } }
        return dic

    def to_dic(self):
        dic = { 'name' : self.name,
                'filepath' : self.filepath,
                'classname' : self.classname,
                'typename' : self.typename,
                'value' : self.value }
        return dic

    @property
    def typename(self):
        return self._typename

    @property
    def type(self):
        return self.root_node.find_types(self.typename)[0]
    @property
    def value(self):
        return self._value

    @property
    def value_string(self):
        return self._value

    @property
    def full_path(self):
        return self.parent.full_path + sep + self.name

