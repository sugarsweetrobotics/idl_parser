"""Type references: primitive types, sequences, maps, arrays, fixed-point
types and named types.

:func:`IDLType` turns a type name as written in the IDL into one of the
classes here. A name that is not primitive is an :class:`IDLBasicType`,
which is resolved to its definition through :attr:`IDLBasicType.obj`.
"""
import os, sys, traceback, re

from . import node
from . import exception
from . import const_expr

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
    'uint8', 'uint16', 'uint32', 'uint64',
    # Base types that are not numbers or strings (issue #119)
    'any', 'Object', 'ValueBase']

# any, Object and ValueBase hold a reference or a value of any type, so they
# have no default value such as 0 (issue #119)
reference_primitive = ['any', 'Object', 'ValueBase', 'TypeCode', 'Principal', 'AbstractBase']

# Types of module CORBA that an ORB knows without any IDL (the definitions
# of orb.idl), such as CORBA::TypeCode (issue #138). When IDL does not define
# them (e.g. by including an orb.idl), CORBA::TypeCode is an IDLPrimitive
# named 'TypeCode'.
builtin_corba_types = ('TypeCode', 'Principal', 'AbstractBase')


def builtin_corba_type(name, scope=None):
    """The name of the built-in CORBA type (``'TypeCode'``) that ``name``
    (``'CORBA::TypeCode'``, ``'::CORBA::TypeCode'``, or ``'TypeCode'``
    written inside module CORBA) names, or None (issue #138)."""
    parts = str(name).strip().lstrip(':').split(sep)
    if len(parts) == 2 and parts[0] == 'CORBA' and parts[1] in builtin_corba_types:
        return parts[1]
    if len(parts) == 1 and parts[0] in builtin_corba_types and not str(name).strip().startswith(sep):
        n = scope
        while n is not None:
            if n.classname == 'IDLModule' and n.name == 'CORBA' and n.parent is not None and n.parent.parent is None:
                return parts[0]
            n = n.parent
    return None

# Bounded strings such as 'string<8>' or 'wstring< MAX_LEN >' (issue #9).
# The bound may be a constant expression ('string<N * 2>', issue #130).
_bounded_string_head = re.compile(r'^(w?string)\s*<')

def _angle_close(name, open_):
    """Index of the ``>`` matching the ``<`` at ``name[open_]``, or None.
    ``<`` and ``>`` inside ``( )`` are operators (``(1 << 3)``), not brackets."""
    depth = 0
    paren = 0
    for i in range(open_, len(name)):
        c = name[i]
        if c == '(':
            paren = paren + 1
        elif c == ')':
            paren = paren - 1
        elif paren > 0:
            continue
        elif c == '<':
            depth = depth + 1
        elif c == '>':
            depth = depth - 1
            if depth == 0:
                return i
    return None

def parse_bounded_string(name):
    """Return (base, bound) for a bounded string type name, otherwise None.
    bound is an int for a numeric literal, or the bound as written (a
    constant name or a constant expression, evaluated by :class:`IDLPrimitive`)."""
    name = name.strip()
    m = _bounded_string_head.match(name)
    if not m:
        return None
    close = _angle_close(name, m.end() - 1)
    if close != len(name) - 1:
        return None
    bound = name[m.end():close].strip()
    if not bound:
        return None
    return (m.group(1), _parse_bound(bound))

def _parse_bound(bound):
    """An int for a numeric literal, otherwise the bound as written (a
    constant name or a constant expression)."""
    bound = bound.strip()
    value = const_expr.parse_int_literal(bound)
    return bound if value is None else value

def _evaluate_bound(bound, parent, what):
    """The int value of a bound written in ``parent`` (issue #130).
    None (no bound) stays None."""
    if bound is None:
        return None
    return const_expr.evaluate_positive(bound, parent, what)

def split_top_level(text, sep=','):
    """Split ``text`` at ``sep`` that is not inside ``< >`` or ``( )``.
    ``'string<8>, 10'`` gives ``['string<8>', ' 10']``."""
    parts = []
    depth = 0
    paren = 0
    start = 0
    for i, c in enumerate(text):
        if c == '(':
            paren = paren + 1
        elif c == ')':
            paren = paren - 1
        elif paren > 0:
            continue
        elif c == '<':
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
    close = _angle_close(name, open_)
    if close is None or name[close+1:].strip():
        raise exception.InvalidIDLSyntaxError(message='Invalid sequence type "%s"' % name)
    args = split_top_level(name[open_+1:close])
    elem = args[0].strip()
    if not elem or len(args) > 2 or (len(args) == 2 and not args[1].strip()):
        raise exception.InvalidIDLSyntaxError(message='Invalid sequence type "%s"' % name)
    bound = _parse_bound(args[1]) if len(args) == 2 else None
    return (elem, bound)

_fixed = re.compile(r'^fixed\s*<\s*([A-Za-z0-9_:]+)\s*,\s*([A-Za-z0-9_:]+)\s*>$')

def parse_fixed(name):
    """Return (digits, scale) for a fixed-point type name, otherwise None (issue #119).

    ``'fixed<10, 2>'`` gives ``(10, 2)``. Each is an int for a numeric
    literal, or the name as written (e.g. a const).

    :raises ~idl_parser.exception.InvalidIDLSyntaxError: The digits are not
        1 to 31, or the scale is not 0 to the digits.
    """
    m = _fixed.match(name.strip())
    if not m:
        return None
    digits, scale = _parse_bound(m.group(1)), _parse_bound(m.group(2))
    if isinstance(digits, int) and not 1 <= digits <= 31:
        raise exception.InvalidIDLSyntaxError(
            message='Invalid fixed type "%s": the digits must be 1 to 31' % name)
    if isinstance(scale, int) and (scale < 0 or (isinstance(digits, int) and scale > digits)):
        raise exception.InvalidIDLSyntaxError(
            message='Invalid fixed type "%s": the scale must be 0 to the digits' % name)
    return (digits, scale)

def fixed_name(digits, scale):
    """The name of a fixed-point type: ``'fixed<10, 2>'``."""
    return 'fixed<%s, %s>' % (digits, scale)

_map_head = re.compile(r'^map\s*<')

def parse_map(name):
    """Return (key_type_name, value_type_name, bound) for a map type name,
    otherwise None (issue #118).

    As with :func:`parse_sequence`, nested types are kept whole:
    ``'map<string<8>, sequence<long>, 10>'`` gives
    ``('string<8>', 'sequence<long>', 10)``.
    bound is None for an unbounded map, an int for a numeric literal,
    or the name as written (e.g. a const).
    Raises InvalidIDLSyntaxError if the brackets do not match.
    """
    name = name.strip()
    m = _map_head.match(name)
    if not m:
        return None
    open_ = m.end() - 1
    close = _angle_close(name, open_)
    if close is None or name[close+1:].strip():
        raise exception.InvalidIDLSyntaxError(message='Invalid map type "%s"' % name)
    args = [a.strip() for a in split_top_level(name[open_+1:close])]
    if len(args) not in (2, 3) or not all(args):
        raise exception.InvalidIDLSyntaxError(message='Invalid map type "%s"' % name)
    bound = _parse_bound(args[2]) if len(args) == 3 else None
    return (args[0], args[1], bound)

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

def _resolve_element(typ):
    """The definition an element type names (issue #111).

    An :class:`IDLBasicType` is looked up from the scope where it is written,
    like the type of a member; any other type node, and a name that can not
    be resolved (yet), is returned as is.
    """
    if typ.classname == 'IDLBasicType':
        typs = typ.resolve()
        if len(typs) > 0:
            return typs[0]
    return typ

def IDLType(name, parent):
    """Make a type node from a type name as written.

    ``'void'`` gives an :class:`IDLVoid`, ``'sequence<...>'`` an
    :class:`IDLSequence`, ``'map<...>'`` an :class:`IDLMap`, a name with ``[n]`` an :class:`IDLArray`,
    ``'fixed<d, s>'`` an :class:`IDLFixed`, a primitive name (``any``,
    ``Object`` and ``ValueBase`` included) an :class:`IDLPrimitive`, and any
    other name an :class:`IDLBasicType`.

    :param name: Type name (``'long'``, ``'sequence<T, 10>'``, ``'map<K, V>'``,
        ``'long[3]'``, ``'fixed<10, 2>'``, ``'M::T'``).
    :param parent: The node where the name is written; named types are
        resolved from its scope.
    """
    if name == 'void':
        return IDLVoid(name, parent)

    elif _sequence_head.match(name.strip()) and not name.rstrip().endswith(']'):
        return IDLSequence(name, parent)
    elif _map_head.match(name.strip()) and not name.rstrip().endswith(']'):
        return IDLMap(name, parent)
    elif name.find('[') >= 0:
        return IDLArray(name, parent)
    elif _fixed.match(name.strip()):
        return IDLFixed(name, parent)

    if is_primitive(name):
        return IDLPrimitive(name, parent)

    return IDLBasicType(name, parent)

class IDLTypeBase(node.IDLNode):
    """Base class of the type nodes made by :func:`IDLType`.

    The parent of a type node is the global module (the root node).
    """
    def __init__(self, classname, name, parent):
        super(IDLTypeBase, self).__init__(classname, name, parent.root_node)
        self._line_number = None  # a type is not a definition (issue #141)
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
        typ_, bound = parsed
        self._bound = _evaluate_bound(bound, parent, 'bound of "%s"' % name.strip())
        self._type = IDLType(typ_, parent)
        self._is_primitive = False #self.inner_type.is_primitive
        self._is_sequence = True

    @property
    def inner_type(self):
        """Element type: a type node made by :func:`IDLType`, or, for a named
        type, its definition (``IDLStruct``, ``IDLEnum``, ``IDLTypedef``, ...),
        as for :attr:`idl_parser.struct.IDLMember.type` (issue #111). A name
        that is not defined (yet) is an :class:`IDLBasicType`."""
        return _resolve_element(self._type)

    @property
    def bound(self):
        """Maximum length of a bounded sequence ('sequence<long, 10>' -> 10), an int.
        A constant name or a constant expression is evaluated
        ('sequence<long, N * 2>' -> 6 when N is 3, issue #130).
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
        return self.inner_type

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

class IDLMap(IDLTypeBase):
    """A map type (``map<K, V>`` or ``map<K, V, N>``, issue #118).

    ``str()`` gives ``'map<K, V>'``; the bound is available as :attr:`bound`.

    :raises ~idl_parser.exception.InvalidIDLSyntaxError: The name is not a
        valid map type.
    """
    def __init__(self, name, parent):
        super(IDLMap, self).__init__('IDLMap', name, parent.root_node)
        self._verbose = True
        parsed = parse_map(name)
        if parsed is None:
            raise exception.InvalidIDLSyntaxError()
        key_, value_, bound = parsed
        self._bound = _evaluate_bound(bound, parent, 'bound of "%s"' % name.strip())
        self._key_type = IDLType(key_, parent)
        self._value_type = IDLType(value_, parent)

    @property
    def key_type(self):
        """Key type, resolved like :attr:`IDLSequence.inner_type`."""
        return _resolve_element(self._key_type)

    @property
    def value_type(self):
        """Value type, resolved like :attr:`IDLSequence.inner_type`."""
        return _resolve_element(self._value_type)

    @property
    def bound(self):
        """Maximum number of entries of a bounded map ('map<long, string, 10>' -> 10),
        an int. A constant name or a constant expression is evaluated (issue #130). None for an unbounded map.
        The type name does not include the bound, as with sequences."""
        return self._bound

    @property
    def is_bounded_map(self):
        """True if the map has a bound (``map<long, string, 10>``)."""
        return self._bound is not None

    def __str__(self):
        return 'map<%s, %s>' % (str(self.key_type), str(self.value_type))

    @property
    def obj(self):
        """The map itself."""
        return self

    @property
    def full_path(self):
        return self.parent.full_path + sep + self.name

    def to_simple_dic(self, quiet=False, full_path=False, recursive=False, member_only=False):
        """A compact summary, ``str(self)`` (``'map<K, V>'``) when ``quiet`` or
        ``recursive`` is given, otherwise None."""
        if quiet or recursive:
            return str(self)

    def to_dic(self):
        """The map as a plain dict (for JSON or YAML output)."""
        return { 'name' : self.name,
                 'classname' : self.classname,
                 'key_type' : str(self.key_type),
                 'value_type' : str(self.value_type) }

class IDLFixed(IDLTypeBase):
    """A fixed-point decimal type (``fixed<10, 2>``, issue #119).

    ``str()`` and ``name`` give ``'fixed<10, 2>'``; the total number of
    digits and the number of digits after the decimal point are available as
    :attr:`digits` and :attr:`scale`.

    :raises ~idl_parser.exception.InvalidIDLSyntaxError: The name is not a
        valid fixed-point type.
    """
    def __init__(self, name, parent):
        parsed = parse_fixed(name)
        if parsed is None:
            raise exception.InvalidIDLSyntaxError(message='Invalid fixed type "%s"' % name)
        self._digits, self._scale = parsed
        super(IDLFixed, self).__init__('IDLFixed', fixed_name(*parsed), parent.root_node)
        self._verbose = True

    @property
    def digits(self):
        """Total number of digits ('fixed<10, 2>' -> 10). A constant name is
        returned as written."""
        return self._digits

    @property
    def scale(self):
        """Number of digits after the decimal point ('fixed<10, 2>' -> 2).
        A constant name is returned as written."""
        return self._scale

    @property
    def obj(self):
        """The fixed-point type itself."""
        return self

    @property
    def full_path(self):
        return self.parent.full_path + sep + self.name

    def to_simple_dic(self, quiet=False, full_path=False, recursive=False, member_only=False):
        """A compact summary, ``str(self)`` (``'fixed<10, 2>'``) when ``quiet`` or
        ``recursive`` is given, otherwise None."""
        if quiet or recursive:
            return str(self)

    def to_dic(self):
        """The fixed-point type as a plain dict (for JSON or YAML output)."""
        return { 'name' : self.name,
                 'classname' : self.classname,
                 'digits' : self.digits,
                 'scale' : self.scale }

class IDLArray(IDLTypeBase):
    """An array type (``long[3]``; ``long[2][3]`` is an array of arrays).

    ``str()`` gives the element type with all sizes (``'long[2][3]'``).

    :raises ~idl_parser.exception.InvalidConstExpressionError: A size is not
        a positive integer constant expression (it is also an
        :class:`~idl_parser.exception.InvalidDataTypeException`).
    """
    def __init__(self, name, parent):
        super(IDLArray, self).__init__('IDLArray', name.strip(), parent.root_node)

        self._verbose = True
        if name.find('[') < 0:
            raise exception.InvalidIDLSyntaxError()
        primitive_type_name = name[:name.find('[')]
        size = name[name.find('[')+1 : name.find(']')]
        inner_type_name = primitive_type_name + name[name.find(']')+1:]

        size_literal = self.parse_size(size, parent)

        self._size = size_literal
        self._type = IDLType(inner_type_name.strip(), parent)
        self._is_primitive = False #self.inner_type.is_primitive
        self._is_sequence = False
        self._is_array = True


    @property
    def inner_type(self):
        """Element type (for ``long[2][3]``, the array type ``long[3]``).
        A named type is resolved to its definition, as for
        :attr:`IDLSequence.inner_type` (issue #111)."""
        return _resolve_element(self._type)

    @property
    def primitive_type(self):
        """The innermost element type (for ``long[2][3]``, ``long``)."""
        if self.inner_type.is_array:
            return self.inner_type.primitive_type
        else:
            return self.inner_type

    def __str__(self):
        n = ['%s' % str(self.primitive_type)]
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

    def parse_size(self, size, scope=None):
        """The int value of an array size: an integer constant expression
        such as ``3``, ``N`` or ``N * 2`` (issue #130).

        :param scope: Node where the array is written; constants in the scopes
            enclosing it are found first.
        :raises ~idl_parser.exception.InvalidConstExpressionError: The size is
            not a positive integer.
        """
        return const_expr.evaluate_positive(size, scope if scope is not None else self,
                                            'array size')

    @property
    def type(self):
        """Element type; same as :attr:`inner_type`."""
        return self.inner_type

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

    The built-in types of module CORBA (``CORBA::TypeCode``,
    ``CORBA::Principal``, ``CORBA::AbstractBase``) are primitive types too,
    named ``'TypeCode'``, ... (issue #138); :attr:`is_builtin_corba_type`
    is True for them.

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
        self._bound = _evaluate_bound(bounded[1], parent, 'bound of "%s"' % name.strip()) \
            if bounded is not None else None

    @property
    def bound(self):
        """Maximum length of a bounded string ('string<8>' -> 8), an int.
        A constant name or a constant expression is evaluated
        ('string<N * 2>' -> 6 when N is 3, issue #130). None for an unbounded string and for other primitive types."""
        return self._bound

    @property
    def is_bounded_string(self):
        """True for a bounded string (``string<8>``)."""
        return self._bound is not None

    @property
    def is_builtin_corba_type(self):
        """True for a built-in type of module CORBA (``CORBA::TypeCode``, issue #138)."""
        return self.name in builtin_corba_types
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
