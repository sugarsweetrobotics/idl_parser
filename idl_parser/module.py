import os, sys, traceback

from . import node, type, exception
from . import struct, typedef, interface, enum, const, union
global_namespace = '__global__'
sep = '::'

class IDLModule(node.IDLNode):

    def __init__(self, name=None, parent = None):
        super(IDLModule, self).__init__('IDLModule', name, parent)
        self._verbose = False
        if name is None:
            self._name = global_namespace
        if parent:
            self._global_module = self._parent
            while self._global_module:
                if self._global_module.name == '__global__':
                    break
                self._global_module = self._global_module._parent
        else:
            self._global_module = self
        self._interfaces = []
        self._typedefs = []
        self._structs = []
        self._enums = []
        self._unions = []
        self._consts = []
        self._modules = []
        self._forward_decls = []
        self._processed_modules = [global_namespace]
        self._found_types = {}
        self._full_path  = ''
        if self.parent is None:
            self._full_path  = '' # self.name
        else:
            if len(self.parent.full_path) == 0:
                self._full_path  = self.name
            self._full_path  = self.parent.full_path + sep + self.name    
    @property
    def is_global(self):
        return self.name == global_namespace

    @property
    def full_path(self):
        return self._full_path

    def to_simple_dic(self, quiet=False):
        dic = {'module %s' % self.name : [s.to_simple_dic(quiet) for s in self.structs] +
               [i.to_simple_dic(quiet) for i in self.interfaces] +
               [m.to_simple_dic(quiet) for m in self.modules] +
               [e.to_simple_dic(quiet) for e in self.enums] +
               [u.to_simple_dic(quiet) for u in self.unions] +
               [t.to_simple_dic(quiet) for t in self.typedefs] +
               [t.to_simple_dic(quiet) for t in self.consts]}
        return dic

    def to_dic(self):
        dic = { 'name' : self.name,
                'filepath' : self.filepath,
                'classname' : self.classname,
                'interfaces' : [i.to_dic() for i in self.interfaces],
                'typedefs' : [t.to_dic() for t in self.typedefs],
                'structs' : [s.to_dic() for s in self.structs],
                'enums' : [e.to_dic() for e in self.enums],
                'unions' : [u.to_dic() for u in self.unions],
                'modules' : [m.to_dic() for m in self.modules],
                'consts' : [c.to_dic() for c in self.consts],
                'annotations':[a.to_dic() for a in self._annotations] }
        return dic


    def parse_tokens(self, token_buf, filepath=None):
        self._filepath = filepath
        if not self.name == global_namespace:
            ln, fn, kakko = token_buf.pop()
            if not kakko == '{':
                if self._verbose: sys.stdout.write('# Error. No kakko "{".\n')
                raise exception.InvalidIDLSyntaxError()
        annotation_found = False
        annotations = ''
        keywords = ['module', 'typedef', 'struct', 'interface', 'enum', 'union', 'const']
        if self.full_path == 'stanag4817::p7::catl_json::core::basic_types::contact':
            print('stop')
        while True:
            ln, fn, token = token_buf.pop()         
            if token != None:
                if token.find('@') > -1 and token != '@annotation':
                    annotation_found = True
                    annotations += token
                    while True:
                        ln, fn, t = token_buf.pop()                        
                        if t in keywords:
                            token = t
                            break
                        annotations += ' '+ t
            if token == None:
                if self.name in self._global_module._processed_modules:
                    break
                if self._verbose: sys.stdout.write('# Error. No kokka "}".\n')
                raise exception.InvalidIDLSyntaxError()                
            elif token == 'module':
                ln, fn, name_ = token_buf.pop()
                m = self.module_by_name(name_)                
                if m == None:
                    m = IDLModule(name_, self)
                    self._modules.append(m)
                    self._global_module._processed_modules +=[name_]
                    m.parse_tokens(token_buf, filepath=filepath)
                    if annotation_found:
                        parts = annotations.strip().split('@')
                        for part in parts:
                            v = node.IDLAnnotation('@'+part)
                            if v.annotation_type != node.AnnotationType.UNKNOWN:
                                m._annotations += [v]
                        annotations = ''
                        annotation_found = False
                else:
                    m.parse_tokens(token_buf, filepath=filepath)
            elif token == 'typedef':
                blocks = []
                while True:
                    ln, fn, t = token_buf.pop()
                    if t == None:
                        raise exception.InvalidIDLSyntaxError()
                    elif t == ';':
                        break
                    else:
                        blocks.append(t)
                t = typedef.IDLTypedef(self)
                self._typedefs.append(t)
                t.parse_blocks(blocks, filepath=filepath)
            elif token == 'struct':
                ln, fn, name_ = token_buf.pop()                
                s_ = self.struct_by_name(name_)
                s = struct.IDLStruct(name_, self)
                s.parse_tokens(token_buf, filepath=filepath)
                if s.forward_decl == False:
                    if annotation_found:
                        parts = annotations.strip().split('@')
                        for part in parts:
                            v = node.IDLAnnotation('@'+part)
                            if v.annotation_type != node.AnnotationType.UNKNOWN:
                                s._annotations += [v]
                        annotations = ''
                        annotation_found = False
                    if s_:
                        if self._verbose: sys.stdout.write('# Error. Same Struct Defined (%s)\n' % name_)
                        raise exception.InvalidIDLSyntaxError()
                    else:
                        self._structs.append(s)
                else:
                    self._forward_decls.append(s)
            elif token == 'interface':
                ln, fn, name_ = token_buf.pop()
                s = interface.IDLInterface(name_, self)
                s.parse_tokens(token_buf, filepath=filepath)

                s_ = self.interface_by_name(name_)
                if s_:
                    if self._verbose: sys.stdout.write('# Error. Same Interface Defined (%s)\n' % name_)
                    raise exception.InvalidIDLSyntaxError()
                else:
                    self._interfaces.append(s)
            elif token == 'enum':
                ln, fn, name_ = token_buf.pop()
                s = enum.IDLEnum(name_, self)
                s.parse_tokens(token_buf, filepath)
                s_ = self.enum_by_name(name_)
                if s_:
                    if self._verbose: sys.stdout.write('# Error. Same Enum Defined (%s)\n' % name_)
                    raise exception.InvalidIDLSyntaxError()
                else:
                    self._enums.append(s)
            elif token == 'union':
                ln, fn, name_ = token_buf.pop()
                s = union.IDLUnion(name_, self)
                s.parse_tokens(token_buf, filepath)
                if s.forward_decl == False:                    
                    s_ = self.union_by_name(name_)
                    if s_:
                        if self._verbose: sys.stdout.write('# Error. Same Union Defined (%s)\n' % name_)
                        raise exception.InvalidIDLSyntaxError()
                    else:
                        self._unions.append(s)
                else:
                    self._forward_decls.append(s)
            elif token == 'const':
                values = []
                while True:
                    ln, fn, t = token_buf.pop()
                    if t == ';':
                        break
                    values.append(t)
                s = const.IDLConst(values, self, filepath=filepath)
                s_ = self.const_by_name(name_)
                if s_:
                    if self._verbose: sys.stdout.write('# Error. Same Const Defined (%s)\n' % name_)
                else:
                    self._consts.append(s)
            elif token == '@annotation':
                #skip annotation definitions
                while True:
                    ln, fn, token = token_buf.pop()
                    if token == None:
                        if self._verbose: sys.stdout.write('# Error. No kokka "}".\n')
                        raise exception.InvalidIDLSyntaxError()
                    elif token == '}':
                        ln, fn, token = token_buf.pop()
                        if not token == ';':
                            if self._verbose: sys.stdout.write('# Error. No semi-colon after "}".\n')
                            raise exception.InvalidIDLSyntaxError()
                        break                
            elif token == '}':
                break

        return True



    @property
    def modules(self):
        return self._modules

    def module_by_name(self, name):
        for m in self.modules:
            if m.name == name:
                return m
        return None

    def for_each_module(self, func):
        retval = []
        for m in self.modules:
            retval.append(func(m))
        return retval

    @property
    def interfaces(self):
        return self._interfaces

    def interface_by_name(self, name):
        for i in self.interfaces:
            if i.name == name:
                return i
        return None

    def for_each_interface(self, func):
        retval = []
        for m in self.interfaces:
            retval.append(func(m))
        return retval

    @property
    def structs(self):
        return self._structs

    def struct_by_name(self, name):
        for s in self.structs:
            if s.name == name:
                return s
        return None

    def for_each_struct(self, func, filter=None):
        retval = []
        for m in self.structs:
            if filter:
                if filter(m):
                    retval.append(func(m))
                pass
            else:
                retval.append(func(m))
        return retval
    def for_each_forward_decl(self, func):
        retval = []
        for m in self._forward_decls:
            retval.append(func(m))
        return retval
    @property
    def enums(self):
        return self._enums

    def enum_by_name(self, name):
        for e in self.enums:
            if e.name == name:
                return e
        return None

    def for_each_enum(self, func):
        retval = []
        for m in self.enums:
            retval.append(func(m))
        return retval

    @property
    def unions(self):
        return self._unions

    def union_by_name(self, name):
        for u in self.unions:
            if u.name == name:
                return u
        return None

    def for_each_union(self, func):
        retval = []
        for m in self.unions:
            retval.append(func(m))
        return retval

    @property
    def consts(self):
        return self._consts

    def const_by_name(self, name):
        for c in self.consts:
            if c.name == name:
                return c
        return None

    def for_each_const(self, func):
        retval = []
        for m in self.consts:
            retval.append(func(m))
        return retval


    @property
    def typedefs(self):
        return self._typedefs

    def typedef_by_name(self, name):
        for t in self.typedefs:
            if t.name == name:
                return t
        return None

    def for_each_typedef(self, func):
        retval = []
        for m in self.typedefs:
            retval.append(func(m))

    def find_types(self, full_typename, parent=None):
        if type.is_primitive(full_typename):
            return [type.IDLType(full_typename, self)]
        typenode = []
        res = self._found_types.get(full_typename, None)
        if res:
            return res
        def parse_node(s, name=str(full_typename)):
            if parent:
                if parent.full_path + '::' + name.strip() == s.full_path or name.strip() == s.full_path:
                    typenode.append(s)
                else:
                    if s.name.find(name.strip()) > -1 or s.full_path.find(name.strip()) > -1:
                        typenode.append(s)
            else:
                if s.name == name.strip() or s.full_path == name.strip():
                    typenode.append(s)
                else:
                    if s.name.find(name.strip()) > -1 or s.full_path.find(name.strip()) > -1:
                        typenode.append(s)

        def parse_module(m):
            m.for_each_module(parse_module)
            m.for_each_struct(parse_node)
            m.for_each_typedef(parse_node)
            m.for_each_enum(parse_node)
            m.for_each_union(parse_node)
            m.for_each_interface(parse_node)
            m.for_each_forward_decl(parse_node)

        parse_module(self)
        if len(typenode) > 0:
            self._found_types[full_typename] = typenode
        return typenode
