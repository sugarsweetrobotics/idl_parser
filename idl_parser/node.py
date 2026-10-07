class IDLNode(object):
    def __init__(self, classname, name, parent):
        self._classname = classname
        self._parent = parent
        self._name = name
        self._filepath = None
        self.sep = '::'

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
        type = ''
        for t in blocks[:-1]:
            type = type + ' ' + t
        type = type.strip()
        return (name, type)

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

    def is_pending_forward_interface(self, typename):
        """True if typename names an interface that has been forward-declared
        ("interface A;") but whose definition has not been parsed yet.

        Such a type may legally be used (e.g. as a member, typedef or argument
        type) before its definition, so it must not be reported as unknown.
        """
        name = str(typename).strip()
        if name.startswith(self.sep):
            name = name[len(self.sep):]
        if len(self.root_node.find_types(name)) > 0:
            return False
        found = []
        def walk(m):
            prefix = m.full_path.lstrip(':')
            for n in getattr(m, 'forward_interfaces', []):
                full = prefix + self.sep + n if prefix else n
                if name == n or name == full:
                    found.append(full)
            for sub in getattr(m, 'modules', []):
                walk(sub)
        walk(self.root_node)
        return len(found) > 0

    def refine_typename(self, typ):
        global_module = self.root_node
        if typ.name.find('sequence') >= 0:
            name = typ.name[typ.name.find('<')+1 : typ.name.find('>')].strip()
            typs = global_module.find_types(name)
            if len(typs) == 0:
                # Not resolvable yet (e.g. a forward-declared interface): keep the inner name
                return 'sequence < ' + name + ' >'

            return 'sequence < ' + typs[0].name + ' >'
        else:
            typs = global_module.find_types(typ.name)
            if len(typs) == 0:
                return typ.name
            else:
                return typs[0].name
