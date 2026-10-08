"""IDL interfaces, their operations and the arguments of the operations."""
import sys
from . import node
from . import exception

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
            if a.name == name:
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

class IDLInterface(node.IDLNode):
    """An ``interface`` and its operations.

    :param name: Interface name.
    :param parent: Enclosing :class:`~idl_parser.module.IDLModule`.
    """
    def __init__(self, name, parent):
        super(IDLInterface, self).__init__('IDLInterface', name, parent)
        self._verbose = True
        self._methods = []
        self._inheritances = []
        self._forward = False

    @property
    def is_forward(self):
        """True if this node came from a forward declaration ("interface A;")."""
        return self._forward

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
        are the ``to_simple_dic()`` of the operations.

        :param quiet: Return only ``'interface NAME'``.
        """
        if quiet:
            return 'interface %s' % self.name
        # The first entry is always {'inherits': [...]}; it is an empty list
        # for an interface without base interfaces.
        entries = [{'inherits' : [i.full_path for i in self.inheritances]}]
        entries += [m.to_simple_dic() for m in self.methods]
        dic = { 'interface ' + self.name : entries }
        return dic

    def to_dic(self):
        """The interface as a plain dict (for JSON or YAML output)."""
        dic = { 'name' : self.name,
                'filepath' : self.filepath,
                'classname' : self.classname,
                'inheritances' : [i.full_path for i in self.inheritances],
                'methods' : [m.to_dic() for m in self.methods] }
        return self._with_annotations(dic)

    def _all_interfaces(self):
        """Interfaces seen so far, keyed by full path without a leading '::'.

        Returns (defined, forward): defined maps paths to IDLInterface objects,
        forward is the set of paths that have only been forward-declared.
        """
        defined = {}
        forward = set()
        def walk(m):
            prefix = m.full_path.lstrip(':')
            for i in m.interfaces:
                defined[i.full_path.lstrip(':')] = i
            for n in m.forward_interfaces:
                forward.add(prefix + sep + n if prefix else n)
            for sub in m.modules:
                walk(sub)
        walk(self.root_node)
        return defined, forward - set(defined)

    def _resolve_inheritance(self, name, ln, fn):
        """Resolve a base interface name following the OMG IDL scoping rules.

        '::A::B' is looked up from the global scope.  Any other (possibly
        scoped) name is looked up in the enclosing scope first and then in
        each outer scope in turn, so the innermost declaration wins.
        """
        interfaces, forward = self._all_interfaces()
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
        msg ='Can not find "%s" interface which is generalization of "%s"' % (name, self.name)
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

        block_tokens = []
        while True:

            ln, fn, token = token_buf.pop()
            if token == None:
                if self._verbose: sys.stdout.write('# Error. No kokka "}".\n')
                raise exception.InvalidIDLSyntaxError(ln, fn, "No \"}\" in the declaration of interface \"%s\"" % self.name)

            elif token == '}':
                ln, fn, token = token_buf.pop()
                if not token == ';':
                    if self._verbose: sys.stdout.write('# Error. No semi-colon after "}".\n')
                    raise exception.InvalidIDLSyntaxError(ln, fn, 'No ";" after "}" in the declaration of interface "%s"' % self.name)
                break

            if token == ';':
                self._parse_block(block_tokens)
                block_tokens = []
                continue
            block_tokens.append(token)
        self._post_process()

    def _post_process(self):
        self.forEachMethod(lambda m : m.post_process())

    def _parse_block(self, blocks):
        v = IDLMethod(self)
        v.parse_blocks(blocks, self.filepath)
        self._methods.append(v)

    @property
    def methods(self):
        """Operations (list of :class:`IDLMethod`), in order."""
        return self._methods

    def method_by_name(self, name):
        """The operation named ``name``, or None.

        Operations of base interfaces are not searched.
        """
        for m in self.methods:
            if name == m.name:
                return m
        return None

    def forEachMethod(self, func):
        """Call ``func`` with each operation."""
        for m in self.methods:
            func(m)


