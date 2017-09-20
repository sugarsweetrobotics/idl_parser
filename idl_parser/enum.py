import os, sys, traceback

from . import node
sep = '::'

class IDLEnumValue(node.IDLNode):
    def __init__(self, value, parent):
        super(IDLEnumValue, self).__init__('IDLEnumValue', '', parent)
        self._verbose = True
        self._value = value

    def parse_blocks(self, blocks, filepath=None):
        self._filepath = filepath
        if len(blocks) == 1:
            self._name = blocks[0]
        else:
            sys.stdout.write('Unkown Enum format %s\n' % blocks)
        #name, type = self._name_and_type(blocks)
        #self._name = name
        #self._type = type

    @property
    def full_path(self):
        return self.full_path + '.' + self.name

    def to_simple_dic(self):
        dic = {self.name : self.value }
        return dic

    def to_dic(self):
        dic = { 'name' : self.name,
                'filepath' : self.filepath,
                'classname' : self.classname,
                'value' : self.value }
        return dic
    @property
    def value(self):
        return self._value




class IDLEnum(node.IDLNode):

    def __init__(self, name, parent):
        super(IDLEnum, self).__init__('IDLEnum', name, parent)
        self._verbose = True
        self._values = []

    def to_simple_dic(self, quiet=False, full_path=False, recursive=False, member_only=False):
        name = self.full_path if full_path else self.name
        if quiet:
            return 'enum %s' % name
        dic = { 'enum %s' % name : [v.to_simple_dic() for v in self.values] }
        return dic


    def to_dic(self):
        dic = { 'name' : self.name,
                'classname' : self.classname,
                'values' : [v.to_dic() for v in self.values] }
        return dic

    @property
    def full_path(self):
        return self.parent.full_path + sep + self.name

    def parse_tokens(self, token_buf, filepath=None):
        self._filepath = filepath
        self._counter = 0
        kakko = token_buf.pop()
        if not kakko == '{':
            if self._verbose: sys.stdout.write('# Error. No kakko "{".\n')
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

                if len(block_tokens) > 0:
                    self._parse_block(block_tokens)
                break

            if token == ',':
                self._parse_block(block_tokens)
                block_tokens = []
                continue
            block_tokens.append(token)

    def _parse_block(self, blocks):
        v = IDLEnumValue(self._counter, self)
        self._counter = self._counter+ 1
        v.parse_blocks(blocks, self.filepath)
        self._values.append(v)

    @property
    def values(self):
        return self._values


    def value_by_name(self, name):
        for m in self.values:
            if m.name == name:
                return m
        return None
