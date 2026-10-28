"""IDL modules, including the global scope.

:class:`IDLModule` is also the node returned by
:meth:`idl_parser.parser.IDLParser.load`: the global scope is a module
without a name (internally ``'__global__'``).
"""
import os, sys, traceback, warnings

from . import node, type
from . import interface, definitions, valuetype, repository_id
from .exception import InvalidIDLSyntaxError, UnsupportedIDLSyntaxWarning
global_namespace = '__global__'
sep = '::'

# Keywords of valid IDL definitions that are not supported yet. Such a
# definition is skipped with an UnsupportedIDLSyntaxWarning (issue #76).
unsupported_keywords = ('component',
                        'home', 'porttype', 'connector',
                        'import')

# Declarations that set repository IDs (issue #135)
repository_id_keywords = ('typeid', 'typeprefix')

# Modifiers written before a definition keyword ("local interface",
# "abstract valuetype"). They apply to the definition after them; an
# interface records "local" and "abstract" (issue #93), a valuetype or an
# eventtype "abstract" and "custom" (issue #99), and the others are dropped.
modifier_keywords = ('abstract', 'local', 'custom')

class IDLModule(definitions.IDLDefinitionScope, node.IDLNode):
    """A ``module`` (or the global scope) and the definitions in it.

    Definitions are available by kind (:attr:`structs`, :attr:`interfaces`,
    ...), by name (:meth:`struct_by_name`, ...) and through callbacks
    (:meth:`for_each_struct`, ...). A module that is opened again
    (``module M { ... }; module M { ... };``) is a single node.

    :param name: Module name; ``None`` for the global scope.
    :param parent: Enclosing module; ``None`` for the global scope.
    """
    def __init__(self, name=None, parent = None):
        super(IDLModule, self).__init__('IDLModule', name, parent)
        self._verbose = False
        if name is None:
            self._name = global_namespace

        self._interfaces = []
        self._forward_interfaces = []
        self._valuetypes = []
        self._forward_valuetypes = []
        self._eventtypes = []
        self._forward_eventtypes = []
        self._init_definitions()
        self._modules = []
        self._filepaths = []
        # typeid / typeprefix declarations, kept in the global scope (issue #135)
        self._type_declarations = []

    @property
    def filepath(self):
        """File where the module is first opened (an absolute path), or
        None. A module opened in several files (``module M { ... };`` in
        a.idl and in b.idl) lists them all in :attr:`filepaths` (issue #142).
        For the global scope it is the first file parsed."""
        return self._filepath

    @property
    def filepaths(self):
        """Files where the module is opened (absolute paths), in the order
        they are read (issue #142)."""
        return list(self._filepaths)

    @property
    def is_global(self):
        """True if this is the global scope."""
        return self.name == global_namespace

    @property
    def full_path(self):
        """Scoped name of the module (``'A::B'``); ``''`` for the global scope."""
        if self.parent is None:
            return '' # self.name
        else:
            if len(self.parent.full_path) == 0:
                return self.name
            return self.parent.full_path + sep + self.name

    def to_simple_dic(self, quiet=False):
        """A compact summary for printing: ``{'module NAME': [...]}``.

        The list holds the ``to_simple_dic()`` of each definition, grouped by kind.

        :param quiet: Passed to the definitions (only their kind and name).
        """
        dic = {'module %s' % self.name : [s.to_simple_dic(quiet) for s in self.structs] +
               [x.to_simple_dic(quiet) for x in self.exceptions] +
               [i.to_simple_dic(quiet) for i in self.interfaces] +
               [v.to_simple_dic(quiet) for v in self.valuetypes] +
               [v.to_simple_dic(quiet) for v in self.eventtypes] +
               [m.to_simple_dic(quiet) for m in self.modules] +
               [e.to_simple_dic(quiet) for e in self.enums] +
               [b.to_simple_dic(quiet) for b in self.bitmasks] +
               [b.to_simple_dic(quiet) for b in self.bitsets] +
               [u.to_simple_dic(quiet) for u in self.unions] +
               [t.to_simple_dic(quiet) for t in self.typedefs] +
               [n.to_simple_dic(quiet) for n in self.natives] +
               [t.to_simple_dic(quiet) for t in self.consts]}
        return dic

    def to_dic(self):
        """All the contents as plain dicts and lists (for JSON or YAML output)."""
        dic = { 'name' : self.name,
                'filepath' : self.filepath,
                'classname' : self.classname,
                'interfaces' : [i.to_dic() for i in self.interfaces],
                'valuetypes' : [v.to_dic() for v in self.valuetypes],
                'eventtypes' : [v.to_dic() for v in self.eventtypes] }
        defs = self._definitions_dic()
        consts = defs.pop('consts')
        dic.update(defs)
        dic['modules'] = [m.to_dic() for m in self.modules]
        dic['consts'] = consts  # same key order as before (issue #101)
        return self._with_annotations(dic)


    def parse_tokens(self, token_buf, filepath=None):
        """Parse definitions from ``token_buf`` into this module.

        For a named module, the tokens start at ``{`` and are read up to the
        matching ``}``; for the global scope, up to the end of the input.

        :param token_buf: :class:`~idl_parser.token_buffer.TokenBuffer` to read from.
        :param filepath: File name recorded in the parsed nodes.
        :raises ~idl_parser.exception.InvalidIDLSyntaxError: The input is not valid IDL.
        """
        # A module opened in several files keeps the file where it is first
        # opened, and lists them all in filepaths (issue #142)
        if self._filepath is None:
            self._filepath = filepath
        if filepath is not None and filepath not in self._filepaths:
            self._filepaths.append(filepath)
        if not self.name == global_namespace:
            ln, fn, kakko = token_buf.pop()
            if not kakko == '{':
                if self._verbose: sys.stdout.write('# Error. No kakko "{".\n')
                raise InvalidIDLSyntaxError()

        annotations = []
        modifiers = []
        while True:
            ln, fn, token = token_buf.pop()
            repository_id.take_pragmas(self, token_buf)
            if token is not None and token.startswith('@'):
                # Annotations apply to the next definition (issue #39).
                annotations.append(self._parse_annotation(token, token_buf))
                continue
            if token in modifier_keywords:
                # "local interface I", "@a abstract interface I": the modifier
                # and the annotations before it apply to the next definition.
                modifiers.append(token)
                continue
            pending_annotations, annotations = annotations, []
            pending_modifiers, modifiers = modifiers, []
            # Record the file each definition is written in, which differs
            # from ``filepath`` for the lines pasted by #include (issue #109).
            fp = fn if fn else filepath

            if token == None:
                if self.name == global_namespace:
                    break
                if self._verbose: sys.stdout.write('# Error. No kokka "}".\n')
                raise InvalidIDLSyntaxError()
            elif token == 'module' and _is_template_module(token_buf):
                # A template module ("module MT <typename T> { ... };") or
                # its instantiation ("module MI = MT<long>;"). Not supported
                # yet, so it is skipped like the definitions in
                # unsupported_keywords (issue #121).
                words = self._skip_definition(token, token_buf, ln, fn)
                _warn('%s: unsupported template module "%s" is skipped.'
                      % (_where(ln, fn), ' '.join(words)),
                      UnsupportedIDLSyntaxWarning)
            elif token == 'module':
                ln, fn, name_ = token_buf.pop()
                node.check_identifier(name_, 'module', ln, fn)
                m = self.module_by_name(name_)
                if m == None:
                    m = IDLModule(name_, self)
                    self._modules.append(m)
                    self._definitions.append(m)
                # A #pragma prefix in an earlier opening ended with it (issue #135)
                m._prefix_state = self._prefix_state
                m._add_annotations(pending_annotations)
                m.parse_tokens(token_buf, filepath=fp)
            elif token == 'interface':
                ln, fn, name_ = token_buf.pop()
                node.check_identifier(name_, 'interface', ln, fn)
                s = interface.IDLInterface(name_, self)
                s._add_annotations(pending_annotations)
                s._local = 'local' in pending_modifiers
                s._abstract = 'abstract' in pending_modifiers
                s.parse_tokens(token_buf, filepath=fp)

                if s.is_forward:
                    # Forward declaration ("interface A;"): remember the name only.
                    # The definition, if any, is added to interfaces when it appears.
                    if node.unescape(name_) not in self._forward_interfaces:
                        self._forward_interfaces.append(node.unescape(name_))
                    self._definitions.append(s)
                    continue

                s_ = self.interface_by_name(name_)
                if s_:
                    if self._verbose: sys.stdout.write('# Error. Same Interface Defined (%s)\n' % name_)
                #    raise InvalidIDLSyntaxError
                else:
                    self._interfaces.append(s)
                    self._definitions.append(s)

            elif token in ('valuetype', 'eventtype'):
                self._parse_valuetype(token, token_buf, pending_annotations, pending_modifiers, fp)

            elif token in definitions.definition_keywords:
                self.parse_definition(token, token_buf, fp, pending_annotations)

            elif token == '}':
                break

            elif token == ';':
                pass

            elif token in repository_id_keywords:
                self._parse_repository_id_declaration(token, token_buf, ln, fn)

            elif any(a.name == 'annotation' for a in pending_annotations):
                # An annotation definition ("@annotation A { ... };"). It
                # declares no type, so it is skipped without a warning.
                self._skip_definition(token, token_buf, ln, fn)

            elif token in unsupported_keywords:
                # A valid definition that is not supported yet
                # (e.g. "exception E { ... };"). Skip it, including its
                # "{ ... }" body, so that the closing brace of the body is not
                # mistaken for the end of this module (issue #39).
                words = self._skip_definition(token, token_buf, ln, fn)
                _warn('%s: unsupported definition "%s" is skipped.'
                      % (_where(ln, fn), ' '.join(words)),
                      UnsupportedIDLSyntaxWarning)

            else:
                # An unknown word, e.g. a misspelled keyword ("strcut S { ... };").
                # It was dropped silently, then skipped with an
                # UnknownIDLSyntaxWarning (issue #76); it is an error now (issue #94).
                words = self._skip_definition(token, token_buf, ln, fn)
                raise InvalidIDLSyntaxError(
                    ln, fn, 'Unknown word "%s" in %s ("%s")'
                    % (token,
                       'the global scope' if self.is_global else 'module ' + self.full_path,
                       ' '.join(words)))

        return True

    def _parse_valuetype(self, keyword, token_buf, annotations, modifiers, filepath):
        """Parse a valuetype or an eventtype after its keyword (issue #99)."""
        ln, fn, name_ = token_buf.pop()
        if name_ is None or name_ in (';', '{', '}', ':'):
            raise InvalidIDLSyntaxError(ln, fn, 'No name after "%s"' % keyword)
        node.check_identifier(name_, keyword, ln, fn)
        cls = valuetype.IDLValueType if keyword == 'valuetype' else valuetype.IDLEventType
        v = cls(name_, self)
        v._add_annotations(annotations)
        v._abstract = 'abstract' in modifiers
        v._custom = 'custom' in modifiers
        if v.is_abstract and v.is_custom:
            raise InvalidIDLSyntaxError(ln, fn, '%s "%s" can not be both abstract and custom' % (keyword, name_))
        v.parse_tokens(token_buf, filepath=filepath)

        defined = self._valuetypes if keyword == 'valuetype' else self._eventtypes
        if v.is_forward:
            forward = self._forward_valuetypes if keyword == 'valuetype' else self._forward_eventtypes
            if node.unescape(name_) not in forward:
                forward.append(node.unescape(name_))
            self._definitions.append(v)
        elif any(d.name == node.unescape(name_) for d in defined):
            if self._verbose: sys.stdout.write('# Error. Same %s Defined (%s)\n' % (keyword, name_))
        else:
            defined.append(v)
            self._definitions.append(v)

    def _parse_repository_id_declaration(self, keyword, token_buf, ln, fn):
        """Read ``typeid N "ID";`` or ``typeprefix N "P";`` after its keyword (issue #135)."""
        tokens = []
        while True:
            t = token_buf.peek()[2]
            if t is None or t in ('}', '{'):
                raise InvalidIDLSyntaxError(ln, fn, 'No ";" after "%s %s"' % (keyword, ' '.join(tokens)))
            token_buf.pop()
            if t == ';':
                break
            tokens.append(t)
        repository_id.parse_declaration(keyword, tokens, self, ln, fn)

    def _parse_annotation(self, token, token_buf):
        """Consume an annotation and return it as an :class:`~idl_parser.node.IDLAnnotation`.
        '@bit_bound ( 8 )' -> @bit_bound(8)."""
        tokens = [token]
        if token_buf.peek()[2] == '(':
            depth = 0
            while True:
                ln, fn, t = token_buf.pop()
                if t is None:
                    raise InvalidIDLSyntaxError(ln, fn, 'No ")" in annotation "%s"' % token)
                tokens.append(t)
                if t == '(':
                    depth += 1
                elif t == ')':
                    depth -= 1
                    if depth == 0:
                        break
        annotations, _ = node.parse_annotations(tokens)
        return annotations[0]

    def _skip_block(self, token_buf, start_line=None, start_file=None):
        """Skip tokens up to the "}" matching an already consumed "{"."""
        depth = 1
        while depth > 0:
            ln, fn, t = token_buf.pop()
            if t is None:
                raise InvalidIDLSyntaxError(start_line, start_file,
                                            'No "}" matching "{" of an unsupported block')
            elif t == '{':
                depth += 1
            elif t == '}':
                depth -= 1

    def _skip_definition(self, token, token_buf, start_line=None, start_file=None):
        """Skip a definition whose first token ``token`` is already consumed.

        Tokens are skipped up to ";", or up to the end of a "{ ... }" block
        (and the ";" after it). A "}" that closes this module is not consumed.
        Returns the skipped words, with a block shown as "{ ... }".
        """
        words = [token]
        t = token
        while t not in (';', '{'):
            t = token_buf.peek()[2]
            if t is None or t == '}':
                return words
            token_buf.pop()
            words.append(t)
        if t == '{':
            words[-1] = '{ ... }'
            self._skip_block(token_buf, start_line, start_file)
            if token_buf.peek()[2] == ';':
                token_buf.pop()
        elif words[-1] == ';':
            words.pop()
        return words



    @property
    def modules(self):
        """Sub-modules (list of :class:`IDLModule`), in order of appearance."""
        return self._modules

    def module_by_name(self, name):
        """The sub-module named ``name`` (not scoped), or None."""
        for m in self.modules:
            if m.name == node.unescape(name):
                return m
        return None

    def for_each_module(self, func):
        """Call ``func`` with each sub-module and return the results as a list."""
        retval = []
        for m in self.modules:
            retval.append(func(m))
        return retval

    @property
    def interfaces(self):
        """Interfaces defined directly in this module (list of :class:`~idl_parser.interface.IDLInterface`)."""
        return self._interfaces

    def interface_by_name(self, name):
        """The interface named ``name`` (not scoped) in this module, or None."""
        for i in self.interfaces:
            if i.name == node.unescape(name):
                return i
        return None

    @property
    def forward_interfaces(self):
        """Names of interfaces forward-declared ("interface A;") in this module,
        in declaration order, whether or not they are defined later."""
        return list(self._forward_interfaces)

    @property
    def undefined_forward_interfaces(self):
        """Forward-declared interface names that have no definition in this module."""
        return [n for n in self._forward_interfaces if self.interface_by_name(n) is None]

    def for_each_interface(self, func):
        """Call ``func`` with each interface and return the results as a list."""
        retval = []
        for m in self.interfaces:
            retval.append(func(m))
        return retval

    @property
    def valuetypes(self):
        """Value types defined directly in this module (list of
        :class:`~idl_parser.valuetype.IDLValueType`), boxed ones included (issue #99)."""
        return self._valuetypes

    def valuetype_by_name(self, name):
        """The value type named ``name`` (not scoped) in this module, or None."""
        for v in self._valuetypes:
            if v.name == node.unescape(name):
                return v
        return None

    @property
    def forward_valuetypes(self):
        """Names of value types forward-declared ("valuetype V;") in this module,
        in declaration order, whether or not they are defined later."""
        return list(self._forward_valuetypes)

    @property
    def undefined_forward_valuetypes(self):
        """Forward-declared value type names that have no definition in this module."""
        return [n for n in self._forward_valuetypes if self.valuetype_by_name(n) is None]

    def for_each_valuetype(self, func):
        """Call ``func`` with each value type and return the results as a list."""
        return [func(v) for v in self._valuetypes]

    @property
    def eventtypes(self):
        """Event types defined directly in this module (list of
        :class:`~idl_parser.valuetype.IDLEventType`, issue #99)."""
        return self._eventtypes

    def eventtype_by_name(self, name):
        """The event type named ``name`` (not scoped) in this module, or None."""
        for v in self._eventtypes:
            if v.name == node.unescape(name):
                return v
        return None

    @property
    def forward_eventtypes(self):
        """Names of event types forward-declared ("eventtype E;") in this module,
        in declaration order, whether or not they are defined later."""
        return list(self._forward_eventtypes)

    @property
    def undefined_forward_eventtypes(self):
        """Forward-declared event type names that have no definition in this module."""
        return [n for n in self._forward_eventtypes if self.eventtype_by_name(n) is None]

    def for_each_eventtype(self, func):
        """Call ``func`` with each event type and return the results as a list."""
        return [func(v) for v in self._eventtypes]

    def find_types(self, full_typename, parent=None, scope=None):
        """Return the type definitions named ``full_typename`` (a list).

        ``scope`` is the node where the name is written (issue #72). When it
        is given, the name is resolved with the IDL scoping rules: it is
        looked up in the innermost enclosing scope first, then in the outer
        ones (``X`` in module ``B`` finds ``B::X`` before ``X`` elsewhere).
        A name starting with ``::`` is looked up from the global scope only.
        If the scoping rules find nothing, every definition whose name or
        full path is ``full_typename`` is returned, as before.
        """
        if type.is_primitive(full_typename):
            return [type.IDLType(full_typename, scope if scope is not None else self)]
        # A fully qualified name may start with '::' ("::M::A", issue #69).
        # full_path has no leading '::' ("M::A"), so drop it before comparing.
        # Escaped identifiers ("_Foo") name "Foo" (issue #140).
        name = node.unescape(str(full_typename).strip())
        absolute = name.startswith('::')
        if absolute:
            name = name.lstrip(':').strip()

        nodes = []
        for m in definition_scopes(self, scope):
            for each in (m.for_each_struct, m.for_each_typedef, m.for_each_enum,
                         m.for_each_bitmask, m.for_each_bitset, m.for_each_union,
                         m.for_each_native):
                each(nodes.append)
            if m.classname == 'IDLModule':
                m.for_each_interface(nodes.append)
                m.for_each_valuetype(nodes.append)
                m.for_each_eventtype(nodes.append)
        nodes.extend(enclosing_definitions(scope, nodes))
        found = _find_by_name(nodes, name, absolute, parent, scope)
        if not found:
            # CORBA::TypeCode and the other types an ORB knows (issue #138)
            builtin = type.builtin_corba_type(full_typename, scope)
            if builtin is not None:
                return [type.IDLPrimitive(builtin, scope if scope is not None else self)]
        return found

    def find_exceptions(self, name, scope=None):
        """Return the exceptions named ``name`` (a list), as in "raises (E)".

        The name is resolved like :meth:`find_types`. Exceptions are kept
        apart from the types because they can not be used as the type of a
        member or an argument.
        """
        name = node.unescape(str(name).strip())
        absolute = name.startswith('::')
        if absolute:
            name = name.lstrip(':').strip()
        nodes = []
        for m in definition_scopes(self, scope):
            m.for_each_exception(nodes.append)
        return _find_by_name(nodes, name, absolute, None, scope)


def definition_scopes(module, scope=None):
    """The scopes that hold definitions in ``module``: its sub-modules
    (innermost first), the module itself, and the interfaces (issue #101),
    value types and event types (issue #99) in each of them.

    ``scope`` is the node where a name is written. An interface or a value
    type enclosing it that is still being parsed (so it is not in its module
    yet) is included too, so a definition in it can use the ones before it.

    The structs, exceptions and unions that hold types declared in their
    members (issue #144) are scopes too, as is the one enclosing ``scope``.
    """
    scopes = []
    def add(s):
        scopes.append(s)
        for holder in s.structs + s.exceptions + s.unions:
            if holder.has_definitions:
                add(holder)
    def walk(m):
        for sub in m.modules:
            walk(sub)
        add(m)
        for i in m.interfaces + m.valuetypes + m.eventtypes:
            add(i)
    walk(module)
    n = scope
    while n is not None:
        if n.classname in _definition_scope_classnames + _member_scope_classnames and \
                all(n is not x for x in scopes):
            scopes.append(n)
        n = n.parent
    return scopes


def enclosing_definitions(scope, known=()):
    """The interfaces, value types and event types enclosing ``scope`` that
    are still being parsed, so they are not in their module yet (issue #133).

    In ``interface NC { exception CP { NC cxt; }; };`` the name ``NC`` in the
    exception names the interface being parsed, as if it were
    forward-declared. Nodes already in ``known`` are left out.
    """
    found = []
    n = scope
    while n is not None:
        if n.classname in _definition_scope_classnames and all(n is not x for x in known):
            found.append(n)
        n = n.parent
    return found


def _find_by_name(nodes, name, absolute, parent, scope):
    """The ``nodes`` that ``name`` names (see :meth:`IDLModule.find_types`)."""
    def with_full_path(full):
        return [s for s in nodes if s.full_path.lstrip(':') == full]

    if absolute:
        # '::X' always names X from the global scope
        return with_full_path(name)

    if scope is not None:
        for prefix in _enclosing_scopes(scope):
            found = with_full_path(prefix + sep + name if prefix else name)
            if len(found) > 0:
                return found

    if parent:
        prefix = parent.full_path.lstrip(':')
        return [s for s in nodes
                if s.full_path.lstrip(':') in ((prefix + sep + name if prefix else name), name)]
    return [s for s in nodes if s.name == name or s.full_path.lstrip(':') == name]


def _is_template_module(token_buf):
    """True if the tokens after "module" start a template module
    ("MT <typename T> {", "MT<typename T> {") or an instantiation of one
    ("MI = MT<long> ;", issue #121). Nothing is consumed."""
    name_, after = token_buf.peek()[2], token_buf.peek(1)[2]
    if name_ is None:
        return False
    if '<' in name_:
        return True
    return after is not None and (after.startswith('<') or after == '=')


def _warn(message, category):
    """warnings.warn() reported at the caller of idl_parser (e.g. the line
    calling IDLParser.load()), not at a line inside this package."""
    package_dir = os.path.dirname(os.path.abspath(__file__))
    level = 2  # 1 is this function, 2 its caller
    frame = sys._getframe(1)
    while frame is not None and os.path.dirname(os.path.abspath(frame.f_code.co_filename)) == package_dir:
        frame = frame.f_back
        level += 1
    warnings.warn(message, category, stacklevel=level)


def _where(line_number, file_name):
    """'File "a.idl", line 3' for warnings (like IDLParserException.message)."""
    text = 'File "%s"' % (file_name if file_name else '<string>')
    if line_number is not None and line_number >= 0:
        text += ', line %s' % line_number
    return text


_definition_scope_classnames = ('IDLInterface', 'IDLValueType', 'IDLEventType')
# Scopes that hold the types declared in their members (issue #144)
_member_scope_classnames = ('IDLStruct', 'IDLException', 'IDLUnion')
_scope_classnames = ('IDLModule',) + _member_scope_classnames + _definition_scope_classnames

def _enclosing_scopes(node):
    """Full paths (without a leading '::') of the scopes enclosing ``node``,
    innermost first and ending with the global scope ('')."""
    scopes = []
    n = node
    while n is not None:
        if n.classname in _scope_classnames:
            path = n.full_path.lstrip(':')
            if path not in scopes:
                scopes.append(path)
        n = n.parent
    if '' not in scopes:
        scopes.append('')
    return scopes
