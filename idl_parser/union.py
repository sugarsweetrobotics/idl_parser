import os, sys, traceback

from . import node
from . import type as idl_type


class IDLUnionMember(node.IDLNode):
    def __init__(self, parent):
        super(IDLUnionMember, self).__init__('IDLUnionMember', '', parent)
        self._verbose = True
        self._type = None
        self._descriminator_value_associations = []
        self.sep = '::'

    @property
    def full_path(self):
        return self.parent.full_path + self.sep + self.name

    def parse_blocks(self, blocks, filepath=None):
        self._filepath = filepath

        while True:
            if blocks[0] != 'case':
                break
            blocks.pop(0)
            token = blocks.pop(0)
            self._descriminator_value_associations.append(token)
            token = blocks.pop(0)
            if token != ':':
                if self._verbose: sys.stdout.write('# Error. No ":" after case value.\n')
                raise InvalidDataTypeException()

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
                'descriminator_value_associations' : self.descriminator_value_associations,
                'filepath' : self.filepath,
                'classname' : self.classname,
                'type' : self.type.name }
        return dic

    @property
    def type(self):
        if self._type.classname == 'IDLBasicType': # Union
            typs = self.root_node.find_types(self._type.name)
            if len(typs) == 0:
                print('Can not find Data Type (%s)\n' % self._type.name)
                raise InvalidDataTypeException()
            return typs[0]
        return self._type

    @property
    def descriminator_value_associations(self):
        return self._descriminator_value_associations

    def get_type(self, extract_typedef=False):
        if extract_typedef:
            if self.type.is_typedef:
                return self.type.type
        return self.type

    def post_process(self):
        self._type._name = self.refine_typename(self.type)

class IDLUnion(node.IDLNode):

    def __init__(self, name, parent):
        super(IDLUnion, self).__init__('IDLUnion', name.strip(), parent)
        self._verbose = True
        self._descriminator_kind = None
        self._members = []
        self.sep = '::'

    @property
    def full_path(self):
        return (self.parent.full_path + self.sep + self.name).strip()

    def to_simple_dic(self, quiet=False, full_path=False, recursive=False, member_only=False):
        name = self.full_path if full_path else self.name
        if quiet:
            return 'union %s' % name

        dic = { 'union %s' % name : [v.to_simple_dic(recursive=recursive) for v in self.members] }

        if member_only:
            return dic.values()[0]
        return dic

    def to_dic(self):
        dic = { 'name' : self.name,
                'classname' : self.classname,
                'descriminator_kind' : self.descriminator_kind,
                'members' : [v.to_dic() for v in self.members] }
        return dic

    def parse_tokens(self, token_buf, filepath=None):
        self._filepath = filepath

        self.parse_descriminator_kind(token_buf)

        token = token_buf.pop()
        if token != '{':
            if self._verbose: sys.stdout.write('# Error. No kokka "{".\n')
            raise InvalidIDLSyntaxError()

        block_tokens = []
        while True:

            token = token_buf.pop()
            if token == None:
                if self._verbose: sys.stdout.write('# Error. No kokka "}".\n')
                raise InvalidIDLSyntaxError()

            elif token == '}':
                token = token_buf.pop()
                if not token == ';':
                    if self._verbose: sys.stdout.write('# Error. No semi-colon after "}".\n')
                    raise InvalidIDLSyntaxError()
                break

            if token == ';':
                self._parse_block(block_tokens)
                block_tokens = []
                continue
            block_tokens.append(token)

        self._post_process()

    def parse_descriminator_kind(self, token_buf):
        token = token_buf.pop()
        if token != 'switch':
            if self._verbose: sys.stdout.write('# Error. Union definition missing "switch".\n')
            raise InvalidIDLSyntaxError()
        token = token_buf.pop()
        if token != '(':
            if self._verbose: sys.stdout.write('# Error. No "(".\n')
            raise InvalidIDLSyntaxError()
        token = token_buf.pop()
        self._descriminator_kind = token
        token = token_buf.pop()
        if token != ')':
            if self._verbose: sys.stdout.write('# Error. No ")".\n')
            raise InvalidIDLSyntaxError()

    def _parse_block(self, blocks):
        v = IDLUnionMember(self)
        v.parse_blocks(blocks, self.filepath)
        self._members.append(v)

    def _post_process(self):
        self.forEachMember(lambda m : m.post_process())

    @property
    def members(self):
        return self._members

    @property
    def descriminator_kind(self):
        return self._descriminator_kind

    def member_by_name(self, name):
        for m in self._members:
            if m.name == name:
                return m

        return None
    def forEachMember(self, func):
        for m in self._members:
            func(m)
