"""Base class of all nodes, and IDL annotations (``@name(...)``)."""
import re

from .exception import InvalidIDLSyntaxError


class IDLAnnotation(object):
    """An annotation such as ``@key``, ``@bit_bound(8)`` or ``@range(min=0, max=10)``.

    Arguments are kept as written in the IDL (strings keep their quotes;
    whitespace inside them may be normalized by the tokenizer).
    """

    def __init__(self, name, args=None, params=None):
        self._name = name
        self._args = list(args or [])
        self._params = dict(params or {})

    @property
    def name(self):
        """Name without ``@`` (``'key'``, ``'bit_bound'``)."""
        return self._name

    @property
    def args(self):
        """Positional arguments (``@bit_bound(8)`` -> ``['8']``)."""
        return list(self._args)

    @property
    def params(self):
        """Named arguments (``@range(min=0, max=10)`` -> ``{'min': '0', 'max': '10'}``)."""
        return dict(self._params)

    @property
    def value(self):
        """The single argument (``@bit_bound(8)`` and ``@bit_bound(value=8)`` -> ``'8'``),
        or None when there is none or more than one."""
        if len(self._args) == 1 and not self._params:
            return self._args[0]
        if not self._args and list(self._params) == ['value']:
            return self._params['value']
        return None

    def __str__(self):
        items = self._args + ['%s=%s' % kv for kv in self._params.items()]
        if not items:
            return '@' + self._name
        return '@%s(%s)' % (self._name, ', '.join(items))

    def __repr__(self):
        return '<IDLAnnotation %s>' % str(self)

    def to_dic(self):
        """The annotation as a plain dict: ``{'name': ..., 'args': [...], 'params': {...}}``."""
        return {'name': self._name, 'args': self.args, 'params': self.params}


def parse_annotations(tokens):
    """Split leading annotations off a token list.

    Returns ``([IDLAnnotation, ...], remaining_tokens)``.
    ``['@range', '(', 'min', '=', '0', ',', 'max', '=', '9', ')', 'long', 'x']``
    -> ``([@range(min=0, max=9)], ['long', 'x'])``.
    """
    annotations = []
    i = 0
    while i < len(tokens) and tokens[i].startswith('@') and len(tokens[i]) > 1:
        name = tokens[i][1:]
        i += 1
        arg_tokens = []
        if i < len(tokens) and tokens[i] == '(':
            end = matching_paren(tokens, i)
            if end is None:
                raise InvalidIDLSyntaxError(message='No ")" in annotation "@%s"' % name)
            arg_tokens = tokens[i + 1:end]
            i = end + 1
        annotations.append(_make_annotation(name, arg_tokens))
    return annotations, tokens[i:]


def matching_paren(tokens, start):
    """Index of the ")" matching the "(" at tokens[start], or None."""
    depth = 0
    for j in range(start, len(tokens)):
        if tokens[j] == '(':
            depth += 1
        elif tokens[j] == ')':
            depth -= 1
            if depth == 0:
                return j
    return None


def split_top_level(tokens, sep):
    """Split tokens at ``sep`` tokens that are not inside parentheses."""
    parts, part, depth = [], [], 0
    for t in tokens:
        if t == '(':
            depth += 1
        elif t == ')':
            depth -= 1
        if t == sep and depth == 0:
            parts.append(part)
            part = []
        else:
            part.append(t)
    parts.append(part)
    return parts


def split_declarators(tokens, what='declaration'):
    """Split ``TYPE NAME[, NAME...]`` into the type tokens and the declarators
    (issue #117).

    A declarator is a name with its array sizes, if any, as one string:
    ``['long', 'a', ',', 'c', '[2]', '[3]']`` -> ``(['long'], ['a', 'c[2][3]'])``.
    A ``,`` inside ``< >`` (``sequence<long, 10>``) does not split.

    :param what: Kind of declaration, used in the error message.
    :raises ~idl_parser.exception.InvalidIDLSyntaxError: There is no type or
        no name, or a declarator is not a name with array sizes.
    """
    groups = [[]]
    for t in tokens:
        in_template = sum(x.count('<') - x.count('>') for x in groups[-1]) > 0
        if t == ',' and not in_template:
            groups.append([])
        else:
            groups[-1].append(t)

    def invalid():
        return InvalidIDLSyntaxError(message='Invalid %s "%s"' % (what, ' '.join(tokens)))

    def peel(group):
        # Split trailing "[n]" tokens and the name before them off group.
        end = len(group)
        while end > 0 and group[end - 1].startswith('['):
            end -= 1
        if end == 0:
            raise invalid()
        declarator = ''.join(group[end - 1:])
        name = declarator.split('[', 1)[0]
        if not _identifier.match(name):
            raise invalid()
        check_identifier(name, '%s "%s"' % (what, ' '.join(tokens)))
        return group[:end - 1], declarator

    type_tokens, first = peel(groups[0])
    if not type_tokens:
        raise invalid()
    declarators = [first]
    for g in groups[1:]:
        rest, declarator = peel(g)
        if rest:
            raise invalid()
        declarators.append(declarator)
    return type_tokens, declarators


_identifier = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')

# IDL 4.2 keywords that can not be used as identifiers (issue #119). The
# keywords of the CCM building blocks (component, home, port, ...) and
# import are left out: those definitions are skipped with a warning
# (issue #100), so the words may still be used as names. typeid and
# typeprefix (read since issue #135) are left out too, so that IDL using
# them as names is still read.
reserved_words = frozenset((
    # core data types
    'any', 'boolean', 'case', 'char', 'const', 'default', 'double', 'enum',
    'FALSE', 'fixed', 'float', 'long', 'module', 'native', 'Object', 'octet',
    'sequence', 'short', 'string', 'struct', 'switch', 'TRUE', 'typedef',
    'unsigned', 'union', 'void', 'wchar', 'wstring',
    # interfaces
    'attribute', 'context', 'exception', 'getraises', 'in', 'inout',
    'interface', 'local', 'oneway', 'out', 'raises', 'readonly', 'setraises',
    # value types
    'abstract', 'custom', 'eventtype', 'factory', 'private', 'public',
    'supports', 'truncatable', 'valuetype', 'ValueBase',
    # extended data types
    'bitfield', 'bitmask', 'bitset', 'map', 'int8', 'int16', 'int32', 'int64',
    'uint8', 'uint16', 'uint32', 'uint64'))


def check_identifier(name, what='name', line_number=None, file_name=None):
    """Raise InvalidIDLSyntaxError if ``name`` is an IDL keyword (issue #119).

    A keyword such as ``long``, ``any`` or ``Object`` can not name a
    definition, a member or an argument: ``struct S { long any; };`` is an
    error instead of being read silently.

    :param what: What the name is for, used in the error message
        (``'struct'``, ``'enumerator'``, ...).
    """
    if name is not None and name.split('[', 1)[0].strip() in reserved_words:
        raise InvalidIDLSyntaxError(
            line_number, file_name,
            'The keyword "%s" can not be used as a name (%s)' % (name.split('[', 1)[0].strip(), what))


def _make_annotation(name, arg_tokens):
    args, params = [], {}
    if arg_tokens:
        for part in split_top_level(arg_tokens, ','):
            if len(part) >= 3 and part[1] == '=':
                params[part[0]] = ' '.join(part[2:])
            elif part:
                args.append(' '.join(part))
    return IDLAnnotation(name, args, params)


class IDLNode(object):
    """Base class of all nodes of the parse tree.

    Every node has a :attr:`name`, a :attr:`parent` (``None`` for the global
    module) and the :attr:`annotations` written before it. The ``is_*``
    properties tell the kind of node.

    :param classname: Kind of the node (``'IDLStruct'``, ...), see :attr:`classname`.
    :param name: Name of the node.
    :param parent: Enclosing node.
    """
    def __init__(self, classname, name, parent):
        self._classname = classname
        self._parent = parent
        self._name = name
        self._filepath = None
        self.sep = '::'
        self._annotations = []
        # The line the node is written on (issue #141)
        from . import token_buffer
        self._line_number = token_buffer.current_line() if parent is not None else None
        # Repository ID (issue #135): the #pragma prefix in effect where the
        # node is defined, as (prefix, scope the names are relative to; None
        # for the global scope). A scope passes its current one to the
        # definitions in it; see idl_parser.repository_id.
        self._repo_prefix = getattr(parent, '_prefix_state', ('', None))
        self._prefix_state = self._repo_prefix
        self._include_prefixes = []
        self._repo_id = None
        self._repo_version = None
        self._typeprefix = None

    @property
    def annotations(self):
        """Annotations written before this definition (list of :class:`IDLAnnotation`)."""
        return list(self._annotations)

    def annotation_by_name(self, name):
        """The annotation named ``name`` (without ``@``), or None. The last one wins."""
        for a in reversed(self._annotations):
            if a.name == name:
                return a
        return None

    def has_annotation(self, name):
        """True if an annotation named ``name`` (without ``@``) is written."""
        return self.annotation_by_name(name) is not None

    def _add_annotations(self, annotations):
        self._annotations.extend(annotations)

    def _with_annotations(self, dic):
        """Add 'annotations' to a to_dic() result when there are any."""
        if self._annotations:
            dic['annotations'] = [a.to_dic() for a in self._annotations]
        return dic

    @property
    def obj(self):
        """The definition this node stands for: the node itself.

        A member's ``type`` is either an :class:`~idl_parser.type.IDLBasicType`
        (an unresolved name, whose ``obj`` looks up the definition) or the
        definition node itself (``IDLStruct``, ``IDLEnum``, ``IDLTypedef`` ...).
        Giving every node ``obj`` lets callers write ``member.type.obj`` in
        both cases (issues #30, #43).
        """
        return self

    def __str__(self):
        """The name, so that ``str(member.type)`` is a type name such as ``'T'``
        whether or not the type has been resolved to its definition."""
        return self.name

    @property
    def line_number(self):
        """Line number in :attr:`filepath` where the node is written, or None
        (issue #141).

        For a definition with a name (module, interface, struct, enum, ...)
        it is the line of its name; for a member, an enumerator, an
        operation or an attribute, the line where its declaration starts.
        Type nodes (:class:`~idl_parser.type.IDLTypeBase`) and the global
        scope have None.
        """
        return self._line_number

    @property
    def repository_id(self):
        """The repository ID (``'IDL:omg.org/CosNaming/NamingContext:1.0'``,
        issue #135), following ``#pragma prefix``, ``#pragma ID``,
        ``#pragma version``, ``typeid`` and ``typeprefix``
        (see :mod:`idl_parser.repository_id`).

        Modules, interfaces, value types, event types, structs, exceptions,
        unions, enums, typedefs, constants, native types, bitmasks, bitsets,
        operations and attributes have one; it is None for the global scope
        and for other nodes (members, arguments, enumerators, types).
        """
        from . import repository_id
        return repository_id.repository_id(self)

    @property
    def filepath(self):
        """File the node was defined in, or None (e.g. for :meth:`idl_parser.parser.IDLParser.load` without ``filepath``)."""
        return self._filepath

    @property
    def is_array(self):
        """True for an array type (:class:`~idl_parser.type.IDLArray`)."""
        return self._classname == 'IDLArray'

    @property
    def is_void(self):
        """True for ``void`` (:class:`~idl_parser.type.IDLVoid`)."""
        return self._classname == 'IDLVoid'

    @property
    def is_struct(self):
        """True for a struct (:class:`~idl_parser.struct.IDLStruct`)."""
        return self._classname == 'IDLStruct'

    @property
    def is_exception(self):
        """True for an exception (:class:`~idl_parser.struct.IDLException`)."""
        return self._classname == 'IDLException'

    @property
    def is_native(self):
        """True for a native type (:class:`~idl_parser.native.IDLNative`)."""
        return self._classname == 'IDLNative'

    @property
    def is_typedef(self):
        """True for a typedef (:class:`~idl_parser.typedef.IDLTypedef`)."""
        return self._classname == 'IDLTypedef'

    @property
    def is_sequence(self):
        """True for a sequence type (:class:`~idl_parser.type.IDLSequence`)."""
        return self._classname == 'IDLSequence'

    @property
    def is_map(self):
        """True for a map type (:class:`~idl_parser.type.IDLMap`, issue #118)."""
        return self._classname == 'IDLMap'

    @property
    def is_fixed(self):
        """True for a fixed-point type (:class:`~idl_parser.type.IDLFixed`, issue #119)."""
        return self._classname == 'IDLFixed'

    @property
    def is_primitive(self):
        """True for a primitive type (:class:`~idl_parser.type.IDLPrimitive`)."""
        return self._classname == 'IDLPrimitive'

    @property
    def is_interface(self):
        """True for an interface (:class:`~idl_parser.interface.IDLInterface`)."""
        return self._classname == 'IDLInterface'

    @property
    def is_valuetype(self):
        """True for a value type or an event type
        (:class:`~idl_parser.valuetype.IDLValueType`, issue #99)."""
        return self._classname in ('IDLValueType', 'IDLEventType')

    @property
    def is_eventtype(self):
        """True for an event type (:class:`~idl_parser.valuetype.IDLEventType`)."""
        return self._classname == 'IDLEventType'

    @property
    def is_enum(self):
        """True for an enum (:class:`~idl_parser.enum.IDLEnum`)."""
        return self._classname == 'IDLEnum'

    @property
    def is_bitmask(self):
        """True for a bitmask (:class:`~idl_parser.bitmask.IDLBitmask`)."""
        return self._classname == 'IDLBitmask'

    @property
    def is_bitset(self):
        """True for a bitset (:class:`~idl_parser.bitset.IDLBitset`)."""
        return self._classname == 'IDLBitset'

    @property
    def is_union(self):
        """True for a union (:class:`~idl_parser.union.IDLUnion`)."""
        return self._classname == 'IDLUnion'

    @property
    def is_const(self):
        """True for a constant (:class:`~idl_parser.const.IDLConst`)."""
        return self._classname == 'IDLConst'

    @property
    def classname(self):
        """Kind of the node as a string (``'IDLStruct'``, ``'IDLPrimitive'``, ...)."""
        return self._classname



    @property
    def name(self):
        """Name of the node, without its scope (``'T'`` for ``M::T``)."""
        return self._name

    @property
    def basename(self):
        """Last part of a scoped :attr:`name` (``'A::B'`` -> ``'B'``, ``'::A'`` -> ``'A'``)."""
        return self._name.split(self.sep)[-1]

    @property
    def pathname(self):
        """Scope part of a scoped :attr:`name` (``'A::B'`` -> ``'A'``, ``'::A::B'`` -> ``'A'``), or ``''``."""
        name = self._name
        if name.startswith(self.sep):
            name = name[len(self.sep):]
        if self.sep in name:
            return name[:name.rfind(self.sep)]
        return ''


    @property
    def parent(self):
        """Enclosing node, or None for the global module."""
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
        """True for the global module (the node without a parent)."""
        return self.parent == None

    @property
    def root_node(self):
        """The global module (:class:`~idl_parser.module.IDLModule`) this node belongs to."""
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
        return self._is_pending_forward(typename, ('forward_interfaces',))

    def is_pending_forward_declaration(self, typename):
        """True if typename names an interface, struct, union, valuetype or
        eventtype that has been forward-declared ("interface A;", "struct A;",
        "union A;", "valuetype A;", "eventtype A;") but whose definition has
        not been parsed yet.
        """
        return self._is_pending_forward(
            typename, ('forward_interfaces', 'forward_structs', 'forward_unions',
                       'forward_valuetypes', 'forward_eventtypes'))

    def _is_pending_forward(self, typename, kinds):
        name = str(typename).strip()
        if name.startswith(self.sep):
            name = name[len(self.sep):]
        if len(self.root_node.find_types(name)) > 0:
            return False
        from .module import definition_scopes
        for m in definition_scopes(self.root_node, self):
            prefix = m.full_path.lstrip(':')
            for kind in kinds:
                for n in getattr(m, kind, []):
                    full = prefix + self.sep + n if prefix else n
                    if name == n or name == full:
                        return True
        return False

    def check_element_types(self, typ):
        """Raise InvalidDataTypeException if an element type of the sequence,
        array or map ``typ`` (nested ones included) is not declared (issue #67).
        For a map, both the key and the value type are checked (issue #118).

        A type that has been forward-declared ("interface A;", "struct A;",
        "union A;") may be used before its definition, as with a direct member.
        """
        if getattr(typ, 'is_map', False):
            for t in (typ.key_type, typ.value_type):
                self._check_element_type(t)
                self.check_element_types(t)
            return
        while getattr(typ, 'is_sequence', False) or getattr(typ, 'is_array', False):
            typ = typ.inner_type
            self._check_element_type(typ)
            if getattr(typ, 'is_map', False):
                self.check_element_types(typ)
                return

    def _check_element_type(self, typ):
        """Raise InvalidDataTypeException if the element type ``typ`` is a
        name that is not declared."""
        from . import exception
        if typ.classname != 'IDLBasicType':
            return
        name = typ.name.strip()
        if name.startswith(self.sep):
            name = name[len(self.sep):]
        if len(typ.resolve()) > 0:
            return
        if self.is_pending_forward_declaration(name):
            return
        if self._is_enclosing_definition(name):
            return # recursive type: "struct Node { sequence<Node> children; };"
        print('Can not find Data Type (%s)\n' % typ.name)
        raise exception.InvalidDataTypeException(
            message='Can not find Data Type (%s)' % typ.name)

    def _is_enclosing_definition(self, name):
        """True if name is a struct, union or value type that encloses this node and is
        still being parsed (so it is not registered in its module yet)."""
        n = self.parent
        while n is not None and not n.is_root:
            if n.classname in ('IDLStruct', 'IDLUnion', 'IDLValueType', 'IDLEventType'):
                if name == n.name or name == n.full_path.lstrip(':'):
                    return True
            n = n.parent
        return False

    def refine_typename(self, typ):
        """Name of the definition that the type ``typ`` refers to.

        Sequences and maps keep their form with refined element types
        (``'sequence < T >'``, ``'map < K , V >'``), bounded strings give their base type, and a name
        that can not be resolved yet is returned as written.
        """
        return self._refine_typename(typ.name)

    def _lookup_scope(self):
        """The node whose scope type names written here are resolved from."""
        return self

    def _refine_typename(self, name):
        from . import type as idl_type
        name = name.strip()
        # 'sequence<long> [3]' is an array of sequences: keep it as written
        seq = idl_type.parse_sequence(name) if name.endswith('>') else None
        if seq is not None:
            # Nested types are refined recursively (issue #31). The bound of
            # a bounded sequence is not part of the type name (see .bound).
            return 'sequence < ' + self._refine_typename(seq[0]) + ' >'
        map_ = idl_type.parse_map(name) if name.endswith('>') else None
        if map_ is not None:
            # As with sequences, the bound is not part of the name (issue #118)
            return 'map < ' + self._refine_typename(map_[0]) + ' , ' + self._refine_typename(map_[1]) + ' >'
        bounded = idl_type.parse_bounded_string(name)
        if bounded is not None:
            return bounded[0]
        fixed = idl_type.parse_fixed(name)
        if fixed is not None:
            # The digits and scale are part of the type ('fixed<10, 2>', issue #119)
            return idl_type.fixed_name(*fixed)
        typs = self.root_node.find_types(name, scope=self._lookup_scope())
        if len(typs) == 0:
            # Not resolvable yet (e.g. a forward-declared interface): keep the name
            return name
        return typs[0].name
