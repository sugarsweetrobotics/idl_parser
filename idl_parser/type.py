"""Type references: primitive types, sequences, arrays and named types.

:func:`IDLType` turns a type name as written in the IDL into one of the
classes here. A name that is not primitive is an :class:`IDLBasicType`,
which is resolved to its definition through :attr:`IDLBasicType.obj`.
"""
import os, sys, traceback, re

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
    'wstring',
    # IDL 4.2 explicitly-sized integer types (issue #18)
    'int8', 'int16', 'int32', 'int64',
    'uint8', 'uint16', 'uint32', 'uint64']

# Bounded strings such as 'string<8>' or 'wstring< MAX_LEN >' (issue #9).
_bounded_string = re.compile(r'^(w?string)\s*<\s*([A-Za-z0-9_:]+)\s*>$')

def parse_bounded_string(name):
    """Return (base, bound) for a bounded string type name, otherwise None.
    bound is an int for a numeric literal, or the name as written (e.g. a const)."""
    m = _bounded_string.match(name.strip())
    if not m:
        return None
    base, bound = m.group(1), m.group(2)
    try:
        bound = int(bound)
    except ValueError:
        pass
    return (base, bound)

def _parse_bound(bound):
    """An int for a numeric literal, otherwise the name as written (e.g. a const)."""
    bound = bound.strip()
    try:
        return int(bound)
    except ValueError:
        return bound

def split_top_level(text, sep=','):
    """Split ``text`` at ``sep`` that is not inside ``< >``.
    ``'string<8>, 10'`` gives ``['string<8>', ' 10']``."""
    parts = []
    depth = 0
    start = 0
    for i, c in enumerate(text):
        if c == '<':
            depth = depth + 1
        elif c == '>':
            depth = depth - 1
        elif c == sep and depth == 0:
            parts.append(text[start:i])
            start = i + 1
    parts.append(text[start:])
    return parts

_sequence_head = re.compile(r'^sequence\s*<')

def parse_sequence(name):
    """Return (element_type_name, bound) for a sequence type name, otherwise None (issue #31).

    The ``<`` and ``>`` are matched, so nested types are kept whole:
    ``'sequence<string<8>, 10>'`` gives ``('string<8>', 10)`` and
    ``'sequence<sequence<long>>'`` gives ``('sequence<long>', None)``.
    bound is None for an unbounded sequence, an int for a numeric literal,
    or the name as written (e.g. a const).
    Raises InvalidIDLSyntaxError if the brackets do not match.
    """
    name = name.strip()
    m = _sequence_head.match(name)
    if not m:
        return None
    open_ = m.end() - 1
    depth = 0
    close = None
    for i in range(open_, len(name)):
        if name[i] == '<':
            depth = depth + 1
        elif name[i] == '>':
            depth = depth - 1
            if depth == 0:
                close = i
                break
    if close is None or name[close+1:].strip():
        raise exception.InvalidIDLSyntaxError(message='Invalid sequence type "%s"' % name)
    args = split_top_level(name[open_+1:close])
    elem = args[0].strip()
    if not elem or len(args) > 2 or (len(args) == 2 and not args[1].strip()):
        raise exception.InvalidIDLSyntaxError(message='Invalid sequence type "%s"' % name)
    bound = _parse_bound(args[1]) if len(args) == 2 else None
    return (elem, bound)

def is_string(name):
    """True if ``name`` is ``string`` or ``wstring``, bounded ones included."""
    name = name.strip()
    return name in ('string', 'wstring') or parse_bounded_string(name) is not None

def is_primitive(name):
    """True if ``name`` is a primitive type name.

    Multi-word names such as ``unsigned long`` and bounded strings
    (``string<8>``) count as primitive.
    """
    if parse_bounded_string(name) is not None:
        return True
    for n in name.split():
        if n in primitive:
            return True
    return False

def IDLType(name, parent):
    """Make a type node from a type name as written.

    ``'void'`` gives an :class:`IDLVoid`, ``'sequence<...>'`` an
    :class:`IDLSequence`, a name with ``[n]`` an :class:`IDLArray`, a primitive
    name an :class:`IDLPrimitive`, and any other name an :class:`IDLBasicType`.

    :param name: Type name (``'long'``, ``'sequence<T, 10>'``, ``'long[3]'``, ``'M::T'``).
    :param parent: The node where the name is written; named types are
        resolved from its scope.
    """
    if name == 'void':
        return IDLVoid(name, parent)

    elif _sequence_head.match(name.strip()) and not name.rstrip().endswith(']'):
        return IDLSequence(name, parent)
    elif name.find('[') >= 0:
        return IDLArray(name, parent)

    if is_primitive(name):
        return IDLPrimitive(name, parent)

    return IDLBasicType(name, parent)

class IDLTypeBase(node.IDLNode):
    """Base class of the type nodes made by :func:`IDLType`.

    The parent of a type node is the global module (the root node).
    """
    def __init__(self, classname, name, parent):
        super(IDLTypeBase, self).__init__(classname, name, parent.root_node)
        self._is_sequence = False
        self._is_primitive = False

    def __str__(self):
        return self.name

    @property
    def is_sequence(self):
        """True for :class:`IDLSequence`."""
        return self._is_sequence

    @property
    def is_primitive(self):
        """True for :class:`IDLPrimitive`."""
        return self._is_primitive


class IDLVoid(IDLTypeBase):
    """The ``void`` return type."""
    def __init__(self, name, parent):
        super(IDLVoid, self).__init__('IDLVoid', name, parent.root_node)
        self._verbose = True

class IDLSequence(IDLTypeBase):
    """A sequence type (``sequence<T>`` or ``sequence<T, N>``).

    ``str()`` gives ``'sequence<T>'``; the bound is available as :attr:`bound`.

    :raises ~idl_parser.exception.InvalidIDLSyntaxError: The name is not a
        valid sequence type.
    """
    def __init__(self, name, parent):
        super(IDLSequence, self).__init__('IDLSequence', name, parent.root_node)
        self._verbose = True
        parsed = parse_sequence(name)
        if parsed is None:
            raise exception.InvalidIDLSyntaxError()
        typ_, self._bound = parsed
        self._type = IDLType(typ_, parent)
        self._is_primitive = False #self.inner_type.is_primitive
        self._is_sequence = True

    @property
    def inner_type(self):
        """Element type (a type node made by :func:`IDLType`)."""
        return self._type

    @property
    def bound(self):
        """Maximum length of a bounded sequence ('sequence<long, 10>' -> 10).
        A constant name is returned as written ('sequence<long, MAXLEN>' -> 'MAXLEN').
        None for an unbounded sequence. The type name does not include the bound
        ('sequence<long, 10>' -> 'sequence<long>'), as with bounded strings."""
        return self._bound

    @property
    def is_bounded_sequence(self):
        """True if the sequence has a bound (``sequence<long, 10>``)."""
        return self._bound is not None

    def __str__(self):
        return 'sequence<%s>' % str(self.inner_type)

    @property
    def obj(self):
        """The sequence itself."""
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
        """Element type; same as :attr:`inner_type`."""
        return self._type

    @property
    def full_path(self):
        return self.parent.full_path + sep + self.name

    def to_simple_dic(self, quiet=False, full_path=False, recursive=False, member_only=False):
        """A compact summary.

        :param quiet: Return ``'sequence<T>'``.
        :param recursive: Return ``{'sequence<T>': ...}`` with the element type
            expanded. Without ``quiet`` or ``recursive``, None is returned.
        """
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
        """The sequence as a plain dict (for JSON or YAML output)."""
        dic = { 'name' : self.name,
                'classname' : self.classname,
                'type' : str(self.type) }
        return dic

class IDLArray(IDLTypeBase):
    """An array type (``long[3]``; ``long[2][3]`` is an array of arrays).

    ``str()`` gives the element type with all sizes (``'long[2][3]'``).

    :raises ~idl_parser.exception.InvalidDataTypeException: The size is not
        an integer or the name of an integer constant.
    """
    def __init__(self, name, parent):
        super(IDLArray, self).__init__('IDLArray', name.strip(), parent.root_node)

        self._verbose = True
        if name.find('[') < 0:
            raise exception.InvalidIDLSyntaxError()
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
        """Element type (for ``long[2][3]``, the array type ``long[3]``)."""
        return self._type

    @property
    def primitive_type(self):
        """The innermost element type (for ``long[2][3]``, ``long``)."""
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
        """The array itself."""
        return self

    @property
    def size(self):
        """Number of elements of the outermost dimension (an int)."""
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
        """The int value of an array size: an integer literal or the name of a
        constant.

        :raises ~idl_parser.exception.InvalidDataTypeException: The size is not
            an integer.
        """
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
        """Element type; same as :attr:`inner_type`."""
        return self._type

    @property
    def full_path(self):
        return self.parent.full_path + sep + self.name

    def to_simple_dic(self, quiet=False, full_path=False, recursive=False, member_only=False):
        """A compact summary, ``str(self)`` (``'long[3]'``) when ``quiet`` or
        ``recursive`` is given, otherwise None.
        """
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
        """The array as a plain dict (for JSON or YAML output)."""
        dic = { 'name' : self.name,
                'classname' : self.classname,
                'type' : str(self.type) }
        return dic


class IDLPrimitive(IDLTypeBase):
    """A primitive type (``long``, ``unsigned short``, ``string``, ...).

    A bounded string keeps its base name (``string<8>`` -> ``'string'``); the
    bound is available as :attr:`bound`.
    """
    def __init__(self, name, parent):
        bounded = parse_bounded_string(name)
        if bounded is not None:
            # A bounded string keeps its base type name ('string<8>' -> 'string');
            # the length limit is available via .bound
            name = bounded[0]
        super(IDLPrimitive, self).__init__('IDLPrimitive', name, parent.root_node)
        self._verbose = True
        self._is_primitive = True
        self._bound = bounded[1] if bounded is not None else None

    @property
    def bound(self):
        """Maximum length of a bounded string ('string<8>' -> 8).
        A constant name is returned as written ('string<MAXLEN>' -> 'MAXLEN').
        None for an unbounded string and for other primitive types."""
        return self._bound

    @property
    def is_bounded_string(self):
        """True for a bounded string (``string<8>``)."""
        return self._bound is not None
    @property
    def full_path(self):
        return (self.parent.full_path + self.sep + self.name).strip()
class IDLBasicType(IDLTypeBase):
    """A named type that is not primitive (``T``, ``M::T``, ``::M::T``).

    The definition is looked up when needed (:meth:`resolve`, :attr:`obj`),
    so the name may be used before the type is defined (e.g. a forward
    declaration).
    """
    def __init__(self, name, parent):
        # The node where the name is written: the name is resolved from its
        # scope (issue #72). The parent of a type node is the root node.
        self._scope = parent
        self._ref_name = name.strip()
        super(IDLBasicType, self).__init__('IDLBasicType', name, parent.root_node)
        self._verbose = True
        #if self.name.find('['):
        #    self._name = self.name[self.name.find('[')+1:]
        self._name = self.refine_typename(self)

    @property
    def ref_name(self):
        """The type name as written (``'A::X'``, ``'::B::X'``). ``name`` is
        the name of the definition without its scope (``'X'``)."""
        return self._ref_name

    def _lookup_scope(self):
        return self._scope

    def resolve(self):
        """The definitions this name refers to, found from the scope where
        it is written (a list; empty if it is not defined)."""
        return self.root_node.find_types(self._ref_name, scope=self._scope)

    @property
    def obj(self):
        """The definition this name refers to (an ``IDLStruct``, ``IDLEnum``, ...),
        or None if it is not defined.
        """
        typs = self.resolve()
        if len(typs) == 0:
            return None
        else:
            return typs[0]
