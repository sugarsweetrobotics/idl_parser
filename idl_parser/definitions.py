"""Type and constant definitions shared by modules and interfaces.

A ``module`` and an ``interface`` can both hold ``struct``, ``union``,
``enum``, ``typedef``, ``const``, ``exception``, ``native``, ``bitmask`` and
``bitset`` definitions (issue #101). :class:`IDLDefinitionScope` keeps them
and parses them for both.
"""
import os
import sys

from . import node
from .exception import InvalidIDLSyntaxError

# Keywords of the types that can be declared inside a typedef
# ("typedef struct S { ... } SS;", issue #121).
constr_type_keywords = ('struct', 'union', 'enum', 'bitmask', 'bitset')

# Keywords of the types that can be declared in a member of a struct or a
# union ("struct S { struct T { long a; } t; };", issue #144).
member_type_keywords = ('struct', 'union', 'enum')

# Keywords that start a definition handled by IDLDefinitionScope.parse_definition().
definition_keywords = ('typedef', 'struct', 'exception', 'enum', 'bitmask',
                       'bitset', 'union', 'native', 'const')


class IDLDefinitionScope(object):
    """Mixin for a scope that holds type and constant definitions.

    Used by :class:`~idl_parser.module.IDLModule` and
    :class:`~idl_parser.interface.IDLInterface`, and by
    :class:`~idl_parser.struct.IDLStruct` and :class:`~idl_parser.union.IDLUnion`
    for the types declared in their members (issue #144).
    """

    def _init_definitions(self):
        self._typedefs = []
        self._structs = []
        self._forward_structs = []
        self._exceptions = []
        self._enums = []
        self._bitmasks = []
        self._bitsets = []
        self._unions = []
        self._forward_unions = []
        self._consts = []
        self._natives = []
        # Every definition in the order it is written (issue #134)
        self._definitions = []
        # Names declared in this scope (issue #143): lower-case name ->
        # list of (name, kind, forward, location)
        self._declared = {}

    def _scope_description(self):
        """``'module "M"'``, ``'interface "M::I"'`` or ``'the global scope'`` for messages."""
        if self.parent is None:
            return 'the global scope'
        return '%s "%s"' % (getattr(self, '_kind', None) or self.classname[3:].lower(),
                            self.full_path.lstrip(':'))

    def _declare(self, name, kind, location=None, forward=False, reread=True):
        """Declare ``name`` in this scope; return True if the definition is
        new and is to be kept (issue #143).

        IDL allows a name once in a scope, also across kinds, and two names
        that differ only in case collide. A module may be opened again, and
        a forward declaration may come before or after the definition of
        the same kind. A definition read again from the same place
        ``location`` (``(line, file, index of the token in the line)``,
        from :meth:`~idl_parser.token_buffer.TokenBuffer.position`; a file
        included by several files parsed one after the other) is skipped:
        False is returned. With
        ``reread=False`` (the members of an interface) ``location`` is used
        for the message only.

        :raises ~idl_parser.exception.InvalidIDLSyntaxError: The name is
            already declared in this scope, or differs only in case from a
            name declared in it.
        """
        name = node.unescape(name)  # "_long" declares "long" (issue #140)
        ln, fn = location[:2] if location is not None else (None, None)
        if fn:
            # The same file may be reached by a relative and an absolute path
            location = (ln, os.path.abspath(fn)) + tuple(location[2:])
        entries = self._declared.setdefault(name.lower(), [])
        for n, k, fwd, loc in entries:
            if reread and location is not None and loc == location and k == kind and fwd == forward:
                return False  # the same definition, read again
        for n, k, fwd, loc in entries:
            if n != name:
                raise InvalidIDLSyntaxError(
                    ln, fn, '"%s" differs only in case from "%s" in %s'
                    % (name, n, self._scope_description()))
            if k == kind and (k == 'module' or fwd or forward):
                continue
            raise InvalidIDLSyntaxError(
                ln, fn, '"%s" is already defined in %s' % (name, self._scope_description()))
        entries.append((name, kind, forward, location))
        return True

    def parse_definition(self, token, token_buf, filepath=None, annotations=()):
        """Parse a definition whose keyword ``token`` is already consumed.

        :param token: The keyword (one of :data:`definition_keywords`).
        :param token_buf: :class:`~idl_parser.token_buffer.TokenBuffer` to read from.
        :param filepath: File name recorded in the parsed nodes.
        :param annotations: Annotations written before the keyword.
        :return: False if ``token`` does not start a definition (nothing is read).
        :raises ~idl_parser.exception.InvalidIDLSyntaxError: The definition is
            not valid IDL.
        """
        pending_annotations = list(annotations)
        if token == 'typedef':
            if token_buf.peek()[2] in constr_type_keywords:
                # "typedef enum E { A, B } EE;" (issue #121)
                type_name = self._parse_typedef_constr_type(token_buf, filepath)
                blocks = [type_name]
            else:
                blocks = []
            while True:
                ln, fn, t = token_buf.pop()
                if t == None:
                    raise InvalidIDLSyntaxError()
                elif t == ';':
                    break
                else:
                    blocks.append(t)
            pos = token_buf.position()  # of the ";"
            anns, blocks = node.parse_annotations(blocks)
            # "typedef long A, B[3];" defines one typedef per name (issue #117)
            typename, declarators = node.split_declarators(blocks, 'typedef')
            for d in declarators:
                t = typedef.IDLTypedef(self)
                t._add_annotations(pending_annotations + anns)
                t.parse_blocks(typename + [d], filepath=filepath)
                if self._declare(t.name, 'typedef', pos):
                    self._typedefs.append(t)
                    self._definitions.append(t)

        elif token == 'struct':
            ln, fn, name_ = token_buf.pop()
            pos = token_buf.position()
            node.check_identifier(name_, 'struct', ln, fn)
            s = struct.IDLStruct(name_, self)
            s._add_annotations(pending_annotations)
            s.parse_tokens(token_buf, filepath=filepath)
            if not self._declare(name_, 'struct', pos, s.is_forward):
                pass  # read again (issue #143)
            elif s.is_forward:
                # Forward declaration ("struct A;"): remember the name only.
                # The definition, if any, is added to structs when it appears.
                if node.unescape(name_) not in self._forward_structs:
                    self._forward_structs.append(node.unescape(name_))
                self._definitions.append(s)
            else:
                self._structs.append(s)
                self._definitions.append(s)

        elif token == 'exception':
            ln, fn, name_ = token_buf.pop()
            pos = token_buf.position()
            node.check_identifier(name_, 'exception', ln, fn)
            s = struct.IDLException(name_, self)
            s._add_annotations(pending_annotations)
            s.parse_tokens(token_buf, filepath=filepath)
            if self._declare(name_, 'exception', pos):
                self._exceptions.append(s)
                self._definitions.append(s)

        elif token == 'enum':
            ln, fn, name_ = token_buf.pop()
            pos = token_buf.position()
            node.check_identifier(name_, 'enum', ln, fn)
            s = enum.IDLEnum(name_, self)
            s._add_annotations(pending_annotations)
            s.parse_tokens(token_buf, filepath)
            if self._declare(name_, 'enum', pos):
                # The enumerators belong to this scope (issue #143)
                for v in s.values:
                    self._declare(v.name, 'enumerator', pos)
                self._enums.append(s)
                self._definitions.append(s)

        elif token == 'bitmask':
            ln, fn, name_ = token_buf.pop()
            pos = token_buf.position()
            node.check_identifier(name_, 'bitmask', ln, fn)
            s = bitmask.IDLBitmask(name_, self, pending_annotations)
            s.parse_tokens(token_buf, filepath)
            if self._declare(name_, 'bitmask', pos):
                self._bitmasks.append(s)
                self._definitions.append(s)

        elif token == 'bitset':
            ln, fn, name_ = token_buf.pop()
            pos = token_buf.position()
            node.check_identifier(name_, 'bitset', ln, fn)
            s = bitset.IDLBitset(name_, self)
            s._add_annotations(pending_annotations)
            s.parse_tokens(token_buf, filepath)
            if self._declare(name_, 'bitset', pos):
                self._bitsets.append(s)
                self._definitions.append(s)

        elif token == 'union':
            ln, fn, name_ = token_buf.pop()
            pos = token_buf.position()
            node.check_identifier(name_, 'union', ln, fn)
            s = union.IDLUnion(name_, self)
            s._add_annotations(pending_annotations)
            s.parse_tokens(token_buf, filepath)
            if not self._declare(name_, 'union', pos, s.is_forward):
                pass  # read again (issue #143)
            elif s.is_forward:
                # Forward declaration ("union A;"): remember the name only.
                if node.unescape(name_) not in self._forward_unions:
                    self._forward_unions.append(node.unescape(name_))
                self._definitions.append(s)
            else:
                self._unions.append(s)
                self._definitions.append(s)

        elif token == 'native':
            # "native N;": a type with a name only (issue #93).
            ln, fn, name_ = token_buf.pop()
            pos = token_buf.position()
            node.check_identifier(name_, 'native', ln, fn)
            if name_ is None or name_ in (';', '{', '}'):
                raise InvalidIDLSyntaxError(ln, fn, 'No name after "native"')
            ln2, fn2, t = token_buf.pop()
            if t != ';':
                raise InvalidIDLSyntaxError(ln, fn, 'No ";" after "native %s"' % name_)
            n = native.IDLNative(name_, self, filepath=filepath)
            n._add_annotations(pending_annotations)
            if self._declare(name_, 'native', pos):
                self._natives.append(n)
                self._definitions.append(n)

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
            pos = token_buf.position()  # of the ";"

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
            node.check_identifier(name_, 'const', ln, fn)
            typename = ' '.join(values[:eq-1])
            s = const.IDLConst(name_, typename, value_, self, filepath=filepath)
            s._add_annotations(pending_annotations)
            s._evaluate(ln, fn)
            if self._declare(name_, 'const', pos):
                self._consts.append(s)
                self._definitions.append(s)

        else:
            return False
        return True

    def _parse_typedef_constr_type(self, token_buf, filepath):
        """Parse the struct, union, enum, bitmask or bitset declared in a
        typedef (``typedef enum E { A, B } EE;``, issue #121).

        The declared type is added to this scope as if it were written
        before the typedef. The tokens after it, up to the ``;``, are left
        in ``token_buf`` for the typedef. Returns the name of the type.
        """
        ln, fn, keyword = token_buf.pop()
        ln_, fn_, name_ = token_buf.peek()
        if name_ is None or name_ in (';', '{', '}', ','):
            raise InvalidIDLSyntaxError(ln, fn, 'No name after "typedef %s"' % keyword)
        # The tokens of the definition: its name, a base (": B") or a
        # discriminator ("switch (long)") if any, the "{ ... }" body, and a
        # ";" closing it, as the parsers of the definitions expect.
        tokens = [token_buf.pop()]
        if token_buf.peek()[2] in (':', 'switch'):
            while token_buf.peek()[2] not in ('{', ';', None):
                tokens.append(token_buf.pop())
            if token_buf.peek()[2] != '{':
                raise InvalidIDLSyntaxError(ln, fn, 'No "{" after "typedef %s %s"' % (keyword, name_))
        if token_buf.peek()[2] == '{':
            depth = 0
            while True:
                t = token_buf.pop()
                if t[2] is None:
                    raise InvalidIDLSyntaxError(ln, fn, 'No "}" closing "typedef %s %s"' % (keyword, name_))
                tokens.append(t)
                if t[2] == '{':
                    depth += 1
                elif t[2] == '}':
                    depth -= 1
                    if depth == 0:
                        break
        elif keyword not in ('struct', 'union'):
            raise InvalidIDLSyntaxError(ln, fn, 'No "{" after "typedef %s %s"' % (keyword, name_))
        # else: a forward declaration ("typedef struct S SS;")
        tokens.append((tokens[-1][0], tokens[-1][1], ';'))
        self.parse_definition(keyword, token_buf.from_tokens(tokens), filepath)
        return name_

    def _starts_member_type(self, token_buf):
        """True if ``token_buf`` starts with a struct, union or enum
        definition written in a member (``struct T { ... } t;``, issue #144).
        Nothing is consumed."""
        return token_buf.peek()[2] in member_type_keywords and \
            token_buf.peek(2)[2] in ('{', ':', 'switch')

    @property
    def has_definitions(self):
        """True if any type or constant is defined in this scope."""
        return any((self._typedefs, self._structs, self._exceptions, self._enums,
                    self._bitmasks, self._bitsets, self._unions, self._consts,
                    self._natives))

    @property
    def definitions(self):
        """Every definition in this scope in the order it is written (issue #134).

        Unlike the lists by kind (:attr:`structs`, :attr:`typedefs`, ...),
        the kinds are mixed: ``const long A = 1; struct S { ... }; typedef S T;``
        gives ``[A, S, T]``. Forward declarations are included as the nodes
        they make (``is_forward`` is True), one for each declaration. A
        definition that repeats one already in the scope is left out, as in
        the lists by kind.

        In a module, sub-modules, interfaces, value types and event types
        are included too; a module opened more than once
        (``module M { ... }; module M { ... };``) is listed where it is
        first opened, and its own ``definitions`` are those of every
        opening in order. In an interface or a value type, the operations,
        attributes, state members and factories are included too.
        """
        return list(self._definitions)

    @property
    def structs(self):
        """Structs defined directly in this scope (list of :class:`~idl_parser.struct.IDLStruct`)."""
        return self._structs

    def struct_by_name(self, name):
        """The struct named ``name`` (not scoped) in this scope, or None."""
        for s in self.structs:
            if s.name == node.unescape(name):
                return s
        return None

    @property
    def forward_structs(self):
        """Names of structs forward-declared ("struct A;") in this scope,
        in declaration order, whether or not they are defined later."""
        return list(self._forward_structs)

    @property
    def undefined_forward_structs(self):
        """Forward-declared struct names that have no definition in this scope."""
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
    def exceptions(self):
        """Exceptions defined directly in this scope (list of :class:`~idl_parser.struct.IDLException`)."""
        return self._exceptions

    def exception_by_name(self, name):
        """The exception named ``name`` (not scoped) in this scope, or None."""
        for x in self.exceptions:
            if x.name == node.unescape(name):
                return x
        return None

    def for_each_exception(self, func):
        """Call ``func`` with each exception and return the results as a list."""
        return [func(x) for x in self.exceptions]

    @property
    def enums(self):
        """Enums defined directly in this scope (list of :class:`~idl_parser.enum.IDLEnum`)."""
        return self._enums

    def enum_by_name(self, name):
        """The enum named ``name`` (not scoped) in this scope, or None."""
        for e in self.enums:
            if e.name == node.unescape(name):
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
        """Bitmasks defined directly in this scope (list of :class:`~idl_parser.bitmask.IDLBitmask`)."""
        return self._bitmasks

    def bitmask_by_name(self, name):
        """The bitmask named ``name`` (not scoped) in this scope, or None."""
        for b in self.bitmasks:
            if b.name == node.unescape(name):
                return b
        return None

    def for_each_bitmask(self, func):
        """Call ``func`` with each bitmask and return the results as a list."""
        return [func(b) for b in self.bitmasks]

    @property
    def bitsets(self):
        """Bitsets defined directly in this scope (list of :class:`~idl_parser.bitset.IDLBitset`)."""
        return self._bitsets

    def bitset_by_name(self, name):
        """The bitset named ``name`` (not scoped) in this scope, or None."""
        for b in self.bitsets:
            if b.name == node.unescape(name):
                return b
        return None

    def for_each_bitset(self, func):
        """Call ``func`` with each bitset and return the results as a list."""
        return [func(b) for b in self.bitsets]

    @property
    def unions(self):
        """Unions defined directly in this scope (list of :class:`~idl_parser.union.IDLUnion`)."""
        return self._unions

    def union_by_name(self, name):
        """The union named ``name`` (not scoped) in this scope, or None."""
        for u in self.unions:
            if u.name == node.unescape(name):
                return u
        return None

    @property
    def forward_unions(self):
        """Names of unions forward-declared ("union A;") in this scope,
        in declaration order, whether or not they are defined later."""
        return list(self._forward_unions)

    @property
    def undefined_forward_unions(self):
        """Forward-declared union names that have no definition in this scope."""
        return [n for n in self._forward_unions if self.union_by_name(n) is None]

    def for_each_union(self, func):
        """Call ``func`` with each union and return the results as a list."""
        retval = []
        for m in self.unions:
            retval.append(func(m))
        return retval

    @property
    def consts(self):
        """Constants defined directly in this scope (list of :class:`~idl_parser.const.IDLConst`)."""
        return self._consts

    def const_by_name(self, name):
        """The constant named ``name`` (not scoped) in this scope, or None."""
        for c in self.consts:
            if c.name == node.unescape(name):
                return c
        return None

    def for_each_const(self, func):
        """Call ``func`` with each constant and return the results as a list."""
        retval = []
        for m in self.consts:
            retval.append(func(m))
        return retval

    @property
    def natives(self):
        """Native types declared directly in this scope (list of :class:`~idl_parser.native.IDLNative`)."""
        return self._natives

    def native_by_name(self, name):
        """The native type named ``name`` (not scoped) in this scope, or None."""
        for n in self.natives:
            if n.name == node.unescape(name):
                return n
        return None

    def for_each_native(self, func):
        """Call ``func`` with each native type and return the results as a list."""
        return [func(n) for n in self.natives]

    @property
    def typedefs(self):
        """Typedefs defined directly in this scope (list of :class:`~idl_parser.typedef.IDLTypedef`)."""
        return self._typedefs

    def typedef_by_name(self, name):
        """The typedef named ``name`` (not scoped) in this scope, or None."""
        for t in self.typedefs:
            if t.name == node.unescape(name):
                return t
        return None

    def for_each_typedef(self, func):
        """Call ``func`` with each typedef.

        Unlike the other ``for_each_*`` methods, it returns None.
        """
        retval = []
        for m in self.typedefs:
            retval.append(func(m))

    def _definitions_simple_dic(self, quiet=False):
        """``to_simple_dic()`` of the definitions in this scope, grouped by kind."""
        return ([s.to_simple_dic(quiet) for s in self.structs] +
                [x.to_simple_dic(quiet) for x in self.exceptions] +
                [e.to_simple_dic(quiet) for e in self.enums] +
                [b.to_simple_dic(quiet) for b in self.bitmasks] +
                [b.to_simple_dic(quiet) for b in self.bitsets] +
                [u.to_simple_dic(quiet) for u in self.unions] +
                [t.to_simple_dic(quiet) for t in self.typedefs] +
                [n.to_simple_dic(quiet) for n in self.natives] +
                [c.to_simple_dic(quiet) for c in self.consts])

    def _definitions_dic(self):
        """``to_dic()`` of the definitions in this scope, keyed by kind."""
        return { 'typedefs' : [t.to_dic() for t in self.typedefs],
                 'natives' : [n.to_dic() for n in self.natives],
                 'structs' : [s.to_dic() for s in self.structs],
                 'exceptions' : [x.to_dic() for x in self.exceptions],
                 'enums' : [e.to_dic() for e in self.enums],
                 'bitmasks' : [b.to_dic() for b in self.bitmasks],
                 'bitsets' : [b.to_dic() for b in self.bitsets],
                 'unions' : [u.to_dic() for u in self.unions],
                 'consts' : [c.to_dic() for c in self.consts] }


# Imported here, after IDLDefinitionScope, because IDLStruct and IDLUnion
# use it too (issue #144)
from . import struct, typedef, enum, const, union, bitmask, bitset, native
