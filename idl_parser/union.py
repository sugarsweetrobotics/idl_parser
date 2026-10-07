import os, sys, traceback

from . import node
from . import type as idl_type
from . import exception

class IDLUnionMember(node.IDLNode):
    def __init__(self, parent):
        super(IDLUnionMember, self).__init__('IDLUnionMember', '', parent)
        self._verbose = True
        self._type = None
        self._descriminator_value_associations = []
        self._is_default = False
        self.sep = '::'

    @property
    def full_path(self):
        return self.parent.full_path + self.sep + self.name

    def parse_blocks(self, blocks, filepath=None):
        self._filepath = filepath

        annotations, blocks = node.parse_annotations(blocks)
        self._add_annotations(annotations)
        while blocks:
            if blocks[0] == 'case':
                blocks.pop(0)
                if len(blocks) < 2:
                    if self._verbose: sys.stdout.write('# Error. No value after "case".\n')
                    raise exception.InvalidIDLSyntaxError()
                self._descriminator_value_associations.append(blocks.pop(0))
            elif blocks[0] == 'default':
                blocks.pop(0)
                self._is_default = True
            else:
                break
            if not blocks or blocks.pop(0) != ':':
                if self._verbose: sys.stdout.write('# Error. No ":" after case label.\n')
                raise exception.InvalidIDLSyntaxError()

        annotations, blocks = node.parse_annotations(blocks)
        self._add_annotations(annotations)
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
                'is_default' : self.is_default,
                'filepath' : self.filepath,
                'classname' : self.classname,
                'type' : self.type.name }
        return self._with_annotations(dic)

    @property
    def type(self):
        if self._type.classname == 'IDLBasicType': # Union
            typs = self.root_node.find_types(self._type.name)
            if len(typs) == 0:
                print('Can not find Data Type (%s)\n' % self._type.name)
                raise exception.InvalidDataTypeException()
            return typs[0]
        return self._type

    @property
    def descriminator_value_associations(self):
        """The ``case`` label values that select this member (``default`` is not included)."""
        return self._descriminator_value_associations

    @property
    def is_default(self):
        """True if this member has the ``default:`` label."""
        return self._is_default

    def get_type(self, extract_typedef=False):
        if extract_typedef:
            if self.type.is_typedef:
                return self.type.type
        return self.type

    def post_process(self):
        if self._type.classname == 'IDLBasicType' and self.is_pending_forward_declaration(self._type.name):
            return # forward-declared type; resolved via .type once it is defined
        self.check_element_types(self._type) # sequence / array elements (issue #67)
        self._type._name = self.refine_typename(self.type)

class IDLUnion(node.IDLNode):

    def __init__(self, name, parent):
        super(IDLUnion, self).__init__('IDLUnion', name.strip(), parent)
        self._verbose = True
        self._descriminator_kind = None
        self._members = []
        self._forward = False
        self.sep = '::'

    @property
    def is_forward(self):
        """True if this node came from a forward declaration ("union A;")."""
        return self._forward

    @property
    def full_path(self):
        return (self.parent.full_path + self.sep + self.name).strip()

    def to_simple_dic(self, quiet=False, full_path=False, recursive=False, member_only=False):
        name = self.full_path if full_path else self.name
        if quiet:
            return 'union %s' % name

        dic = { 'union %s' % name : [v.to_simple_dic(recursive=recursive) for v in self.members] }

        if member_only:
            return list(dic.values())[0]
        return dic

    def to_dic(self):
        dic = { 'name' : self.name,
                'classname' : self.classname,
                'descriminator_kind' : self.descriminator_kind,
                'members' : [v.to_dic() for v in self.members] }
        return self._with_annotations(dic)

    def parse_tokens(self, token_buf, filepath=None):
        self._filepath = filepath

        if token_buf.peek()[2] == ';': # Forward declaration (union A;)
            token_buf.pop()
            self._forward = True
            return

        self.parse_descriminator_kind(token_buf)

        ln, fn, token = token_buf.pop()
        if token != '{':
            if self._verbose: sys.stdout.write('# Error. No kokka "{".\n')
            raise exception.InvalidIDLSyntaxError()

        block_tokens = []
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

            if token == ';':
                self._parse_block(block_tokens)
                block_tokens = []
                continue
            block_tokens.append(token)

        self._post_process()

    def parse_descriminator_kind(self, token_buf):
        ln, fn, token = token_buf.pop()
        if token != 'switch':
            if self._verbose: sys.stdout.write('# Error. Union definition missing "switch".\n')
            raise exception.InvalidIDLSyntaxError()
        ln, fn, token = token_buf.pop()
        if token != '(':
            if self._verbose: sys.stdout.write('# Error. No "(".\n')
            raise exception.InvalidIDLSyntaxError()
        ln, fn, token = token_buf.pop()
        self._descriminator_kind = token
        ln, fn, token = token_buf.pop()
        if token != ')':
            if self._verbose: sys.stdout.write('# Error. No ")".\n')
            raise exception.InvalidIDLSyntaxError()

    def _parse_block(self, blocks):
        v = IDLUnionMember(self)
        v.parse_blocks(blocks, self.filepath)
        if v.is_default and self.default_member is not None:
            if self._verbose: sys.stdout.write('# Error. Union "%s" has more than one "default" label.\n' % self.name)
            raise exception.InvalidIDLSyntaxError()
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

    @property
    def default_member(self):
        """The member with the ``default:`` label, or None."""
        for m in self._members:
            if m.is_default:
                return m
        return None

    def forEachMember(self, func):
        for m in self._members:
            func(m)
