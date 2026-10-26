"""IDL structs, exceptions and their members."""
import os, sys, traceback

from . import node
from . import type as idl_type
from . import exception

class IDLMember(node.IDLNode):
    """A member of a struct, such as ``long x;`` or ``@key string id;``.

    :param parent: The :class:`IDLStruct` the member belongs to.
    """
    def __init__(self, parent):
        super(IDLMember, self).__init__('IDLMember', '', parent)
        self._verbose = True
        self._type = None
        self.sep = '::'

    @property
    def full_path(self):
        """Scoped name (``'M::T::x'``)."""
        return self.parent.full_path + self.sep + self.name

    @property
    def is_key(self):
        """True if annotated with ``@key`` or ``@key(TRUE)`` (not ``@key(FALSE)``).
        ``#pragma keylist`` is not considered; see :attr:`IDLStruct.keys`."""
        a = self.annotation_by_name('key')
        if a is None:
            return False
        value = a.value
        return value is None or value.strip().upper() != 'FALSE'

    def parse_blocks(self, blocks, filepath=None):
        """Read the member from its tokens (``['@key', 'long', 'x']``).

        An array size written after the name (``long a[3]``) becomes part of
        the type.
        """
        self._filepath = filepath
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
        """A compact summary: ``{name: type_name}``.

        :param recursive: Expand non-primitive types to their own summary:
            ``{'TYPE NAME': ...}``.
        """
        if recursive:
            if self.type.is_primitive:
                return str(self.type) + ' ' + self.name
            dic = {str(self.type) +' ' + self.name :
                   self.type.obj.to_simple_dic(recursive=recursive, member_only=True)}
            return dic
        dic = {self.name : str(self.type) }
        return dic

    def to_dic(self):
        """The member as a plain dict (for JSON or YAML output)."""
        dic = { 'name' : self.name,
                'filepath' : self.filepath,
                'classname' : self.classname,
                'type' : str(self.type) }
        return self._with_annotations(dic)

    @property
    def type(self):
        """Type of the member.

        A primitive, sequence or array type is an
        :class:`~idl_parser.type.IDLTypeBase`; a named type is resolved to its
        definition (:class:`IDLStruct`, :class:`~idl_parser.typedef.IDLTypedef`,
        :class:`~idl_parser.enum.IDLEnum`, ...).

        :raises ~idl_parser.exception.InvalidDataTypeException: The named type is
            not defined.
        """
        if self._type.classname == 'IDLBasicType': # Struct
            typs = self._type.resolve() # from this member's scope (issue #72)
            if len(typs) == 0:
                print('Can not find Data Type (%s)\n' % self._type.ref_name)
                raise exception.InvalidDataTypeException()
            return typs[0]
        return self._type


    def get_type(self, extract_typedef=False):
        """Type of the member, like :attr:`type`.

        :param extract_typedef: If the type is a typedef, return the type it
            stands for instead (one level only).
        """
        if extract_typedef:
            if self.type.is_typedef:
                return self.type.type
        return self.type


    def post_process(self):
        """Check the type and replace its name by the name of its definition.

        Called by :class:`IDLStruct` after all members have been read.

        :raises ~idl_parser.exception.InvalidDataTypeException: An element type
            of a sequence or array is not defined.
        """
        if self._type.classname == 'IDLBasicType' and self.is_pending_forward_declaration(self._type.name):
            return # forward-declared type; resolved via .type once it is defined
        self.check_element_types(self._type) # sequence / array elements (issue #67)
        self._type._name = self.refine_typename(self.type)


class IDLStruct(node.IDLNode):
    """A ``struct`` and its members.

    :param name: Struct name.
    :param parent: Enclosing :class:`~idl_parser.module.IDLModule`.
    """
    def __init__(self, name, parent):
        super(IDLStruct, self).__init__('IDLStruct', name.strip(), parent)
        self._verbose = False #True
        self._members = []
        self._keys = None
        self._forward = False
        self._base = None
        self.sep = '::'

    @property
    def base(self):
        """Base struct (:class:`IDLStruct`) of ``struct B : A``, or None (issue #118)."""
        return self._base

    @property
    def all_members(self):
        """Members of the base struct(s) followed by :attr:`members` (issue #118)."""
        return (self._base.all_members if self._base else []) + self._members

    @property
    def is_forward(self):
        """True if this node came from a forward declaration ("struct A;")."""
        return self._forward

    @property
    def keys(self):
        """Key member names (e.g. ``['TestID']``), from ``#pragma keylist`` and ``@key``.

        Keys of ``#pragma keylist`` come first in their order, followed by the
        members annotated with ``@key`` (or ``@key(TRUE)``) that the keylist
        does not name, in member order. When the two disagree, the keylist
        wins: a member named by the keylist is a key even with ``@key(FALSE)``.

        An empty list when the struct has no keys, or a keylist without keys
        (``#pragma keylist T``). Use :attr:`has_keylist` to tell these apart.
        """
        keys = list(self._keys) if self._keys is not None else []
        return keys + [k for k in self.annotated_keys if k not in keys]

    @property
    def has_keylist(self):
        """True if a ``#pragma keylist`` names this struct, or a member has ``@key``
        (``@key(FALSE)`` alone does not count)."""
        return self._keys is not None or len(self.annotated_keys) > 0

    @property
    def pragma_keys(self):
        """Key member names given by ``#pragma keylist`` only, or None without a keylist."""
        return list(self._keys) if self._keys is not None else None

    @property
    def annotated_keys(self):
        """Names of the members annotated with ``@key`` or ``@key(TRUE)``, in member order.
        Keys of the base struct come first (see :attr:`all_members`)."""
        return [m.name for m in self.all_members if m.is_key]

    def _set_keys(self, keys):
        self._keys = list(keys)

    @property
    def full_path(self):
        """Scoped name (``'M::T'``; ``'::T'`` at the global scope)."""
        return (self.parent.full_path + self.sep + self.name).strip()

    def to_simple_dic(self, quiet=False, full_path=False, recursive=False, member_only=False):
        """A compact summary: ``{'struct NAME': [member summaries]}``.

        The members of the base struct are listed first (:attr:`all_members`).

        :param quiet: Return only ``'struct NAME'``.
        :param full_path: Use :attr:`full_path` as the name.
        :param recursive: Expand member types (see :meth:`IDLMember.to_simple_dic`).
        :param member_only: Return only the list of member summaries.
        """
        name = self.full_path if full_path else self.name
        if quiet:
            return 'struct %s' % name

        dic = { 'struct %s' % name : [v.to_simple_dic(recursive=recursive) for v in self.all_members] }

        if member_only:
            return list(dic.values())[0]
        return dic


    def to_dic(self):
        """The struct as a plain dict (for JSON or YAML output).

        ``'members'`` are the struct's own members. ``'base'``, the full name
        of the base struct, is included when the struct has one (issue #118),
        and ``'keys'`` when the struct has keys (see :attr:`has_keylist`).
        """
        dic = { 'name' : self.name,
                'classname' : self.classname,
                'members' : [v.to_dic() for v in self.members] }
        if self._base is not None:
            dic['base'] = self._base.full_path
        if self.has_keylist:
            dic['keys'] = self.keys
        return self._with_annotations(dic)

    def parse_tokens(self, token_buf, filepath=None):
        """Parse the struct from ``token_buf``, starting after its name.

        Reads a forward declaration (``;``), or the optional base struct
        (``: Base``) and the body up to ``};``.

        :raises ~idl_parser.exception.InvalidIDLSyntaxError: The declaration is
            not valid IDL.
        :raises ~idl_parser.exception.InvalidDataTypeException: A member type is
            not defined.
        :raises ~idl_parser.exception.IDLCanNotFindException: The base struct
            is not defined.
        """
        self._filepath = filepath
        ln, fn, kakko = token_buf.pop()
        if kakko == ';': # Forward declaration (struct A;)
            self._forward = True
            return
        if kakko == ':' and self.classname == 'IDLStruct': # struct B : A (issue #118)
            ln, fn, base_name = token_buf.pop()
            self._base = self._find_base(base_name, ln, fn)
            ln, fn, kakko = token_buf.pop()
        if not kakko == '{':
            if self._verbose: sys.stdout.write('# Error. No kakko "{".\n')
            raise exception.InvalidIDLSyntaxError(ln, fn, 'No "{" in the declaration of struct "%s"' % self.name)

        block_tokens = []
        while True:

            ln, fn, token = token_buf.pop()
            if token == None:
                if self._verbose: sys.stdout.write('# Error. No kokka "}".\n')
                raise exception.InvalidIDLSyntaxError()

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
        # "long a, b[2];" declares one member per name (issue #117)
        annotations, blocks = node.parse_annotations(blocks)
        typename, declarators = node.split_declarators(blocks, 'member declaration')
        for d in declarators:
            v = IDLMember(self)
            v.parse_blocks(typename + [d], self.filepath)
            v._add_annotations(annotations)
            self._members.append(v)

    def _find_base(self, name, ln, fn):
        if name in (None, '{', ';'):
            raise exception.InvalidIDLSyntaxError(ln, fn, 'No base struct after ":" in the declaration of struct "%s"' % self.name)
        for t in self.root_node.find_types(name, scope=self.parent):
            if t.is_struct:
                return t
        raise exception.IDLCanNotFindException(
            ln, fn, 'Can not find "%s" struct which is the base of "%s"' % (name, self.name))

    def _post_process(self):
        self.forEachMember(lambda m : m.post_process())

    @property
    def members(self):
        """Members (list of :class:`IDLMember`), in order."""
        return self._members

    def member_by_name(self, name):
        """The member named ``name`` (the base struct is searched too), or None."""
        for m in self.all_members:
            if m.name == name:
                return m

        return None
    def forEachMember(self, func):
        """Call ``func`` with each member."""
        for m in self._members:
            func(m)


class IDLException(IDLStruct):
    """An ``exception`` and its members (issue #93).

    The body is read like a struct (``exception E { string msg; };``), so the
    members are available in the same way (:attr:`members`,
    :meth:`member_by_name`). An exception is not a struct: :attr:`is_struct`
    is False and :attr:`~idl_parser.node.IDLNode.is_exception` is True. The
    exceptions an operation raises are given by
    :attr:`idl_parser.interface.IDLMethod.exceptions`.

    :param name: Exception name.
    :param parent: Enclosing :class:`~idl_parser.module.IDLModule`.
    """
    def __init__(self, name, parent):
        super(IDLException, self).__init__(name, parent)
        self._classname = 'IDLException'

    def to_simple_dic(self, quiet=False, full_path=False, recursive=False, member_only=False):
        """A compact summary: ``{'exception NAME': [member summaries]}``.

        The parameters are those of :meth:`IDLStruct.to_simple_dic`.
        """
        name = self.full_path if full_path else self.name
        if quiet:
            return 'exception %s' % name
        members = [v.to_simple_dic(recursive=recursive) for v in self.members]
        if member_only:
            return members
        return {'exception %s' % name : members}

    def to_dic(self):
        """The exception as a plain dict (for JSON or YAML output)."""
        dic = { 'name' : self.name,
                'classname' : self.classname,
                'members' : [v.to_dic() for v in self.members] }
        return self._with_annotations(dic)

    def parse_tokens(self, token_buf, filepath=None):
        """Parse the exception from ``token_buf``, starting after its name.

        :raises ~idl_parser.exception.InvalidIDLSyntaxError: The declaration is
            not valid IDL (an exception can not be forward-declared).
        :raises ~idl_parser.exception.InvalidDataTypeException: A member type is
            not defined.
        """
        ln, fn, kakko = token_buf.peek()
        if kakko != '{':
            raise exception.InvalidIDLSyntaxError(ln, fn, 'No "{" in the declaration of exception "%s"' % self.name)
        super(IDLException, self).parse_tokens(token_buf, filepath)
