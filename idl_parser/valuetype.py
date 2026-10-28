"""IDL value types (``valuetype``) and event types (``eventtype``) (issue #99).

A value type is read like an interface: it can have operations,
attributes and type definitions. In addition it has state members
(``public long x;``), initializers (``factory create(in long x);``), base
value types (``: truncatable B``) and supported interfaces (``supports I``).
A boxed value type (``valuetype V long;``) wraps a single type.
An ``eventtype`` has the same form as a ``valuetype``.
"""
import sys

from . import node
from . import exception
from . import interface
from . import struct
from . import type as idl_type

sep = '::'


class IDLStateMember(struct.IDLMember):
    """A state member of a value type, such as ``public long x;``.

    It is read like a struct member (:attr:`type`, :attr:`name`), and
    remembers whether it is ``public`` or ``private``.

    :param parent: The :class:`IDLValueType` the member belongs to.
    """
    def __init__(self, parent):
        super(IDLStateMember, self).__init__(parent)
        self._classname = 'IDLStateMember'
        self._public = True

    @property
    def is_public(self):
        """True for a ``public`` member, False for a ``private`` one."""
        return self._public

    @property
    def visibility(self):
        """``'public'`` or ``'private'``."""
        return 'public' if self._public else 'private'

    def to_simple_dic(self, recursive=False, member_only=False):
        """A compact summary: ``{'public NAME': type_name}``
        (``'private NAME'`` for a private member)."""
        return {'%s %s' % (self.visibility, self.name) : str(self.type)}

    def to_dic(self):
        """The member as a plain dict (for JSON or YAML output)."""
        dic = super(IDLStateMember, self).to_dic()
        dic['visibility'] = self.visibility
        return dic

    def post_process(self):
        """Check the type, as for a struct member.

        A value type may refer to itself (``valuetype Node { public Node next; };``).
        """
        name = self._type.name.strip()
        if self._type.classname == 'IDLBasicType' and self._is_enclosing_definition(name.lstrip(':')):
            return
        super(IDLStateMember, self).post_process()


class IDLFactory(interface.IDLMethod):
    """An initializer of a value type, such as
    ``factory create(in long x) raises (E);``.

    It is read like an operation (:attr:`arguments`, :attr:`raises`,
    :attr:`exceptions`) but has no return type.

    :param parent: The :class:`IDLValueType` the initializer belongs to.
    """
    def __init__(self, parent):
        super(IDLFactory, self).__init__(parent)
        self._classname = 'IDLFactory'

    def parse_blocks(self, blocks, filepath=None):
        """Read the initializer from its tokens (``['factory', 'create', '(', ...]``),
        up to (not including) the ``;``."""
        annotations, blocks = node.parse_annotations(blocks)
        if len(blocks) < 3 or blocks[0] != 'factory' or blocks[2] != '(':
            raise exception.InvalidIDLSyntaxError(
                message='Invalid factory declaration "%s"' % ' '.join(blocks))
        super(IDLFactory, self).parse_blocks(['void'] + blocks[1:], filepath)
        self._returns = None
        self._add_annotations(annotations)

    def to_simple_dic(self):
        """A compact summary: ``{'factory NAME': [argument summaries]}``."""
        return {'factory ' + self.name : [a.to_simple_dic() for a in self.arguments]}

    def to_dic(self):
        """The initializer as a plain dict (for JSON or YAML output), like an
        operation without ``'returns'``."""
        dic = super(IDLFactory, self).to_dic()
        del dic['returns']
        return dic


class IDLValueType(interface.IDLInterface):
    """A ``valuetype``: its state members, initializers, operations,
    attributes and the types and constants defined in it (issue #99).

    Base value types are in :attr:`inheritances`, supported interfaces in
    :attr:`supports`. A boxed value type (``valuetype V long;``) has
    :attr:`is_boxed` True and its type in :attr:`boxed_type`.

    :param name: Value type name.
    :param parent: Enclosing :class:`~idl_parser.module.IDLModule`.
    """
    _kind = 'valuetype'

    def __init__(self, name, parent):
        super(IDLValueType, self).__init__(name, parent)
        self._classname = 'IDLValueType'
        self._custom = False
        self._truncatable = False
        self._supports = []
        self._state_members = []
        self._factories = []
        self._boxed_type = None

    @property
    def is_custom(self):
        """True for a ``custom valuetype`` (custom marshaling)."""
        return self._custom

    @property
    def is_truncatable(self):
        """True if the base value type is written ``: truncatable B``."""
        return self._truncatable

    @property
    def is_boxed(self):
        """True for a boxed value type (``valuetype V long;``)."""
        return self._boxed_type is not None

    @property
    def boxed_type(self):
        """The type a boxed value type wraps, or None if it is not boxed.

        A named type is resolved to its definition, as for
        :attr:`idl_parser.typedef.IDLTypedef.type`.

        :raises ~idl_parser.exception.InvalidDataTypeException: The named type
            is not defined.
        """
        if self._boxed_type is None:
            return None
        if self._boxed_type.classname == 'IDLBasicType':
            typs = self._boxed_type.resolve()
            if len(typs) == 0:
                raise exception.InvalidDataTypeException(
                    message='Can not find Data Type (%s)' % self._boxed_type.ref_name)
            return typs[0]
        return self._boxed_type

    @property
    def inheritances(self):
        """Base value types (:class:`IDLValueType` objects), in declaration order."""
        return list(self._inheritances)

    @property
    def supports(self):
        """Supported interfaces (:class:`~idl_parser.interface.IDLInterface`
        objects) in ``supports (...)``, in declaration order."""
        return list(self._supports)

    @property
    def state_members(self):
        """State members (list of :class:`IDLStateMember`), in order."""
        return self._state_members

    def state_member_by_name(self, name):
        """The state member named ``name``, or None.

        Members of base value types are not searched.
        """
        for m in self._state_members:
            if m.name == node.unescape(name):
                return m
        return None

    @property
    def factories(self):
        """Initializers (list of :class:`IDLFactory`), in order."""
        return self._factories

    def factory_by_name(self, name):
        """The initializer named ``name``, or None."""
        for f in self._factories:
            if f.name == node.unescape(name):
                return f
        return None

    def to_simple_dic(self, quiet=False, full_path=False, recursive=False, member_only=False):
        """A compact summary: ``{'valuetype NAME': [{'inherits': [...]}, ...]}``.

        The first entry lists the full paths of the base value types; a
        ``{'supports': [...]}`` entry follows when interfaces are supported.
        The rest are the ``to_simple_dic()`` of the state members, the
        initializers, the operations, the attributes and the definitions.
        A boxed value type gives ``{'valuetype NAME': 'TYPE'}``.

        :param quiet: Return only ``'valuetype NAME'``.
        """
        key = '%s %s' % (self._kind, self.full_path if full_path else self.name)
        if quiet:
            return key
        if self.is_boxed:
            return {key : str(self._boxed_type)}
        entries = [{'inherits' : [v.full_path for v in self.inheritances]}]
        if self._supports:
            entries.append({'supports' : [i.full_path for i in self.supports]})
        entries += [m.to_simple_dic() for m in self.state_members]
        entries += [f.to_simple_dic() for f in self.factories]
        entries += [m.to_simple_dic() for m in self.methods]
        entries += [a.to_simple_dic() for a in self.attributes]
        entries += self._definitions_simple_dic()
        if member_only:
            return entries
        return {key : entries}

    def to_dic(self):
        """The value type as a plain dict (for JSON or YAML output).

        ``'abstract'``, ``'custom'`` and ``'truncatable'`` (``True``) are
        included only when they are written, ``'boxed_type'`` only for a boxed
        value type, and ``'attributes'`` and the definitions only when there
        are any.
        """
        dic = { 'name' : self.name,
                'filepath' : self.filepath,
                'classname' : self.classname }
        if self.is_boxed:
            dic['boxed_type'] = str(self._boxed_type)
        else:
            dic.update({ 'inheritances' : [v.full_path for v in self.inheritances],
                         'supports' : [i.full_path for i in self.supports],
                         'state_members' : [m.to_dic() for m in self.state_members],
                         'factories' : [f.to_dic() for f in self.factories],
                         'methods' : [m.to_dic() for m in self.methods] })
            if self.attributes:
                dic['attributes'] = [a.to_dic() for a in self.attributes]
            if self.has_definitions:
                dic.update(self._definitions_dic())
        for flag in ('abstract', 'custom', 'truncatable'):
            if getattr(self, 'is_' + flag):
                dic[flag] = True
        return self._with_annotations(dic)

    def _error(self, ln, fn, message):
        if self._verbose: sys.stdout.write('# Error. %s\n' % message)
        raise exception.InvalidIDLSyntaxError(ln, fn, message)

    def parse_tokens(self, token_buf, filepath=None):
        """Parse the value type from ``token_buf``, starting after its name.

        Reads a forward declaration (``;``), a boxed value type (``TYPE ;``),
        or the optional base value types (``: [truncatable] A, B``), the
        supported interfaces (``supports I, J``) and the body up to ``};``.

        :raises ~idl_parser.exception.InvalidIDLSyntaxError: The declaration is
            not valid IDL.
        :raises ~idl_parser.exception.IDLCanNotFindException: A base value type
            or a supported interface is not defined (or only forward-declared).
        """
        self._filepath = filepath
        ln, fn, token = token_buf.pop()
        if token is None:
            self._error(ln, fn, 'No ";" or "{" after %s "%s"' % (self._kind, self.name))
        if token == ';': # Forward declaration (valuetype V;)
            self._forward = True
            return

        if token != '{' and token != 'supports' and not token.startswith(':'):
            self._parse_boxed(token, token_buf, ln, fn)
            return

        if token.startswith(':') and not token.startswith(sep):
            # ": B" or ":B" (one token)
            names, token = self._read_names([token[1:]] if token != ':' else [],
                                            token_buf, ln, fn, 'base %s' % self._kind)
            if names[0][0] == 'truncatable':
                if self._abstract:
                    self._error(ln, fn, 'An abstract %s "%s" can not be truncatable' % (self._kind, self.name))
                self._truncatable = True
                names[0].pop(0)
            for name in self._single_names(names, ln, fn, 'base %s' % self._kind):
                base = self._resolve_inheritance(name, ln, fn, ('valuetypes', 'eventtypes'),
                                                 'valuetype which is a base of')
                if base in self._inheritances:
                    self._error(ln, fn, '"%s" is inherited more than once by "%s"' % (name, self.name))
                self._inheritances.append(base)
        if token == 'supports':
            names, token = self._read_names([], token_buf, ln, fn, 'supported interface')
            for name in self._single_names(names, ln, fn, 'supported interface'):
                i = self._resolve_inheritance(name, ln, fn, ('interfaces',),
                                              'interface supported by')
                if i in self._supports:
                    self._error(ln, fn, '"%s" is supported more than once by "%s"' % (name, self.name))
                self._supports.append(i)
        if token != '{':
            self._error(ln, fn, 'No "{" in the declaration of %s "%s"' % (self._kind, self.name))
        self._parse_body(token_buf, filepath)

    def _read_names(self, tokens, token_buf, ln, fn, what):
        """Read "A, B, ..." (after the tokens already read) up to "{" or
        "supports". Returns the names split at "," (lists of tokens) and the
        token after them."""
        while True:
            ln2, fn2, t = token_buf.pop()
            if t is None or t in ('{', 'supports', ';', '}'):
                break
            tokens.append(t)
        groups = [[]]
        for x in tokens:
            if x == ',':
                groups.append([])
            else:
                groups[-1].append(x)
        if any(len(g) == 0 for g in groups):
            self._error(ln, fn, 'Name of a %s is expected in the declaration of "%s"' % (what, self.name))
        return groups, t

    def _single_names(self, groups, ln, fn, what):
        for g in groups:
            if len(g) != 1:
                self._error(ln, fn, 'Invalid %s "%s" in the declaration of "%s"' % (what, ' '.join(g), self.name))
        return [g[0] for g in groups]

    def _parse_boxed(self, token, token_buf, ln, fn):
        """Read the type of a boxed value type up to ``;``."""
        if self._kind != 'valuetype':
            self._error(ln, fn, 'No "{" in the declaration of %s "%s" (only a valuetype can be boxed)' % (self._kind, self.name))
        if self._abstract or self._custom:
            self._error(ln, fn, 'A boxed valuetype "%s" can not be abstract or custom' % self.name)
        tokens = [token]
        while True:
            ln2, fn2, t = token_buf.pop()
            if t is None or t in ('{', '}'):
                self._error(ln, fn, 'No ";" after boxed valuetype "%s"' % self.name)
            if t == ';':
                break
            tokens.append(t)
        self._boxed_type = idl_type.IDLType(' '.join(tokens), self)
        if self._boxed_type.classname == 'IDLBasicType':
            if self.is_pending_forward_declaration(self._boxed_type.name):
                return
            if len(self._boxed_type.resolve()) == 0:
                raise exception.InvalidDataTypeException(
                    message='Can not find Data Type (%s)' % self._boxed_type.ref_name)
        self.check_element_types(self._boxed_type)

    def _parse_block(self, blocks):
        annotations, rest = node.parse_annotations(blocks)
        if rest and rest[0] in ('public', 'private'):
            if self._abstract:
                raise exception.InvalidIDLSyntaxError(
                    message='An abstract %s "%s" can not have state members' % (self._kind, self.name))
            self._state_members.extend(self._parse_state_members(annotations, rest))
            return
        if rest and rest[0] == 'factory':
            if self._abstract:
                raise exception.InvalidIDLSyntaxError(
                    message='An abstract %s "%s" can not have factories' % (self._kind, self.name))
            f = IDLFactory(self)
            f.parse_blocks(blocks, self.filepath)
            self._factories.append(f)
            return
        super(IDLValueType, self)._parse_block(blocks)

    def _parse_state_members(self, annotations, blocks):
        """``public T a, b[3]`` -> one IDLStateMember per name."""
        public = blocks[0] == 'public'
        typename, declarators = node.split_declarators(blocks[1:], 'state member declaration')
        members = []
        for name in declarators:
            m = IDLStateMember(self)
            m.parse_blocks(typename + [name], self.filepath)
            m._add_annotations(annotations)
            m._public = public
            members.append(m)
        return members

    def _post_process(self):
        for m in self._state_members:
            m.post_process()
        super(IDLValueType, self)._post_process()


class IDLEventType(IDLValueType):
    """An ``eventtype``. It has the same form as a :class:`IDLValueType`
    (except that it can not be boxed), and :attr:`~idl_parser.node.IDLNode.is_eventtype`
    is True (issue #99).

    :param name: Event type name.
    :param parent: Enclosing :class:`~idl_parser.module.IDLModule`.
    """
    _kind = 'eventtype'

    def __init__(self, name, parent):
        super(IDLEventType, self).__init__(name, parent)
        self._classname = 'IDLEventType'
