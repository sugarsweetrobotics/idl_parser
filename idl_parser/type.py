import os, sys, traceback

from . import node
from . import exception

sep = '::'

primitive = [
    'boolean',
    'char', 'byte', 'octet',
    'short', 'wchar',
    'long',
    'float',
    'double',
    'string',
    'wstring']

def is_primitive(name):
    for n in name.split(' '):
        if n in primitive:
            return True
    return False

def IDLType(name, parent):
    if name == 'void':
        return IDLVoid(name, parent)

    elif name.find('sequence') >= 0:
        return IDLSequence(name, parent)
    elif name.find('[') >= 0:
        return IDLArray(name, parent)

    if is_primitive(name):
        return IDLPrimitive(name, parent)

    return IDLBasicType(name, parent)

class IDLTypeBase(node.IDLNode):
    def __init__(self, classname, name, parent):
        super(IDLTypeBase, self).__init__(classname, name, parent.root_node)
        self._is_sequence = False
        self._is_primitive = False

    def __str__(self):
        return self.name

    @property
    def is_sequence(self):
        return self._is_sequence

    @property
    def is_primitive(self):
        return self._is_primitive


class IDLVoid(IDLTypeBase):
    def __init__(self, name, parent):
        super(IDLVoid, self).__init__('IDLVoid', name, parent.root_node)
        self._verbose = True

class IDLSequence(IDLTypeBase):
    def __init__(self, name, parent):
        super(IDLSequence, self).__init__('IDLSequence', name, parent.root_node)
        self._verbose = True
        if name.find('sequence') < 0:
            raise InvalidIDLSyntaxError()
        typ_ = name[name.find('<')+1 : name.find('>')].strip()
        self._type = IDLType(typ_, parent)
        self._is_primitive = False #self.inner_type.is_primitive
        self._is_sequence = True

    @property
    def inner_type(self):
        return self._type

    def __str__(self):
        return 'sequence<%s>' % str(self.inner_type)

    @property
    def obj(self):
        return self


    def __hoge(self):
        global_module = self.root_node
        typs = global_module.find_types(self.inner_type)
        # print self.inner_type
        if len(typs) == 0:
            # print 'None'
            return None
        else:
            # print typs[0]
            return typs[0]

    @property
    def type(self):
        return self._type

    @property
    def full_path(self):
        return self.parent.full_path + sep + self.name

    def to_simple_dic(self, quiet=False, full_path=False, recursive=False, member_only=False):
        name = self.full_path if full_path else self.name
        if quiet:
            return 'sequence<%s>' % str(self.inner_type)

        if recursive:
            if self.type.is_primitive:
                return { 'sequence<%s>' % str(self.type) : str(self.type)}
            else:
                return { 'sequence<%s>' % str(self.type) : self.type.obj.to_simple_dic(recursive=recursive, member_only=True)}
        """
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
        """

    def to_dic(self):
        dic = { 'name' : self.name,
                'classname' : self.classname,
                'type' : str(self.type) }
        return dic

class IDLArray(IDLTypeBase):
    def __init__(self, name, parent):
        super(IDLArray, self).__init__('IDLArray', name.strip(), parent.root_node)

        self._verbose = True
        if name.find('[') < 0:
            raise InvalidIDLSyntaxError()
        primitive_type_name = name[:name.find('[')]
        size = name[name.find('[')+1 : name.find(']')]
        inner_type_name = primitive_type_name + name[name.find(']')+1:]

        size_literal = self.parse_size(size)

        self._size = size_literal
        self._type = IDLType(inner_type_name.strip(), parent)
        self._is_primitive = False #self.inner_type.is_primitive
        self._is_sequence = False
        self._is_array = True


    @property
    def inner_type(self):
        return self._type

    @property
    def primitive_type(self):
        if self.inner_type.is_array:
            return self.inner_type.primitive_type
        else:
            return self.inner_type

    def __str__(self):
        n = ['%s' % self.primitive_type.name]
        def _apply_size(typ):
            n[0] = n[0] + '[%s]' % typ.size
            if typ.inner_type.is_array:
                _apply_size(typ.inner_type)

        _apply_size(self)
        return n[0]

    @property
    def obj(self):
        return self

    @property
    def size(self):
        return self._size

    def __hoge(self):
        global_module = self.root_node
        typs = global_module.find_types(self.inner_type)
        # print self.inner_type
        if len(typs) == 0:
            # print 'None'
            return None
        else:
            # print typs[0]
            return typs[0]

    def parse_size(self, size):
        is_const_type = None

        if self.root_node.modules:
            is_const_type = self.root_node.modules[-1].const_by_name(size)
        else:
            is_const_type = self.root_node.const_by_name(size)

        # maybe there are modules but the constant is defined at a global scope?
        if not is_const_type:
            is_const_type = self.root_node.const_by_name(size)

        size_literal = None

        if is_const_type:
            size_literal = is_const_type.value
        else:
            size_literal = size

        try:
            size_literal = int(size_literal)
        except:
            if self._verbose: sys.stdout.write(
                "# Error. Array index '%s' not an integer.\n" % size_literal)
            raise exception.InvalidDataTypeException()

        return size_literal

    @property
    def type(self):
        return self._type

    @property
    def full_path(self):
        return self.parent.full_path + sep + self.name

    def to_simple_dic(self, quiet=False, full_path=False, recursive=False, member_only=False):
        name = self.full_path if full_path else self.name
        if quiet:
            return str(self)

        if recursive:
            if self.type.is_primitive:
                return str(self)
            else:
                return str(self)
        """
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
        """

    def to_dic(self):
        dic = { 'name' : self.name,
                'classname' : self.classname,
                'type' : str(self.type) }
        return dic


class IDLPrimitive(IDLTypeBase):
    def __init__(self, name, parent):
        super(IDLPrimitive, self).__init__('IDLPrimitive', name, parent.root_node)
        self._verbose = True
        self._is_primitive = True
    @property
    def full_path(self):
        return (self.parent.full_path + self.sep + self.name).strip()
class IDLBasicType(IDLTypeBase):
    def __init__(self, name, parent):
        super(IDLBasicType, self).__init__('IDLBasicType', name, parent.root_node)
        self._verbose = True
        #if self.name.find('['):
        #    self._name = self.name[self.name.find('[')+1:]
        self._name = self.refine_typename(self)

    @property
    def obj(self):
        global_module = self.root_node
        typs = global_module.find_types(self.name)
        if len(typs) == 0:
            return None
        else:
            return typs[0]
