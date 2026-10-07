"""``#pragma`` directives found in IDL files (issues #10 / #28).

``#pragma`` lines are taken out of the input during preprocessing, so they
never reach the parser as tokens and are ignored wherever they are written.
Each one is kept as an :class:`IDLPragma` and is available from
:attr:`idl_parser.parser.IDLParser.pragmas`.

``#pragma keylist <type> [<member> ...]`` (OpenSplice DDS) is interpreted:
the named struct is looked up after the whole input has been parsed, so the
struct may be defined before or after the pragma, and its key members are
available as :attr:`idl_parser.struct.IDLStruct.keys`.  Other pragmas
(``#pragma prefix``, ``#pragma once``, vendor-specific ones, ...) are only
recorded.
"""
import re

_PRAGMA_RE = re.compile(r'^#\s*pragma\b(.*)$')


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
        return self._line_number

    @property
    def filepath(self):
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
        """For a keylist, the :class:`IDLStruct` it applies to, or ``None`` if not found."""
        return self._target

    def _resolve(self, global_module):
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
                return True
        return False

    def __repr__(self):
        return '<IDLPragma #pragma %s>' % ' '.join([self._name] + self._arguments)


def _find_struct(global_module, path):
    m = global_module
    for name in path[:-1]:
        m = m.module_by_name(name)
        if m is None:
            return None
    return m.struct_by_name(path[-1])


def extract_pragmas(lines):
    """Remove ``#pragma`` lines from preprocessed ``lines``.

    :param lines: List of ``(line_number, filepath, line)`` after comments,
        ``#include`` and ``#ifdef`` have been handled.
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
            pragmas.append(IDLPragma(text, scope, line_number, file_name))
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
