
from enum import Enum
from typing import Any
class AnnotationType(Enum):
    UNKNOWN=-1
    KEY = 0
    OPTIONAL = 1
    RANGE = 2
    BIT_BOUND = 3
    UNIT = 4
    DEFAULT = 5
    TOPIC = 6
    JAUS_DOUBLE = 7
    JAUS_INTEGER = 8
    JAUS_INTEGER_FUNCTION = 9
    JAUS_PRESENCE_VECTOR = 10
    JAUS_EXTENDS = 11
    JAUS_PRESENCE_VECTOR_FIELD = 12
    JAUS_RECOMMENDED_QUERY = 13

class IDLAnnotation(object):
    def __init__(self, value) -> None:
        self.tokens = []
        self.data_ = {}
        self.value_ = None
        if len(value) == 0 or value.lower() == 'struct':
            self.type_ = AnnotationType.UNKNOWN
        else:
            self.tokens = value.split()
            self.name_ = self.tokens[0].strip('@').split('::')[-1]
            self.tokens = self.tokens[1:]
            if self.name_.upper() in AnnotationType.__dict__.keys():
                self.type_ = AnnotationType[self.name_.upper()]
            else:
                self.type_ = AnnotationType.UNKNOWN
            if self.type_ in [AnnotationType.UNIT, AnnotationType.DEFAULT]:
                self.tokens = self.tokens[self.tokens.index('(')+1:self.tokens.index(')')]
                self.value_ = ' '.join(self.tokens).strip('"')
            elif self.type_ == AnnotationType.RANGE:
                self.tokens = self.tokens[self.tokens.index('(')+1:self.tokens.index(')')]
                self.data_['min'] = float(self.tokens[0].split('=')[-1])
                self.data_['max'] = float(self.tokens[2].split('=')[-1])
            elif self.type_ in [AnnotationType.BIT_BOUND]:
                self.tokens = self.tokens[self.tokens.index('(')+1:self.tokens.index(')')]
                self.value_ = int(self.tokens[0])
            elif self.type_ == AnnotationType.TOPIC:
                self.tokens = self.tokens[self.tokens.index('(')+1:self.tokens.index(')')]
                val = ''.join(self.tokens)
                self.tokens = val.split(',')
                for t in self.tokens:
                    t = t.split('=')
                    self.data_[t[0]] = t[1].strip('"')
            elif self.type_ in [ AnnotationType.JAUS_EXTENDS, AnnotationType.JAUS_RECOMMENDED_QUERY, AnnotationType.JAUS_INTEGER_FUNCTION]:
                self.tokens = self.tokens[self.tokens.index('(')+1:self.tokens.index(')')]
                self.value_ = self.tokens[0].strip('"')            
            else:
                pass
        for k in self.data_.keys():
            setattr(self, k, self.data_[k])    
    @property
    def type(self):
        return self.type_.name
    @property
    def annotation_type(self):
        return self.type_
    @property
    def value(self):
        return self.value_
    def __str__(self) -> str:
        data = self.to_dic()
        return str(data)
    def to_dic(self):
        data = {}
        data['type'] = self.type
        if self.value:
            data['value'] = self.value
        data.update(self.data_)
        return data
class IDLNode(object):
    def __init__(self, classname, name, parent):
        self._classname = classname
        self._parent = parent
        self._name = name
        self._filepath = None
        self.sep = '::'
        self._annotations = []

    @property
    def filepath(self):
        return self._filepath

    @property
    def is_array(self):
        return self._classname == 'IDLArray'

    @property
    def is_void(self):
        return self._classname == 'IDLVoid'

    @property
    def is_struct(self):
        return self._classname == 'IDLStruct'

    @property
    def is_typedef(self):
        return self._classname == 'IDLTypedef'

    @property
    def is_sequence(self):
        return self._classname == 'IDLSequence'

    @property
    def is_primitive(self):
        return self._classname == 'IDLPrimitive'

    @property
    def is_interface(self):
        return self._classname == 'IDLInterface'

    @property
    def is_enum(self):
        return self._classname == 'IDLEnum'

    @property
    def is_union(self):
        return self._classname == 'IDLUnion'

    @property
    def is_const(self):
        return self._classname == 'IDLConst'

    @property
    def classname(self):
        return self._classname



    @property
    def name(self):
        return self._name

    @property
    def basename(self):
        return self._name.split(self.sep)[-1]

    @property
    def basename(self):
        if self.name.find(self.sep) > 0:
            return self.name[self.name.rfind('::')+2:]
        return self.name

    @property
    def pathname(self):
        if self.name.find(self.sep) > 0:
            return self.name[:self.name.rfind('::')]
        return ''


    @property
    def parent(self):
        return self._parent

    def _name_and_type(self, blocks):
        name = blocks[-1]
        type_ = ''
        for t in blocks[:-1]:
            type_ = type_ + ' ' + t
        type_ = type_.strip()
        if type_.find('@') >=0:
            ann = type_.split('@')
            for a in ann:                
                if len(a)>0:
                    v = IDLAnnotation(('@'+a).strip())
                    if v.annotation_type != AnnotationType.UNKNOWN:
                        self._annotations += [v]
            k = type_.rfind(')')
            if k > 0:
                type_ = type_[k+1:].strip()
            else:
                type_ = ' '.join(type_.split()[1:])                    
        if type_.find('struct') >=0:
            type_ = type_[type_.find('struct')+len('struct'):].strip()
        
        return (name, type_)

    @property
    def is_root(self):
        return self.parent == None

    @property
    def root_node(self):
        roots = []
        def find_root(n):
            if n.is_root:
                roots.append(n)
            else:
                find_root(n.parent)
        find_root(self)
        return roots[0]

    def refine_typename(self, typ):
        global_module = self.root_node
        if typ.name.find('sequence') >= 0:
            name = typ.name[typ.name.find('<')+1 : typ.name.find('>')].strip()
            typs = global_module.find_types(name)
            if len(typs) == 0:
                typ__ = typ
            else:
                typ__  = typs[0]

            return 'sequence < ' + typ__.name + ' >'
        else:
            typs = global_module.find_types(typ.name)
            if len(typs) == 0:
                return typ.name
            else:
                return typs[0].name
