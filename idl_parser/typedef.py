"""IDL typedefs."""
from . import node
from . import type as idl_type
sep = '::'

class IDLTypedef(node.IDLNode):
    """A ``typedef``, such as ``typedef sequence<double> DoubleSeq;``.

    :param parent: Enclosing :class:`~idl_parser.module.IDLModule`.
    """
    def __init__(self, parent):
        super(IDLTypedef, self).__init__('IDLTypedef', '', parent)
        self._verbose = True
        self._type = None

    @property
    def full_path(self):
        """Scoped name (``'M::DoubleSeq'``; ``'::DoubleSeq'`` at the global scope)."""
        return self.parent.full_path + sep + self.name

    def to_simple_dic(self, quiet=False, full_path=False, recursive=False, member_only=False):
        """A compact summary: ``'typedef TYPE NAME'``.

        :param quiet: Return only ``'typedef NAME'``.
        :param full_path: Use :attr:`full_path` as the name.
        :param recursive: Return a dict that expands a non-primitive type to its
            own summary.
        :param member_only: With ``recursive``, leave out the outer ``{NAME: ...}``.
        """
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
        """The typedef as a plain dict (for JSON or YAML output)."""
        dic = { 'name' : self.name,
                'classname' : self.classname,
                'type' : str(self.type) }
        return self._with_annotations(dic)

    @property
    def type(self):
        """The type this typedef stands for.

        A named type is resolved to its definition, as for
        :attr:`idl_parser.struct.IDLMember.type`.

        :raises ~idl_parser.exception.InvalidDataTypeException: The named type is
            not defined.
        """
        if self._type.classname == 'IDLBasicType': # Struct
            typs = self._type.resolve() # from this typedef's scope (issue #72)
            if len(typs) == 0:
                # issue #69: report an unknown type instead of an IndexError
                from . import exception
                raise exception.InvalidDataTypeException(
                    message='Can not find Data Type (%s)' % self._type.ref_name)
            return typs[0]
        return self._type

    def get_type(self, extract_typedef=False):
        """The type this typedef stands for, like :attr:`type`.

        :param extract_typedef: If that type is a typedef too, return the type
            it stands for instead (one level only).
        """
        if extract_typedef:
            if self.type.is_typedef:
                return self.type.type
        return self.type


    def parse_blocks(self, blocks, filepath=None):
        """Read the typedef from its tokens after ``typedef``, up to (not including)
        the ``;``. An array size after the name (``typedef long A[3];``) becomes
        part of the type.
        """
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
        if self._type.classname == 'IDLBasicType' and self.is_pending_forward_declaration(self._type.name):
            return # forward-declared type; resolved via .type once it is defined
        self.check_element_types(self._type) # sequence / array elements (issue #67)
        self._type._name = self.refine_typename(self.type)
