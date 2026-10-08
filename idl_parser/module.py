"""IDL modules, including the global scope.

:class:`IDLModule` is also the node returned by
:meth:`idl_parser.parser.IDLParser.load`: the global scope is a module
without a name (internally ``'__global__'``).
"""
import os, sys, traceback

from . import node, type
from . import struct, typedef, interface, enum, const, union, bitmask, bitset
from .exception import InvalidIDLSyntaxError
global_namespace = '__global__'
sep = '::'

class IDLModule(node.IDLNode):
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
        self._typedefs = []
        self._structs = []
        self._forward_structs = []
        self._enums = []
        self._bitmasks = []
        self._bitsets = []
        self._unions = []
        self._forward_unions = []
        self._consts = []
        self._modules = []

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
               [i.to_simple_dic(quiet) for i in self.interfaces] +
               [m.to_simple_dic(quiet) for m in self.modules] +
               [e.to_simple_dic(quiet) for e in self.enums] +
               [b.to_simple_dic(quiet) for b in self.bitmasks] +
               [b.to_simple_dic(quiet) for b in self.bitsets] +
               [u.to_simple_dic(quiet) for u in self.unions] +
               [t.to_simple_dic(quiet) for t in self.typedefs] +
               [t.to_simple_dic(quiet) for t in self.consts]}
        return dic

    def to_dic(self):
        """All the contents as plain dicts and lists (for JSON or YAML output)."""
        dic = { 'name' : self.name,
                'filepath' : self.filepath,
                'classname' : self.classname,
                'interfaces' : [i.to_dic() for i in self.interfaces],
                'typedefs' : [t.to_dic() for t in self.typedefs],
                'structs' : [s.to_dic() for s in self.structs],
                'enums' : [e.to_dic() for e in self.enums],
                'bitmasks' : [b.to_dic() for b in self.bitmasks],
                'bitsets' : [b.to_dic() for b in self.bitsets],
                'unions' : [u.to_dic() for u in self.unions],
                'modules' : [m.to_dic() for m in self.modules],
                'consts' : [c.to_dic() for c in self.consts] }
        return self._with_annotations(dic)


    def parse_tokens(self, token_buf, filepath=None):
        """Parse definitions from ``token_buf`` into this module.

        For a named module, the tokens start at ``{`` and are read up to the
        matching ``}``; for the global scope, up to the end of the input.

        :param token_buf: :class:`~idl_parser.token_buffer.TokenBuffer` to read from.
        :param filepath: File name recorded in the parsed nodes.
        :raises ~idl_parser.exception.InvalidIDLSyntaxError: The input is not valid IDL.
        """
        self._filepath = filepath
        if not self.name == global_namespace:
            ln, fn, kakko = token_buf.pop()
            if not kakko == '{':
                if self._verbose: sys.stdout.write('# Error. No kakko "{".\n')
                raise InvalidIDLSyntaxError()

        annotations = []
        while True:
            ln, fn, token = token_buf.pop()
            if token is not None and token.startswith('@'):
                # Annotations apply to the next definition (issue #39).
                annotations.append(self._parse_annotation(token, token_buf))
                continue
            pending_annotations, annotations = annotations, []

            if token == None:
                if self.name == global_namespace:
                    break
                if self._verbose: sys.stdout.write('# Error. No kokka "}".\n')
                raise InvalidIDLSyntaxError()
            elif token == 'module':
                ln, fn, name_ = token_buf.pop()
                m = self.module_by_name(name_)
                if m == None:
                    m = IDLModule(name_, self)
                    self._modules.append(m)
                m._add_annotations(pending_annotations)
                m.parse_tokens(token_buf, filepath=filepath)
            elif token == 'typedef':
                blocks = []
                while True:
                    ln, fn, t = token_buf.pop()
                    if t == None:
                        raise InvalidIDLSyntaxError()
                    elif t == ';':
                        break
                    else:
                        blocks.append(t)
                t = typedef.IDLTypedef(self)
                anns, blocks = node.parse_annotations(blocks)
                t._add_annotations(pending_annotations + anns)
                t.parse_blocks(blocks, filepath=filepath)
                t_ = self.typedef_by_name(t.name)
                if t_:
                    if self._verbose: sys.stdout.write('# Error. Same Typedef Defined (%s)\n' % t.name)
                else:
                    self._typedefs.append(t)

            elif token == 'struct':
                ln, fn, name_ = token_buf.pop()
                s_ = self.struct_by_name(name_)
                s = struct.IDLStruct(name_, self)
                s._add_annotations(pending_annotations)
                s.parse_tokens(token_buf, filepath=filepath)
                if s.is_forward:
                    # Forward declaration ("struct A;"): remember the name only.
                    # The definition, if any, is added to structs when it appears.
                    if name_ not in self._forward_structs:
                        self._forward_structs.append(name_)
                    continue
                if s_:
                    if self._verbose: sys.stdout.write('# Error. Same Struct Defined (%s)\n' % name_)
                #    raise InvalidIDLSyntaxError
                else:
                    self._structs.append(s)

            elif token == 'interface':
                ln, fn, name_ = token_buf.pop()
                s = interface.IDLInterface(name_, self)
                s._add_annotations(pending_annotations)
                s.parse_tokens(token_buf, filepath=filepath)

                if s.is_forward:
                    # Forward declaration ("interface A;"): remember the name only.
                    # The definition, if any, is added to interfaces when it appears.
                    if name_ not in self._forward_interfaces:
                        self._forward_interfaces.append(name_)
                    continue

                s_ = self.interface_by_name(name_)
                if s_:
                    if self._verbose: sys.stdout.write('# Error. Same Interface Defined (%s)\n' % name_)
                #    raise InvalidIDLSyntaxError
                else:
                    self._interfaces.append(s)

            elif token == 'enum':
                ln, fn, name_ = token_buf.pop()
                s = enum.IDLEnum(name_, self)
                s._add_annotations(pending_annotations)
                s.parse_tokens(token_buf, filepath)
                s_ = self.enum_by_name(name_)
                if s_:
                    if self._verbose: sys.stdout.write('# Error. Same Enum Defined (%s)\n' % name_)
                #    raise InvalidIDLSyntaxError
                else:
                    self._enums.append(s)

            elif token == 'bitmask':
                ln, fn, name_ = token_buf.pop()
                s = bitmask.IDLBitmask(name_, self, pending_annotations)
                s.parse_tokens(token_buf, filepath)
                if self.bitmask_by_name(name_):
                    if self._verbose: sys.stdout.write('# Error. Same Bitmask Defined (%s)\n' % name_)
                else:
                    self._bitmasks.append(s)

            elif token == 'bitset':
                ln, fn, name_ = token_buf.pop()
                s = bitset.IDLBitset(name_, self)
                s._add_annotations(pending_annotations)
                s.parse_tokens(token_buf, filepath)
                if self.bitset_by_name(name_):
                    if self._verbose: sys.stdout.write('# Error. Same Bitset Defined (%s)\n' % name_)
                else:
                    self._bitsets.append(s)

            elif token == 'union':
                ln, fn, name_ = token_buf.pop()
                s = union.IDLUnion(name_, self)
                s._add_annotations(pending_annotations)
                s.parse_tokens(token_buf, filepath)
                if s.is_forward:
                    # Forward declaration ("union A;"): remember the name only.
                    if name_ not in self._forward_unions:
                        self._forward_unions.append(name_)
                    continue
                s_ = self.union_by_name(name_)
                if s_:
                    if self._verbose: sys.stdout.write('# Error. Same Union Defined (%s)\n' % name_)
                #    raise InvalidIDLSyntaxError
                else:
                    self._unions.append(s)

            elif token == 'const':
                values = []
                while True:
                    ln, fn, t = token_buf.pop()
                    if t is None:
                        if self._verbose: sys.stdout.write('# Error. No ";" after const.\n')
                        raise InvalidIDLSyntaxError(message='No ";" after const definition')
                    if t == ';':
                        break
                    values.append(t)

                # Split at '=': "<type> <name> = <value>" (issue #52).
                # The value is every token after '=', so that an
                # expression such as "1 + 2" is kept whole.
                if '=' not in values:
                    raise InvalidIDLSyntaxError(ln, fn, 'No "=" in const definition "%s"' % ' '.join(values))
                eq = values.index('=')
                if eq < 2:
                    raise InvalidIDLSyntaxError(ln, fn, 'No type or name in const definition "%s"' % ' '.join(values))
                if eq == len(values) - 1:
                    raise InvalidIDLSyntaxError(ln, fn, 'No value in const definition "%s"' % ' '.join(values))
                value_ = ' '.join(values[eq+1:])
                name_ = values[eq-1]
                typename = ' '.join(values[:eq-1])
                s = const.IDLConst(name_, typename, value_, self, filepath=filepath)
                s._add_annotations(pending_annotations)
                s_ = self.const_by_name(name_)
                if s_:
                    if self._verbose: sys.stdout.write('# Error. Same Const Defined (%s)\n' % name_)
                else:
                    self._consts.append(s)

            elif token == '{':
                # A block opened by an unsupported construct
                # (e.g. "bitmask F { ... }", "bitset B { ... }", "exception E { ... }").
                # Skip it up to the matching "}" so that its closing brace is not
                # mistaken for the end of this module (issue #39).
                self._skip_block(token_buf, ln, fn)

            elif token == '}':
                break

        return True

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
        if self._verbose:
            sys.stdout.write('# Warning. Skipped unsupported block at line %s.\n' % start_line)



    @property
    def modules(self):
        """Sub-modules (list of :class:`IDLModule`), in order of appearance."""
        return self._modules

    def module_by_name(self, name):
        """The sub-module named ``name`` (not scoped), or None."""
        for m in self.modules:
            if m.name == name:
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
            if i.name == name:
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
    def structs(self):
        """Structs defined directly in this module (list of :class:`~idl_parser.struct.IDLStruct`)."""
        return self._structs

    def struct_by_name(self, name):
        """The struct named ``name`` (not scoped) in this module, or None."""
        for s in self.structs:
            if s.name == name:
                return s
        return None

    @property
    def forward_structs(self):
        """Names of structs forward-declared ("struct A;") in this module,
        in declaration order, whether or not they are defined later."""
        return list(self._forward_structs)

    @property
    def undefined_forward_structs(self):
        """Forward-declared struct names that have no definition in this module."""
        return [n for n in self._forward_structs if self.struct_by_name(n) is None]

    def for_each_struct(self, func, filter=None):
        """Call ``func`` with each struct and return the results as a list.

        :param filter: If given, only the structs for which ``filter(struct)`` is
            true are passed to ``func``.
        """
        retval = []
        for m in self.structs:
            if filter:
                if filter(m):
                    retval.append(func(m))
                pass
            else:
                retval.append(func(m))
        return retval

    @property
    def enums(self):
        """Enums defined directly in this module (list of :class:`~idl_parser.enum.IDLEnum`)."""
        return self._enums

    def enum_by_name(self, name):
        """The enum named ``name`` (not scoped) in this module, or None."""
        for e in self.enums:
            if e.name == name:
                return e
        return None

    def for_each_enum(self, func):
        """Call ``func`` with each enum and return the results as a list."""
        retval = []
        for m in self.enums:
            retval.append(func(m))
        return retval

    @property
    def bitmasks(self):
        """Bitmasks defined directly in this module (list of :class:`~idl_parser.bitmask.IDLBitmask`)."""
        return self._bitmasks

    def bitmask_by_name(self, name):
        """The bitmask named ``name`` (not scoped) in this module, or None."""
        for b in self.bitmasks:
            if b.name == name:
                return b
        return None

    def for_each_bitmask(self, func):
        """Call ``func`` with each bitmask and return the results as a list."""
        return [func(b) for b in self.bitmasks]

    @property
    def bitsets(self):
        """Bitsets defined directly in this module (list of :class:`~idl_parser.bitset.IDLBitset`)."""
        return self._bitsets

    def bitset_by_name(self, name):
        """The bitset named ``name`` (not scoped) in this module, or None."""
        for b in self.bitsets:
            if b.name == name:
                return b
        return None

    def for_each_bitset(self, func):
        """Call ``func`` with each bitset and return the results as a list."""
        return [func(b) for b in self.bitsets]

    @property
    def unions(self):
        """Unions defined directly in this module (list of :class:`~idl_parser.union.IDLUnion`)."""
        return self._unions

    def union_by_name(self, name):
        """The union named ``name`` (not scoped) in this module, or None."""
        for u in self.unions:
            if u.name == name:
                return u
        return None

    @property
    def forward_unions(self):
        """Names of unions forward-declared ("union A;") in this module,
        in declaration order, whether or not they are defined later."""
        return list(self._forward_unions)

    @property
    def undefined_forward_unions(self):
        """Forward-declared union names that have no definition in this module."""
        return [n for n in self._forward_unions if self.union_by_name(n) is None]

    def for_each_union(self, func):
        """Call ``func`` with each union and return the results as a list."""
        retval = []
        for m in self.unions:
            retval.append(func(m))
        return retval

    @property
    def consts(self):
        """Constants defined directly in this module (list of :class:`~idl_parser.const.IDLConst`)."""
        return self._consts

    def const_by_name(self, name):
        """The constant named ``name`` (not scoped) in this module, or None."""
        for c in self.consts:
            if c.name == name:
                return c
        return None

    def for_each_const(self, func):
        """Call ``func`` with each constant and return the results as a list."""
        retval = []
        for m in self.consts:
            retval.append(func(m))
        return retval


    @property
    def typedefs(self):
        """Typedefs defined directly in this module (list of :class:`~idl_parser.typedef.IDLTypedef`)."""
        return self._typedefs

    def typedef_by_name(self, name):
        """The typedef named ``name`` (not scoped) in this module, or None."""
        for t in self.typedefs:
            if t.name == name:
                return t
        return None

    def for_each_typedef(self, func):
        """Call ``func`` with each typedef.

        Unlike the other ``for_each_*`` methods, it returns None.
        """
        retval = []
        for m in self.typedefs:
            retval.append(func(m))

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
            return [type.IDLType(full_typename, self)]
        # A fully qualified name may start with '::' ("::M::A", issue #69).
        # full_path has no leading '::' ("M::A"), so drop it before comparing.
        name = str(full_typename).strip()
        absolute = name.startswith('::')
        if absolute:
            name = name.lstrip(':').strip()

        nodes = []
        def parse_module(m):
            m.for_each_module(parse_module)
            for each in (m.for_each_struct, m.for_each_typedef, m.for_each_enum,
                         m.for_each_bitmask, m.for_each_bitset, m.for_each_union,
                         m.for_each_interface):
                each(nodes.append)
        parse_module(self)

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


_scope_classnames = ('IDLModule', 'IDLStruct', 'IDLUnion', 'IDLInterface')

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
