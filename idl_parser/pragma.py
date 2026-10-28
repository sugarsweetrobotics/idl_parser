"""``#pragma`` directives found in IDL files (issues #10 / #28).

``#pragma`` lines are taken out of the input during preprocessing, so they
never reach the parser as tokens. Each one is kept as an :class:`IDLPragma`
and is available from :attr:`idl_parser.parser.IDLParser.pragmas`.

``#pragma keylist <type> [<member> ...]`` (OpenSplice DDS) is interpreted:
the named struct is looked up after the whole input has been parsed, so the
struct may be defined before or after the pragma, and its key members are
available as :attr:`idl_parser.struct.IDLStruct.keys` (combined with members
annotated with ``@key``; see there).  ``#pragma prefix``, ``#pragma ID``
and ``#pragma version`` give the repository IDs of the definitions
(:attr:`idl_parser.node.IDLNode.repository_id`, issue #135; see
:mod:`idl_parser.repository_id`). Other pragmas (``#pragma once``,
vendor-specific ones, ...) are only recorded.

Each key name of a keylist is checked against the members of the target
struct (issue #38).  A key may name a member of a nested struct with
dot-separated names (``#pragma keylist T a.b``).  Keys that cannot be found
are kept as written in :attr:`IDLStruct.keys` so that existing IDL files are
still accepted, but a :class:`KeylistWarning` is issued and they are listed
in :attr:`IDLPragma.unresolved_keys`.
"""
import re
import warnings

from . import exception

_PRAGMA_RE = re.compile(r'^#\s*pragma\b(.*)$')


class KeylistWarning(UserWarning):
    """Issued when a ``#pragma keylist`` key does not name a member of the struct."""


def match_pragma(line):
    """Return the text after ``#pragma`` if ``line`` is a pragma line, else ``None``."""
    m = _PRAGMA_RE.match(line.strip())
    if m is None:
        return None
    return m.group(1).strip()


class IDLPragma(object):
    """One ``#pragma`` directive.

    :param text: Text after ``#pragma`` (e.g. ``'keylist A id'``).
    :param scope: Names of the modules enclosing the pragma, outermost first.
    :param line_number: Line number in ``filepath``.
    :param filepath: File the pragma was written in (``None`` for :meth:`IDLParser.load`).
    """

    def __init__(self, text, scope=(), line_number=None, filepath=None):
        # The comment remover puts spaces around some characters
        # ("A::B" -> "A : : B"); restore scoped names.
        text = re.sub(r':\s*:', '::', text)
        tokens = text.split()
        self._name = tokens[0] if tokens else ''
        self._arguments = tokens[1:]
        self._scope = list(scope)
        self._line_number = line_number
        self._filepath = filepath
        self._target = None
        self._unresolved_keys = None
        # The scope node the pragma is written in (issue #135)
        self._scope_node = None

    @property
    def name(self):
        """Pragma kind, the first word after ``#pragma`` (e.g. ``'keylist'``)."""
        return self._name

    @property
    def arguments(self):
        """Words after the pragma kind, as a list of strings."""
        return list(self._arguments)

    @property
    def scope(self):
        """Names of the enclosing modules, outermost first (``[]`` at file level)."""
        return list(self._scope)

    @property
    def line_number(self):
        """Line number of the pragma in :attr:`filepath`."""
        return self._line_number

    @property
    def filepath(self):
        """File the pragma was written in (``None`` for :meth:`idl_parser.parser.IDLParser.load`
        without ``filepath``)."""
        return self._filepath

    @property
    def is_keylist(self):
        """True for ``#pragma keylist``."""
        return self._name == 'keylist'

    @property
    def type_name(self):
        """For a keylist, the name of the target type as written; otherwise ``None``."""
        if self.is_keylist and self._arguments:
            return self._arguments[0]
        return None

    @property
    def keys(self):
        """For a keylist, the key member names (may be empty); otherwise ``None``."""
        if self.is_keylist:
            return list(self._arguments[1:])
        return None

    @property
    def target(self):
        """For a keylist, the :class:`IDLStruct` it applies to; for
        ``#pragma ID`` and ``#pragma version``, the definition it applies to
        (issue #135). ``None`` if not found, and for other pragmas."""
        return self._target

    @property
    def is_prefix(self):
        """True for ``#pragma prefix`` (issue #135)."""
        return self._name == 'prefix'

    @property
    def is_id(self):
        """True for ``#pragma ID`` (issue #135)."""
        return self._name == 'ID'

    @property
    def is_version(self):
        """True for ``#pragma version`` (issue #135)."""
        return self._name == 'version'

    @property
    def value(self):
        """The string of ``#pragma prefix "P"`` (``'P'``), of ``#pragma ID A "ID"``
        (``'ID'``) or the version of ``#pragma version A 2.4`` (``'2.4'``),
        without quotes; otherwise ``None`` (issue #135)."""
        if self.is_prefix:
            return _unquote(' '.join(self._arguments)) if self._arguments else ''
        if self.is_id or self.is_version:
            if len(self._arguments) >= 2:
                return _unquote(' '.join(self._arguments[1:]))
        return None

    @property
    def unresolved_keys(self):
        """For a keylist whose target was found, the key names that do not
        name a member of the target struct (``[]`` when all are valid).
        ``None`` for other pragmas or when the target has not been found."""
        if self._unresolved_keys is None:
            return None
        return list(self._unresolved_keys)

    def _check_keys(self):
        self._unresolved_keys = [k for k in self.keys
                                 if not _key_exists(self._target, k)]
        for k in self._unresolved_keys:
            where = self._filepath if self._filepath is not None else '<string>'
            if self._line_number is not None:
                where += ', line %s' % self._line_number
            warnings.warn('%s: #pragma keylist %s: %r is not a member of %s'
                          % (where, self.type_name, k, self._target.full_path),
                          KeylistWarning, stacklevel=2)

    def _resolve(self, global_module):
        """Apply a keylist, ``#pragma ID`` or ``#pragma version``.

        See :meth:`_resolve_keylist` and
        :func:`idl_parser.repository_id.apply_pragma`.
        """
        if self.is_id or self.is_version:
            from . import repository_id
            return repository_id.apply_pragma(self, global_module)
        return self._resolve_keylist(global_module)

    def _resolve_keylist(self, global_module):
        """Find the target struct of a keylist and attach the keys to it.

        The type name is looked up like a C++ name: from the innermost
        enclosing module outwards. A name starting with ``::`` is absolute.
        Returns True when the target is found (or the pragma is not a keylist).
        """
        if not self.is_keylist:
            return True
        if self._target is not None:
            return True
        name = self.type_name
        if not name:
            return False

        if name.startswith('::'):
            candidates = [name[2:]]
        else:
            candidates = []
            for i in range(len(self._scope), -1, -1):
                candidates.append('::'.join(self._scope[:i] + [name]))

        for full_name in candidates:
            node = _find_struct(global_module, full_name.split('::'))
            if node is not None:
                node._set_keys(self.keys)
                self._target = node
                self._check_keys()
                return True
        return False

    def __repr__(self):
        return '<IDLPragma #pragma %s>' % ' '.join([self._name] + self._arguments)


def _unquote(text):
    """``'"omg.org"'`` -> ``'omg.org'``."""
    text = text.strip()
    if len(text) >= 2 and text[0] == '"' and text[-1] == '"':
        return text[1:-1]
    return text


# Names of the pragmas put around the lines of an #include file, so that a
# #pragma prefix ends with the file it is written in (issue #135). They are
# not listed in IDLParser.pragmas.
INCLUDE_BEGIN = '__include_begin__'
INCLUDE_END = '__include_end__'


def _key_exists(struct, key):
    """True if ``key`` (``'a'`` or ``'a.b.c'``) names a member of ``struct``.

    Every name except the last must be a member whose type is a struct
    (typedefs are followed).
    """
    names = key.split('.')
    node = struct
    for i, name in enumerate(names):
        if not name or node is None or not getattr(node, 'is_struct', False):
            return False
        member = node.member_by_name(name)
        if member is None:
            return False
        if i == len(names) - 1:
            return True
        try:
            node = member.type
            while getattr(node, 'is_typedef', False):
                node = node.type
        except exception.InvalidDataTypeException:
            return False
    return True


def _find_struct(global_module, path):
    m = global_module
    for name in path[:-1]:
        m = m.module_by_name(name)
        if m is None:
            return None
    return m.struct_by_name(path[-1])


def extract_pragmas(lines, keep_in_place=False):
    """Remove ``#pragma`` lines from preprocessed ``lines``.

    :param lines: List of ``(line_number, filepath, line)`` after comments,
        ``#include`` and ``#ifdef`` have been handled.
    :param keep_in_place: Put each :class:`IDLPragma` where its line was,
        as ``(line_number, filepath, IDLPragma)``, instead of removing the
        line, so that a :class:`~idl_parser.token_buffer.TokenBuffer` can tell
        where it was written (issue #135).
    :returns: ``(lines_without_pragmas, [IDLPragma, ...])``
    """
    output_lines = []
    pragmas = []
    # Track enclosing modules so that keylist type names can be resolved
    # relative to where the pragma is written.
    scope = []      # module names
    braces = []     # for each open "{": module name, or None
    pending_module = None
    expect_module_name = False

    for line_number, file_name, line in lines:
        text = match_pragma(line)
        if text is not None:
            p = IDLPragma(text, scope, line_number, file_name)
            pragmas.append(p)
            if keep_in_place:
                output_lines.append((line_number, file_name, p))
            continue
        output_lines.append((line_number, file_name, line))

        for token in line.split():
            if expect_module_name:
                pending_module = token
                expect_module_name = False
            elif token == 'module':
                expect_module_name = True
            elif token == '{':
                braces.append(pending_module)
                if pending_module is not None:
                    scope.append(pending_module)
                pending_module = None
            elif token == '}':
                if braces and braces.pop() is not None:
                    scope.pop()

    return output_lines, pragmas
