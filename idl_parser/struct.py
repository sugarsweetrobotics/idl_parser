import os, sys, traceback
from . import node
from . import type as idl_type
from . import exception
from . import union
class IDLMember(node.IDLNode):
    def __init__(self, parent):
        super(IDLMember, self).__init__('IDLMember', '', parent)
        self._verbose = True
        self._type = None
        self.sep = '::'

    @property
    def full_path(self):
        return self.parent.full_path + self.sep + self.name

    def parse_blocks(self, blocks, filepath=None):
        self._filepath = filepath
        name, typ = self._name_and_type(blocks)
        if name.find('[') >= 0:
            name_ = name[:name.find('[')]
            typ = typ.strip() + ' ' + name[name.find('['):]
            name = name_
        self._name = name
        self._type = idl_type.IDLType(typ, self)

    def to_simple_dic(self, recursive=False, member_only=False):
        if recursive:
            if self.type.is_primitive:
                return str(self.type) + ' ' + self.name
            elif self.type.obj.is_enum:
                return str('enum') + ' ' + self.name
            dic = {str(self.type) +' ' + self.name :
                   self.type.obj.to_simple_dic(recursive=recursive, member_only=True)}
            return dic
        dic = {self.name : str(self.type) }
        return dic

    def to_dic(self):
        dic = { 'name' : self.name,
                'filepath' : self.filepath,
                'classname' : self.classname,
                'type' : str(self.type),
                'annotations' : [a.to_dic() for a in self._annotations]}
        return dic

    @property
    def type(self):
        if self._type.classname == 'IDLBasicType': # Struct
            typs = self.root_node.find_types(self._type.name)
            if len(typs) == 0:
                print('Can not find Data Type (%s)\n' % self._type.name)
                raise exception.InvalidDataTypeException()
            elif len(typs) > 1:
                typs = self.root_node.find_types(self._type.name, parent=self.parent.parent)
                if len(typs) == 0:
                    print('Can not find Data Type (%s)\n' % self._type.name)
                    raise exception.InvalidDataTypeException()

            return typs[0].name
        return self._type.name
    @property
    def key(self):
        return len([a for a in self._annotations if a.type == node.AnnotationType.KEY ]) > 0
    @property
    def optional(self):
        return len([a for a in self._annotations if a.type == node.AnnotationType.OPTIONAL ]) > 0
    
    def get_type(self, extract_typedef=False):
        if extract_typedef:
            if self.type.is_typedef:
                return self.type.type
        return self.type


    def post_process(self):
        try:
            self._type._name = self.refine_typename(self.type)
        except:
            pass


class IDLStruct(node.IDLNode):

    def __init__(self, name, parent):
        super(IDLStruct, self).__init__('IDLStruct', name.split()[-1].strip(), parent)
        self._verbose = False #True
        self._members = []
        self.sep = '::'
        self.base = None

    @property
    def full_path(self):
        return (self.parent.full_path + self.sep + self.name).strip()

    def to_simple_dic(self, quiet=False, full_path=False, recursive=False, member_only=False):
        name = self.full_path if full_path else self.name
        if quiet:
            return 'struct %s' % name

        dic = { 'struct %s' % name : [v.to_simple_dic(recursive=recursive) for v in self.members] }

        if member_only:
            return dic.values()[0]
        return dic


    def to_dic(self):
        dic = { 'name' : self.name,
                'classname' : self.classname,
                'full_path' : self.full_path,
                'members' : [v.to_dic() for v in self.members],
                'annotations': [str(a) for a in self._annotations]}
        return dic

    def parse_tokens(self, token_buf, filepath=None):
        self._filepath = filepath
        ln, fn, kakko = token_buf.pop()

        if kakko == ':':
            ln, fn, kakko = token_buf.pop()
            self.base = kakko
            ln, fn, kakko = token_buf.pop()

        if not kakko == '{':
            if self._verbose: sys.stdout.write('# Error. No kakko "{".\n')
            raise exception.InvalidIDLSyntaxError()

        block_tokens = []
        while True:

            ln, fn, token = token_buf.pop()
            if token == None:
                if self._verbose: sys.stdout.write('# Error. No kokka "}".\n')
                raise exception.InvalidIDLSyntaxError()
            elif token == 'struct':
                ln, fn, name_ = token_buf.pop()
                s = IDLStruct(name_, self)
                s.parse_tokens(token_buf, filepath=filepath)
                v = node.IDLAnnotation(' '.join(block_tokens))
                if v.annotation_type != node.AnnotationType.UNKNOWN:
                    s._annotations += [v]
                a =  self.parent.classname
                if self.parent.classname == 'IDLModule': 
                    self.parent._structs +=[s]
                else:
                    self.parent.parent._structs +=[s]
                block_tokens=[]
            elif token == 'union':
                ln, fn, name_ = token_buf.pop()
                s = union.IDLUnion(name_, self)
                s.parse_tokens(token_buf, filepath=filepath)
                s._annotations = [' '.join(block_tokens)]
                a =  self.parent.classname
                if self.parent.classname == 'IDLModule': 
                    self.parent._structs +=[s]
                else:
                    self.parent.parent._structs +=[s]
                block_tokens=[]

            elif token == '}':
                ln2, fn2, token = token_buf.pop()
                if not token == ';':
                    if self._verbose: sys.stdout.write('# Error. No semi-colon after "}".\n')
                    raise exception.InvalidIDLSyntaxError(ln, fn, 'No semi-colon after "}"')
                break

            if token == ';':
                self._parse_block(block_tokens)
                block_tokens = []
                continue
            block_tokens.append(token)

        self._post_process()

    def _parse_block(self, blocks):
        v = IDLMember(self)
        v.parse_blocks(blocks, self.filepath)
        self._members.append(v)

    def _post_process(self):
        self.forEachMember(lambda m : m.post_process())
    @property
    def members(self):
        return self._members
    
    @property
    def topic(self):
        return len([a for a in self._annotations if a.type == node.AnnotationType.TOPIC ]) > 0
    
    def member_by_name(self, name):
        for m in self._members:
            if m.name == name:
                return m

        return None
    def forEachMember(self, func):
        for m in self._members:
            func(m)
