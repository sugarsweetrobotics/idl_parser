from . import node
from . import type as idl_type
sep = '::'

class IDLTypedef(node.IDLNode):

    def __init__(self, parent):
        super(IDLTypedef, self).__init__('IDLTypedef', '', parent)
        self._verbose = True
        self._type = None

    @property
    def full_path(self):
        return self.parent.full_path + sep + self.name

    def to_simple_dic(self, quiet=False, full_path=False, recursive=False, member_only=False):
        name = self.full_path if full_path else self.name
        if quiet:
            return 'typedef ' + name

        if recursive:
            n = 'typedef ' + str(self.type) +' ' + name
            if not self.type.is_primitive:
                dic = { n : (self.type.obj.to_simple_dic(recursive=recursive, member_only=True))}
            else:
                dic = { n : str(self.type) }
            if member_only:
                return dic
            return {name : dic}

        dic = 'typedef %s %s' % (self.type, name)
        return dic

    def to_dic(self):
        dic = { 'name' : self.name,
                'classname' : self.classname,
                'type' : str(self.type) }
        return dic

    @property
    def type(self):
        if self._type.classname == 'IDLBasicType': # Struct
            return self.root_node.find_types(self._type.name)[0]
        return self._type

    def get_type(self, extract_typedef=False):
        if extract_typedef:
            if self.type.is_typedef:
                return self.type.type
        return self.type


    def parse_blocks(self, blocks, filepath=None):
        self._filepath = filepath
        type_name_ = ''
        rindex = 1
        name = blocks[-rindex]
        while True:
            if name.find('[') < 0:
                break

            if name.find('[') > 0:
                type_name_ = name[name.find('['):]
                name = name[:name.find('[')]
                #rindex = rindex + 1
                break

            type_name_ = name + type_name_
            rindex = rindex + 1
            name = blocks[-rindex]

        type_name = ''
        for t in blocks[:-rindex]:
            type_name = type_name + ' ' + t
        type_name = type_name + ' ' + type_name_
        type_name = type_name.strip()

        self._type = idl_type.IDLType(type_name, self)
        self._name = name

        self._post_process()

    def _post_process(self):
        self._type._name = self.refine_typename(self.type)
