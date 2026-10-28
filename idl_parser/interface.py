"""IDL interfaces, their operations and the arguments of the operations."""
import sys
from . import node
from . import exception
from . import definitions
from . import token_buffer
from . import repository_id

from . import type as idl_type

sep = '::'

class IDLArgument(node.IDLNode):
    """An argument of an operation, such as ``in long a``.

    :param parent: The :class:`IDLMethod` the argument belongs to.
    """
    def __init__(self, parent):
        super(IDLArgument, self).__init__('IDLArgument', '', parent)
        self._verbose = True
        self._dir = 'in'
        self._type = None

    def parse_blocks(self, blocks, filepath=None):
        """Read the argument from its tokens (``['out', 'T', 't']``).

        The direction may be omitted, in which case it is ``'in'``.
        """
        self._filepath= filepath
        annotations, blocks = node.parse_annotations(blocks)
        self._add_annotations(annotations)
        directions = ['in', 'out', 'inout']
        self._dir = 'in'
        if blocks[0] in directions:
            self._dir = blocks[0]
            blocks.pop(0)
            pass
        argument_name, argument_type = self._name_and_type(blocks)
        node.check_identifier(argument_name, 'argument of operation "%s"' % self.parent.name)
        self._name = argument_name
        self._type = idl_type.IDLType(argument_type, self)

    def to_simple_dic(self):
        """A one-line summary, e.g. ``'out T t'``."""
        dic = '%s %s %s' % (self.direction, self.type, self.name)
        return dic

    def to_dic(self):
        """The argument as a plain dict (for JSON or YAML output)."""
        dic = { 'name' : self.name,
                'classname' : self.classname,
                'type' : str(self.type),
                'direction' : self.direction,
                'filepath' : self.filepath }
        return self._with_annotations(dic)

    @property
    def direction(self):
        """``'in'``, ``'out'`` or ``'inout'``."""
        return self._dir

    @property
    def type(self):
        """Type of the argument (an :class:`~idl_parser.type.IDLTypeBase`).

        Use ``type.obj`` to get the definition of a non-primitive type.
        """
        return self._type

    def post_process(self):
        """Replace the type name by the name of its definition."""
        self._type._name = self.refine_typename(self.type)



class IDLMethod(node.IDLNode):
    """An operation of an interface, such as ``long f(in long a) raises (E);``.

    :param parent: The :class:`IDLInterface` the operation belongs to.
    """
    def __init__(self, parent):
        super(IDLMethod, self).__init__('IDLValue', '', parent)
        self._verbose = True
        self._returns = None
        self._arguments = []
        self._oneway = False
        self._raises = []
        self._contexts = []

    def parse_blocks(self, blocks, filepath=None):
        """Read the operation from its tokens, up to (not including) the ``;``.

        :raises ~idl_parser.exception.InvalidIDLSyntaxError: Parentheses do not
            match, or something other than ``raises (...)`` / ``context (...)``
            follows the arguments.
        """
        self._filepath=filepath

        annotations, blocks = node.parse_annotations(blocks)
        self._add_annotations(annotations)
        if blocks[0] == 'oneway':
            self._oneway = True
            blocks.pop(0)
        else:
            self._oneway = False

        self._returns = idl_type.IDLType(blocks[0], self)
        self._name = blocks[1]
        node.check_identifier(self._name, 'operation in "%s"' % self.parent.name)
        self._arguments = []

        if not blocks[2] == '(':
            print(' -- Invalid Interface Token (%s)' % blocks[1])
            print( blocks)

        self._raises = []
        self._contexts = []
        index = 3
        args_end = len(blocks)
        if blocks[2] == '(':
            # Read the arguments only up to the ")" that closes the argument
            # list; "raises (...)" and "context (...)" may follow it.
            close = node.matching_paren(blocks, 2)
            if close is None:
                raise exception.InvalidIDLSyntaxError(message='No ")" after the arguments of "%s"' % self._name)
            self._parse_clauses(blocks[close + 1:])
            args_end = close + 1
        argument_blocks = []
        while True:
            if index >= args_end:
                break
            token = blocks[index]
            if token.startswith('@') and index + 1 < len(blocks) and blocks[index + 1] == '(':
                # Annotation of an argument with parameters, e.g. @range(min=0, max=9):
                # keep its "(", "," and ")" out of the argument list splitting.
                end = node.matching_paren(blocks, index + 1)
                if end is None:
                    raise exception.InvalidIDLSyntaxError(message='No ")" in annotation "%s" of "%s"' % (token, self._name))
                argument_blocks.extend(blocks[index:end + 1])
                index = end + 1
                continue
            # A "," inside "< >" belongs to the type, e.g. sequence<long, 10> (issue #31)
            in_template = sum(t.count('<') - t.count('>') for t in argument_blocks) > 0
            if (token == ',' and not in_template) or token == ')':
                if len(argument_blocks) == 0:
                    break

                a = IDLArgument(self)
                self._arguments.append(a)
                a.parse_blocks(argument_blocks, self.filepath)

                argument_blocks = []
            else:
                argument_blocks.append(token)
            index = index + 1

    def _parse_clauses(self, blocks):
        """Parse "raises (E1, E2)" and "context ("a", "b")" after the arguments."""
        index = 0
        while index < len(blocks):
            keyword = blocks[index]
            if keyword not in ('raises', 'context'):
                raise exception.InvalidIDLSyntaxError(message='Unexpected token "%s" after the arguments of "%s"' % (keyword, self._name))
            if index + 1 >= len(blocks) or blocks[index + 1] != '(':
                raise exception.InvalidIDLSyntaxError(message='No "(" after "%s" of "%s"' % (keyword, self._name))
            close = node.matching_paren(blocks, index + 1)
            if close is None:
                raise exception.InvalidIDLSyntaxError(message='No ")" after "%s" of "%s"' % (keyword, self._name))
            names = [t for t in blocks[index + 2:close] if t != ',']
            if len(names) == 0:
                raise exception.InvalidIDLSyntaxError(message='Empty "%s (...)" of "%s"' % (keyword, self._name))
            if keyword == 'raises':
                self._raises.extend(names)
            else:
                self._contexts.extend(n.strip('"') for n in names)
            index = close + 1

    def to_simple_dic(self):
        """A compact summary: ``{name: {'returns': ..., 'params': [...]}}``."""
        return {self.name : {
                'returns' : str(self.returns),
                'params' : [a.to_simple_dic() for a in self.arguments]}}

    def to_dic(self):
        """The operation as a plain dict (for JSON or YAML output).

        ``'raises'`` and ``'context'`` are included only when they are written.
        """
        dic = { 'name' : self.name,
                'filepath' : self.filepath,
                'classname' : self.classname,
                'returns' : str(self._returns),
                'arguments' : [a.to_dic() for a in self.arguments]}
        if self._raises:
            dic['raises'] = list(self._raises)
        if self._contexts:
            dic['context'] = list(self._contexts)
        return self._with_annotations(dic)

    @property
    def returns(self):
        """Return type (an :class:`~idl_parser.type.IDLTypeBase`; ``void`` gives an
        :class:`~idl_parser.type.IDLVoid`).
        """
        return self._returns

    @property
    def oneway(self):
        """True if the operation is declared "oneway"."""
        return self._oneway

    @property
    def raises(self):
        """Exception names in "raises (...)", as written (not resolved)."""
        return list(self._raises)

    @property
    def exceptions(self):
        """Exceptions in "raises (...)" (list of
        :class:`~idl_parser.struct.IDLException`), in order.

        Each name is resolved from the scope of the interface, like a type name
        (issue #93), so the members of an exception are available through
        ``method.exceptions[0].members``.

        :raises ~idl_parser.exception.IDLCanNotFindException: A name in
            "raises (...)" is not a defined exception.
        """
        found = []
        for name in self._raises:
            xs = self.root_node.find_exceptions(name, scope=self.parent)
            if len(xs) == 0:
                raise exception.IDLCanNotFindException(
                    None, self.filepath,
                    'Can not find exception "%s" raised by "%s"' % (name, self.name))
            found.append(xs[0])
        return found

    @property
    def contexts(self):
        """Context names in "context (...)", without the quotes."""
        return list(self._contexts)

    @property
    def arguments(self):
        """Arguments (list of :class:`IDLArgument`), in order."""
        return self._arguments

    def argument_by_name(self, name):
        """The argument named ``name``, or None."""
        for a in self.arguments:
            if a.name == node.unescape(name):
                return a

        return None


    def forEachArgument(self, func):
        """Call ``func`` with each argument."""
        for a in self.arguments:
            func(a)

    def post_process(self):
        #self._returns = self.refine_typename(self.returns)
        #self.forEachArgument(lambda a : a.post_process())
        """Hook called after the interface has been parsed. Does nothing."""
        pass

class IDLAttribute(node.IDLNode):
    """An attribute of an interface, such as ``readonly attribute long x;`` (issue #101).

    ``attribute long a, b;`` declares two attributes, each an
    :class:`IDLAttribute`.

    :param name: Attribute name.
    :param parent: The :class:`IDLInterface` the attribute belongs to.
    """
    def __init__(self, name, parent):
        super(IDLAttribute, self).__init__('IDLAttribute', name, parent)
        self._type = None
        self._readonly = False
        self._getraises = []
        self._setraises = []

    @property
    def full_path(self):
        """Scoped name (``'M::I::x'``)."""
        return self.parent.full_path + sep + self.name

    @property
    def type(self):
        """Type of the attribute (an :class:`~idl_parser.type.IDLTypeBase`)."""
        return self._type

    @property
    def readonly(self):
        """True for a ``readonly attribute``."""
        return self._readonly

    @property
    def getraises(self):
        """Exception names raised when the attribute is read, as written:
        ``raises (...)`` of a readonly attribute, or ``getraises (...)``.
        """
        return list(self._getraises)

    @property
    def setraises(self):
        """Exception names in ``setraises (...)``, as written."""
        return list(self._setraises)

    def to_simple_dic(self, quiet=False):
        """A compact summary: ``{'attribute NAME': 'TYPE'}``
        (``'readonly attribute NAME'`` for a readonly one).
        """
        key = '%sattribute %s' % ('readonly ' if self.readonly else '', self.name)
        if quiet:
            return key
        return {key : str(self.type)}

    def to_dic(self):
        """The attribute as a plain dict (for JSON or YAML output).

        ``'getraises'`` and ``'setraises'`` are included only when they are written.
        """
        dic = { 'name' : self.name,
                'classname' : self.classname,
                'type' : str(self.type),
                'readonly' : self.readonly,
                'filepath' : self.filepath }
        if self._getraises:
            dic['getraises'] = list(self._getraises)
        if self._setraises:
            dic['setraises'] = list(self._setraises)
        return self._with_annotations(dic)


def parse_attributes(blocks, parent, filepath=None):
    """Read ``[readonly] attribute TYPE NAME[, NAME...] [raises clauses]``
    (the tokens up to, not including, the ``;``) and return a list of
    :class:`IDLAttribute`.

    :raises ~idl_parser.exception.InvalidIDLSyntaxError: The declaration is
        not valid IDL.
    """
    annotations, blocks = node.parse_annotations(blocks)
    readonly = blocks[0] == 'readonly'
    if readonly:
        blocks = blocks[1:]
    if not blocks or blocks[0] != 'attribute':
        raise exception.InvalidIDLSyntaxError(message='No "attribute" after "readonly"')
    blocks = blocks[1:]
    clause_keywords = ('raises',) if readonly else ('getraises', 'setraises')
    clauses = [i for i, t in enumerate(blocks) if t in ('raises', 'getraises', 'setraises')]
    end = clauses[0] if clauses else len(blocks)

    # "long a, b": one attribute per name; an attribute is not an array
    typename, names = node.split_declarators(blocks[:end], 'attribute declaration')
    if any('[' in n for n in names):
        raise exception.InvalidIDLSyntaxError(
            message='Invalid attribute declaration "%s"' % ' '.join(blocks))
    typename = ' '.join(typename)

    getraises, setraises = [], []
    index = end
    while index < len(blocks):
        keyword = blocks[index]
        if keyword not in clause_keywords:
            raise exception.InvalidIDLSyntaxError(
                message='Unexpected "%s" in the declaration of attribute "%s"' % (keyword, names[0]))
        if index + 1 >= len(blocks) or blocks[index + 1] != '(':
            raise exception.InvalidIDLSyntaxError(
                message='No "(" after "%s" of attribute "%s"' % (keyword, names[0]))
        close = node.matching_paren(blocks, index + 1)
        if close is None:
            raise exception.InvalidIDLSyntaxError(
                message='No ")" after "%s" of attribute "%s"' % (keyword, names[0]))
        exceptions = [t for t in blocks[index + 2:close] if t != ',']
        (setraises if keyword == 'setraises' else getraises).extend(exceptions)
        index = close + 1
    if (getraises or setraises) and len(names) > 1:
        # IDL allows raises clauses only on a single attribute declarator
        raise exception.InvalidIDLSyntaxError(
            message='Raises clauses are allowed only on a single attribute ("%s")' % ', '.join(names))

    attributes = []
    for name in names:
        a = IDLAttribute(name, parent)
        a._filepath = filepath
        a._readonly = readonly
        a._type = idl_type.IDLType(typename, a)
        a._getraises = list(getraises)
        a._setraises = list(setraises)
        a._add_annotations(annotations)
        attributes.append(a)
    return attributes


class IDLInterface(definitions.IDLDefinitionScope, node.IDLNode):
    """An ``interface``: its operations, attributes and the types and
    constants defined in it (issue #101).

    A type defined in an interface is scoped by it (``M::I::S``), and is
    available like one in a module (:attr:`structs`, :meth:`struct_by_name`, ...).

    :param name: Interface name.
    :param parent: Enclosing :class:`~idl_parser.module.IDLModule`.
    """
    def __init__(self, name, parent):
        super(IDLInterface, self).__init__('IDLInterface', name, parent)
        self._verbose = True
        self._methods = []
        self._attributes = []
        self._inheritances = []
        self._init_definitions()
        self._forward = False
        self._local = False
        self._abstract = False

    # The keyword of the definition, used in error messages.
    _kind = 'interface'

    @property
    def is_forward(self):
        """True if this node came from a forward declaration ("interface A;")."""
        return self._forward

    @property
    def is_local(self):
        """True for a ``local interface`` (issue #93)."""
        return self._local

    @property
    def is_abstract(self):
        """True for an ``abstract interface`` (issue #93)."""
        return self._abstract

    @property
    def inheritances(self):
        """Base interfaces (IDLInterface objects), in declaration order."""
        return list(self._inheritances)

    @property
    def full_path(self):
        """Scoped name (``'M::I'``; ``'::I'`` at the global scope)."""
        return self.parent.full_path + sep + self.name

    def to_simple_dic(self, quiet=False, full_path=False, recursive=False, member_only=False):
        """A compact summary: ``{'interface NAME': [{'inherits': [...]}, ...]}``.

        The first entry lists the full paths of the base interfaces; the rest
        are the ``to_simple_dic()`` of the operations, then of the attributes
        and of the types and constants defined in the interface.

        :param quiet: Return only ``'interface NAME'``.
        """
        if quiet:
            return 'interface %s' % self.name
        # The first entry is always {'inherits': [...]}; it is an empty list
        # for an interface without base interfaces.
        entries = [{'inherits' : [i.full_path for i in self.inheritances]}]
        entries += [m.to_simple_dic() for m in self.methods]
        entries += [a.to_simple_dic() for a in self.attributes]
        entries += self._definitions_simple_dic()
        dic = { 'interface ' + self.name : entries }
        return dic

    def to_dic(self):
        """The interface as a plain dict (for JSON or YAML output).

        ``'local'`` and ``'abstract'`` (``True``) are included only for a
        ``local`` or ``abstract`` interface. ``'attributes'`` is included only
        when the interface has attributes, and the definitions (``'structs'``,
        ``'typedefs'``, ...) only when it defines a type or a constant.
        """
        dic = { 'name' : self.name,
                'filepath' : self.filepath,
                'classname' : self.classname,
                'inheritances' : [i.full_path for i in self.inheritances],
                'methods' : [m.to_dic() for m in self.methods] }
        if self.attributes:
            dic['attributes'] = [a.to_dic() for a in self.attributes]
        if self.has_definitions:
            dic.update(self._definitions_dic())
        if self.is_local:
            dic['local'] = True
        if self.is_abstract:
            dic['abstract'] = True
        return self._with_annotations(dic)

    def _all_interfaces(self, kinds=('interfaces',)):
        """Definitions seen so far, keyed by full path without a leading '::'.

        :param kinds: Names of the module lists to look in (``'interfaces'``,
            ``'valuetypes'``, ``'eventtypes'``); ``'forward_' + kind`` lists
            their forward declarations.

        Returns (defined, forward): defined maps paths to the definitions,
        forward is the set of paths that have only been forward-declared.
        """
        defined = {}
        forward = set()
        def walk(m):
            prefix = m.full_path.lstrip(':')
            for kind in kinds:
                for i in getattr(m, kind):
                    defined[i.full_path.lstrip(':')] = i
                for n in getattr(m, 'forward_' + kind):
                    forward.add(prefix + sep + n if prefix else n)
            for sub in m.modules:
                walk(sub)
        walk(self.root_node)
        return defined, forward - set(defined)

    def _resolve_inheritance(self, name, ln, fn, kinds=('interfaces',),
                             what='interface which is generalization of'):
        """Resolve a base interface name following the OMG IDL scoping rules.

        '::A::B' is looked up from the global scope.  Any other (possibly
        scoped) name is looked up in the enclosing scope first and then in
        each outer scope in turn, so the innermost declaration wins.

        ``kinds`` selects what is looked up (see :meth:`_all_interfaces`) and
        ``what`` describes it in the error message; a valuetype resolves its
        base valuetypes and its supported interfaces with them (issue #99).
        """
        interfaces, forward = self._all_interfaces(kinds)
        name = node.unescape(name)
        if name.startswith(sep):
            candidates = [name[len(sep):]]
        else:
            candidates = []
            scope = self.parent
            while scope is not None:
                prefix = scope.full_path.lstrip(':')
                candidates.append(prefix + sep + name if prefix else name)
                scope = scope.parent
        for c in candidates:
            if c in interfaces:
                return interfaces[c]
            if c in forward:
                # OMG IDL: inheriting from an interface whose definition has
                # not been seen yet (only forward-declared) is an error.
                msg = '"%s" is only forward-declared; its definition must appear before "%s" inherits from it' % (name, self.name)
                if self._verbose: sys.stdout.write('# Error. %s\n' % msg)
                raise exception.IDLCanNotFindException(ln, fn, msg)
        msg ='Can not find "%s" %s "%s"' % (name, what, self.name)
        if self._verbose: sys.stdout.write('# Error. %s\n' % msg)
        raise exception.IDLCanNotFindException(ln, fn, msg)

    def parse_tokens(self, token_buf, filepath=None):
        """Parse the interface from ``token_buf``, starting after its name.

        Reads a forward declaration (``;``), or the optional base interfaces
        (``: A, B``) and the body up to ``};``.

        :raises ~idl_parser.exception.InvalidIDLSyntaxError: The declaration is
            not valid IDL.
        :raises ~idl_parser.exception.IDLCanNotFindException: A base interface is
            not defined (or only forward-declared).
        """
        self._filepath=filepath
        ln, fn, token = token_buf.pop()
        if token == ';': # Forward declaration (interface A;)
            self._forward = True
            return
        pending_name = None
        if token is not None and token.startswith(':') and not token.startswith(sep) and token != ':':
            # "B :A" reaches here as the single token ":A"
            pending_name = token[1:]
            token = ':'
        if token == ':': # Detect Inheritance (interface X : A, B, ... {)
            while True:
                if pending_name is not None:
                    name, pending_name = pending_name, None
                else:
                    ln, fn, name = token_buf.pop()
                if name is None or name in ('{', ',', ';'):
                    msg = 'Base interface name is expected after "%s" in the declaration of "%s"' % (':' if name is None else name, self.name)
                    if self._verbose: sys.stdout.write('# Error. %s\n' % msg)
                    raise exception.InvalidIDLSyntaxError(ln, fn, msg)
                base = self._resolve_inheritance(name, ln, fn)
                if base in self._inheritances:
                    msg = '"%s" is inherited more than once by "%s"' % (name, self.name)
                    if self._verbose: sys.stdout.write('# Error. %s\n' % msg)
                    raise exception.InvalidIDLSyntaxError(ln, fn, msg)
                self._inheritances.append(base)
                ln, fn, token = token_buf.pop()
                if token != ',':
                    break

        kakko = token
        if not kakko == '{':
            if self._verbose: sys.stdout.write('# Error. No kakko "{".\n')
            raise exception.InvalidIDLSyntaxError(ln, fn, 'No "{" in the declaration of interface "%s"' % self.name)
        self._parse_body(token_buf, filepath)

    def _parse_body(self, token_buf, filepath=None):
        """Parse the body after its ``{``, up to and including ``};``."""
        block_tokens = []
        block_ln = None  # where the declaration starts (issue #141)
        while True:

            ln, fn, token = token_buf.pop()
            repository_id.take_pragmas(self, token_buf)
            if token == None:
                if self._verbose: sys.stdout.write('# Error. No kokka "}".\n')
                raise exception.InvalidIDLSyntaxError(ln, fn, 'No "}" in the declaration of %s "%s"' % (self._kind, self.name))

            elif token == '}':
                ln, fn, token = token_buf.pop()
                if not token == ';':
                    if self._verbose: sys.stdout.write('# Error. No semi-colon after "}".\n')
                    raise exception.InvalidIDLSyntaxError(ln, fn, 'No ";" after "}" in the declaration of %s "%s"' % (self._kind, self.name))
                break

            if token in definitions.definition_keywords:
                annotations, rest = node.parse_annotations(block_tokens)
                if not rest:
                    # A type or constant defined in the interface (issue #101)
                    self.parse_definition(token, token_buf, filepath, annotations)
                    block_tokens = []
                    continue

            if token == ';':
                if block_tokens:
                    token_buffer.set_line(block_ln)
                    self._parse_block(block_tokens, ln, fn)
                block_tokens = []
                continue
            if not block_tokens:
                block_ln = ln
            block_tokens.append(token)
        self._post_process()

    def _post_process(self):
        self.forEachMethod(lambda m : m.post_process())

    def _parse_block(self, blocks, ln=None, fn=None):
        annotations, rest = node.parse_annotations(blocks)
        if rest and rest[0] in ('typeid', 'typeprefix') and not annotations:
            # "typeid N "ID";" / "typeprefix N "P";" (issue #135)
            repository_id.parse_declaration(rest[0], rest[1:], self, ln, fn)
            return
        if rest and rest[0] in ('attribute', 'readonly'):
            attributes = parse_attributes(blocks, self, self.filepath)
            self._attributes.extend(attributes)
            self._definitions.extend(attributes)
            return
        v = IDLMethod(self)
        v.parse_blocks(blocks, self.filepath)
        self._methods.append(v)
        self._definitions.append(v)

    @property
    def methods(self):
        """Operations (list of :class:`IDLMethod`), in order."""
        return self._methods

    @property
    def attributes(self):
        """Attributes (list of :class:`IDLAttribute`), in order (issue #101)."""
        return self._attributes

    def attribute_by_name(self, name):
        """The attribute named ``name``, or None.

        Attributes of base interfaces are not searched.
        """
        for a in self.attributes:
            if node.unescape(name) == a.name:
                return a
        return None

    def method_by_name(self, name):
        """The operation named ``name``, or None.

        Operations of base interfaces are not searched.
        """
        for m in self.methods:
            if node.unescape(name) == m.name:
                return m
        return None

    def forEachMethod(self, func):
        """Call ``func`` with each operation."""
        for m in self.methods:
            func(m)


