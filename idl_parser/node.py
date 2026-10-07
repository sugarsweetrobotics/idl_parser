"""Base class of all nodes, and IDL annotations (``@name(...)``)."""
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
    def __init__(self, classname, name, parent):
        self._classname = classname
        self._parent = parent
        self._name = name
        self._filepath = None
        self.sep = '::'
        self._annotations = []

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
    def is_bitmask(self):
        return self._classname == 'IDLBitmask'

    @property
    def is_bitset(self):
        return self._classname == 'IDLBitset'

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
        return self._is_pending_forward(typename, ('forward_interfaces',))

    def is_pending_forward_declaration(self, typename):
        """True if typename names an interface, struct or union that has been
        forward-declared ("interface A;", "struct A;", "union A;") but whose
        definition has not been parsed yet.
        """
        return self._is_pending_forward(
            typename, ('forward_interfaces', 'forward_structs', 'forward_unions'))

    def _is_pending_forward(self, typename, kinds):
        name = str(typename).strip()
        if name.startswith(self.sep):
            name = name[len(self.sep):]
        if len(self.root_node.find_types(name)) > 0:
            return False
        found = []
        def walk(m):
            prefix = m.full_path.lstrip(':')
            for kind in kinds:
                for n in getattr(m, kind, []):
                    full = prefix + self.sep + n if prefix else n
                    if name == n or name == full:
                        found.append(full)
            for sub in getattr(m, 'modules', []):
                walk(sub)
        walk(self.root_node)
        return len(found) > 0

    def refine_typename(self, typ):
        return self._refine_typename(typ.name)

    def _refine_typename(self, name):
        from . import type as idl_type
        name = name.strip()
        # 'sequence<long> [3]' is an array of sequences: keep it as written
        seq = idl_type.parse_sequence(name) if name.endswith('>') else None
        if seq is not None:
            # Nested types are refined recursively (issue #31). The bound of
            # a bounded sequence is not part of the type name (see .bound).
            return 'sequence < ' + self._refine_typename(seq[0]) + ' >'
        bounded = idl_type.parse_bounded_string(name)
        if bounded is not None:
            return bounded[0]
        typs = self.root_node.find_types(name)
        if len(typs) == 0:
            # Not resolvable yet (e.g. a forward-declared interface): keep the name
            return name
        return typs[0].name
