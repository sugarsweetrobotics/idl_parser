"""The entry point: :class:`IDLParser` reads IDL text or files.

Before the definitions are parsed, the input is preprocessed: comments are
removed, ``#define`` / ``#ifdef`` / ``#ifndef`` / ``#if`` / ``#elif`` /
``#else`` / ``#endif`` are applied, ``#include`` directives in the branches
that are kept are expanded, object-like macros are expanded (see :mod:`idl_parser.preprocessor`) and
``#pragma`` lines are taken out (see :mod:`idl_parser.pragma`). Every definition ends up in the
:attr:`IDLParser.global_module` tree.
"""
import os, sys
import re
import functools
import warnings

try:
    from warnings import deprecated as _deprecated
except ImportError:  # Python < 3.13 (PEP 702)
    def _deprecated(message, *, category=DeprecationWarning, stacklevel=1):
        """Small stand-in for :func:`warnings.deprecated` (Python 3.13+):
        warn with ``category`` each time the function is called."""
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                warnings.warn(message, category=category, stacklevel=stacklevel + 1)
                return func(*args, **kwargs)
            wrapper.__deprecated__ = message
            return wrapper
        return decorator

from . import  module, token_buffer, pragma as idl_pragma, preprocessor as idl_preprocessor
from . import repository_id
from .token_buffer import _literal_end
from . import type as idl_type
from . import exception 


class ConsoleTracker():
    """Writes indented progress messages to stdout for ``verbose=True``.

    :meth:`indent` and :meth:`deindent` change the indentation of the
    following :meth:`write` calls by two spaces.
    """
    def __init__(self):
        self._indent = 0
        pass

    def write(self, *args):
        """Write ``args`` to stdout after the current indentation."""
        sys.stdout.write('  ' * self._indent)
        sys.stdout.write(*args)

    def indent(self):
        """Indent the following messages one more level."""
        self._indent = self._indent+1

    def deindent(self):
        """Indent the following messages one level less (not below zero)."""
        self._indent = self._indent-1
        if self._indent < 0: self._indent = 0

logger = ConsoleTracker()


def _format_code(code):
    """Put spaces around punctuation in code outside of literals and
    comments, and squash runs of whitespace into one space."""
    code = code.replace('{', ' { ')
    # A single ':' (case label, inheritance), but not '::' (scoped name).
    code = re.sub(r'(?<!:):(?!:)', ' : ', code)
    code = code.replace(';', ' ;')
    code = code.replace('(', ' ( ')
    code = code.replace(',', ' , ')
    code = code.replace('=', ' = ')
    code = code.replace(')', ' ) ')
    code = code.replace('}', ' } ')
    return re.sub(r'\s+', ' ', code)

class IDLParser():
    """Parser of OMG IDL.

    Each call of :meth:`load` or :meth:`parse` adds its definitions to the same
    :attr:`global_module`, so several inputs can be combined::

        p = IDLParser(idl_dirs=['/path/to/idl'])
        p.parse(idls=['/path/to/idl/a.idl'])
        a = p.global_module.module_by_name('A')

    :param idl_dirs: Include directories, searched for ``#include`` files and
        by :meth:`for_each_idl`.
    :param verbose: Print progress messages to stdout.
    :param defines: Macros defined before each IDL is read, like the ``-D``
        option of a C preprocessor (issue #120): a dict of name to value
        (``{'N': '5', 'DEBUG': ''}``) or a list of names (each defined as
        ``1``).
    """
    def __init__(self, idl_dirs=[], verbose=False, defines=None):
        if defines is None:
            defines = {}
        elif not isinstance(defines, dict):
            defines = dict((name, '1') for name in defines)
        self._defines = dict(defines)
        self._global_module = module.IDLModule()
        self._dirs = idl_dirs
        self._verbose = verbose
        self._parsed_files = []
        self._pragmas = []

    @property
    def global_module(self):
        """The global scope (:class:`~idl_parser.module.IDLModule`) holding
        everything parsed so far.
        """
        return self._global_module

    @property
    def pragmas(self):
        """All ``#pragma`` directives found so far, as :class:`~idl_parser.pragma.IDLPragma`.

        ``#pragma`` lines are removed before parsing, so they never affect the
        parse result. ``#pragma keylist`` entries are applied to their struct
        (see :attr:`idl_parser.struct.IDLStruct.keys`); a keylist whose struct
        has not been found has ``target`` set to ``None``.
        """
        return list(self._pragmas)

    def is_primitive(self, name, except_string=False):
        """True if ``name`` is a primitive type name (``long``, ``string<8>``, ...).

        :param name: Type name.
        :param except_string: Return False for ``string`` and ``wstring``
            (bounded ones included).
        """
        if except_string:
            if idl_type.is_string(name):
                return False
        return idl_type.is_primitive(name)

    @property
    def dirs(self):
        """Include directories (list of paths), in search order."""
        return self._dirs

    @_deprecated('IDLParser.prepare_input() is no longer used by load() and '
                'does not look at string literals (issue #53). '
                'load() and parse() now handle spaces inside "[ ]" and "< >" by themselves.')
    def prepare_input(self, data):
        """Remove whitespace just inside ``[ ]`` and ``< >`` in ``data``.

        No longer used by :meth:`load`: the same joining is now done on
        tokens outside literals and comments, for :meth:`load` and
        :meth:`parse` alike (see :func:`idl_parser.token_buffer.join_brackets`,
        issue #53). Kept for compatibility; it does not look at literals.

        .. deprecated:: 0.2.1
           Calling it emits a :class:`DeprecationWarning`.
        """
        from re import compile, UNICODE, MULTILINE
        flags = UNICODE | MULTILINE

        # Remove whitespace (spaces, tabs, newlines) just inside brackets
        # so that e.g. 'long a[ 5 ]' and 'string< 8 >' become single tokens.
        pattern = compile(r'\[\s+', flags)
        data = pattern.sub('[', data)

        pattern = compile(r'\s+\]', flags)
        data = pattern.sub(']', data)

        pattern = compile(r'\<\s+', flags)
        data = pattern.sub('<', data)

        pattern = compile(r'\s+\>', flags)
        data = pattern.sub('>', data)

        return data

    def load(self, input_str, include_dirs=[], filepath=None):
        """Parse IDL text and return :attr:`global_module`.

        :param input_str: IDL text.
        :param include_dirs: Directories added to :attr:`dirs` (they stay added)
            to look for ``#include`` files.
        :param filepath: File name recorded in the parsed nodes and pragmas, and
            the base for ``#include "..."`` relative paths. ``None`` if the text
            does not come from a file.
        :returns: :attr:`global_module`.
        """
        self._dirs = self._dirs + include_dirs
        lines = [(i+1, filepath, l) for i, l in enumerate(input_str.split('\n'))]
        self.parse_lines(lines, filepath=filepath)
        return self._global_module

    def parse(self, idls=[], idl_dirs=[], except_files=[]):
        """ Parse IDL files. Result of parsing can be accessed via global_module property.

        :param idls: List of IDL files. Must be fullpath.
        :param idl_dirs: Directories added to :attr:`dirs` (they stay added) to
            look for ``#include`` files. The IDL files in them are not parsed;
            use :meth:`parse_dirs` to parse every IDL file in directories.
        :param except_files: List of IDL files that should be ignored. Do not have to use fullpath.
        :returns: None
        """
        if self._verbose:
            logger.write('parse(\n')
            logger.write('  idls=%s\n' % idls)
            logger.indent()
        self.for_each_idl(self.parse_idl, except_files=except_files, idls=idls, idl_dirs=idl_dirs)
        if self._verbose: logger.deindent()

    def parse_dirs(self, idl_dirs, except_files=[]):
        """Parse every IDL file in directories (issue #108).

        The ``*.idl`` files directly in each directory are parsed in the
        order of ``idl_dirs``, and by file name in each directory.
        Sub directories are not searched. The directories are also added to
        :attr:`dirs` (they stay added) to look for ``#include`` files.
        A file already parsed, also through an ``#include``, is not parsed
        again.

        :param idl_dirs: Directories that contain the IDL files.
        :param except_files: File names (not paths) of IDL files that should
            be ignored.
        :returns: List of the absolute paths of the found IDL files.
        :raises FileNotFoundError: A directory does not exist. Nothing is
            parsed and :attr:`dirs` is not changed then.
        """
        if self._verbose:
            logger.write('parse_dirs(\n')
            logger.write('  idl_dirs=%s\n' % idl_dirs)
            logger.indent()
        idls = []
        for d in idl_dirs:
            for f in sorted(os.listdir(d)):
                path = os.path.abspath(os.path.join(d, f))
                if f.endswith('.idl') and f not in except_files and os.path.isfile(path) \
                        and path not in idls:
                    idls.append(path)
        self._dirs = self._dirs + [d for d in idl_dirs if d not in self._dirs]
        for path in idls:
            self.parse_idl(path)
        if self._verbose: logger.deindent()
        return idls

    def parse_idl(self, idl_path):
        """Parse one IDL file into :attr:`global_module`.

        A file that has already been parsed by this parser is skipped.

        :param idl_path: Path of the IDL file.
        """
        # Compare absolute paths so that one file given by a relative and an
        # absolute path is parsed once.
        abs_path = os.path.abspath(idl_path)
        if abs_path in self._parsed_files:
            if self._verbose:
                logger.write('Parsing IDL(%s) but ALREADY PARSED.\n' % idl_path)
            return
            pass
        if self._verbose: 
            logger.write('Parsing IDL(%s)\n' % idl_path) #sys.stdout.write(' - Parsing IDL (%s)\n' % idl_path)
            logger.indent()
        # Mark as parsed BEFORE parsing so that mutually including files
        # do not re-enter parse_idl() endlessly (issue #6).
        self._parsed_files.append(abs_path)
        lines = []
        with open(idl_path, 'r') as f:
            for line_number, line in enumerate(f, 1):
                lines.append((line_number, idl_path, line))

        self.parse_lines(lines, filepath=idl_path)

        if self._verbose: 
            logger.deindent()
            logger.write('Parsed IDL (%s)\n' % idl_path)

    def parse_lines(self, lines, filepath=None):
        """Preprocess and parse lines into :attr:`global_module`.

        :param lines: List of ``(line_number, file_name, line)`` tuples.
        :param filepath: File name recorded in the parsed nodes.
        """
        lines = self._clear_comments(lines)
        lines = self._clear_ifdef(lines)
        lines = self._extract_pragmas(lines)

        self._token_buf = token_buffer.TokenBuffer(lines)
        # A #pragma prefix ends with the file it is written in (issue #135)
        self._global_module._prefix_state = ('', None)
        self._global_module._include_prefixes = []
        self._global_module.parse_tokens(self._token_buf, filepath=filepath)
        self._apply_pragmas()

    def _extract_pragmas(self, lines):
        """Take ``#pragma`` lines out of the text and remember them (issues #10 / #28).

        Each pragma stays in ``lines`` as an :class:`~idl_parser.pragma.IDLPragma`,
        so that the parser knows where it is written (issue #135).
        """
        lines, pragmas = idl_pragma.extract_pragmas(lines, keep_in_place=True)
        # A file included by several files is pasted into each of them, so
        # the same pragma can be seen twice.
        known = set((p.filepath, p.line_number) for p in self._pragmas)
        for p in pragmas:
            if p.name in (idl_pragma.INCLUDE_BEGIN, idl_pragma.INCLUDE_END):
                continue
            key = (p.filepath, p.line_number)
            if p.filepath is not None and key in known:
                continue
            known.add(key)
            self._pragmas.append(p)
        return lines

    def _apply_pragmas(self):
        # Retried after every parse so that a keylist may come before the
        # struct it names, even when the struct is in a file parsed later.
        for p in self._pragmas:
            p._resolve(self._global_module)
        # typeid / typeprefix declarations (issue #135)
        for d in self._global_module._type_declarations:
            repository_id.apply_declaration(d, self._global_module)

    def includes(self, idl_path):
        """Paths of the files named by the ``#include`` directives of an IDL file.

        Only the given file is read (included files are not followed), and each
        path appears once, in order.

        :param idl_path: Path of the IDL file.
        :returns: List of paths.
        :raises ~idl_parser.exception.IDLCanNotFindException: An included file
            can not be found.
        """
        included_filepaths = []
        with open(idl_path, 'r') as f:
            for line_number, line in enumerate(f, 1):
                if line.find('#include') >= 0:
                    if line.find('"') >= 0:
                        file = line[line.find('"')+1:line.rfind('"')].strip()
                    elif line.find('<') >= 0:
                        file = line[line.find('<')+1:line.rfind('>')].strip()
                    else:
                        continue
                    p = self._resolve_include(file, current_file=idl_path)
                    if p is None:
                        raise self._include_not_found(file, line_number, idl_path)
                    if p not in included_filepaths:
                        included_filepaths.append(p)

        return included_filepaths


    def for_each_idl(self, func, idl_dirs=[], except_files=[], idls=[], find_all=False):
        """ Parse IDLs and apply function.
        :param func: Function. IDL file fullpath will be passed to the function.
        :param idls: List of IDL files. Must be fullpath.
        :param idl_dirs: List of directory which contains target IDL files. Must be fullpath.
        :param except_files: List of IDL files that should be ignored. Do not have to use fullpath.
        :returns: None
        """
        idl_dirs = self._dirs + idl_dirs
        self._dirs = idl_dirs
        idls_ = []
        basenames_ = []
        for idl_dir in idl_dirs:
            for f in os.listdir(idl_dir):
                if f.endswith('.idl'):
                    if not f in except_files:
                        path = os.path.join(idl_dir, f)
                        if not f in basenames_:
                            if not( path in idls_ ):
                                idls_.append(path)
                                basenames_.append(os.path.basename(path))

        #idls_ = idls_ + idls

        if find_all:
            idls_ = idls_ + idls
        else:
            idls_ = idls

        for f in idls_:
            # if self._verbose: sys.stdout.write(' - Apply function to %s\n' % f)
            func(f)

    def _find_idl(self, filename, apply_func, idl_dirs=[]):
        if self._verbose: 
            logger.write('Finding %s\n' % filename)
            logger.indent()

        global retval
        retval = None
        def func(filepath):
            if os.path.basename(filepath) == filename:
                if self._verbose:
                    logger.write('Found %s\n' % filename)
                global retval
                retval = apply_func(filepath)

        self.for_each_idl(func, idl_dirs=idl_dirs, find_all=True)
        if self._verbose: logger.deindent()
        return retval

    def _resolve_include(self, filename, current_file=None):
        """ Find the IDL file named by an ``#include`` directive.

        ``filename`` may contain a sub path such as ``std/msg/Header.idl``
        (issue #12). Like a C preprocessor, the path is tried relative to
        the directory of the including file first, then relative to each
        include directory. If nothing is found, fall back to the old
        behaviour of matching the base name of IDLs in the include
        directories.

        :returns: Path of the found IDL, or None.
        """
        candidates = []
        if os.path.isabs(filename):
            candidates.append(filename)
        else:
            if current_file is not None:
                candidates.append(os.path.join(os.path.dirname(os.path.abspath(current_file)), filename))
            for d in self._dirs:
                candidates.append(os.path.join(d, filename))
        for c in candidates:
            if os.path.isfile(c):
                if self._verbose: logger.write('Found %s\n' % c)
                return c

        return self._find_idl(os.path.basename(filename), lambda p: p)

    def _include_not_found(self, filename, line_number, current_file):
        """The exception for an ``#include`` whose file can not be found
        (issue #110). The message names the file and the directories that
        were searched; the exception carries the line and the file of the
        ``#include``."""
        dirs = []
        if not os.path.isabs(filename):
            if current_file is not None:
                dirs.append(os.path.dirname(os.path.abspath(current_file)))
            for d in self._dirs:
                if d not in dirs:
                    dirs.append(d)
        msg = 'Included file "%s" can not be found.' % filename
        if dirs:
            msg += ' Searched: %s' % ', '.join(dirs)
        return exception.IDLCanNotFindException(line_number, current_file, msg)

    def _include_function(self, lines):
        """The function that reads an ``#include`` for
        :class:`idl_parser.preprocessor.Preprocessor` (issue #127).

        The preprocessor calls it only for an ``#include`` in a branch that
        is kept, so a file named in a skipped ``#if`` branch is neither
        searched nor parsed. Each file is pasted at most once in this
        translation unit (like ``#pragma once``), which also stops infinite
        recursion when IDL files include each other (issue #6). A pasted
        file is recorded in :meth:`parse_idl`'s list of parsed files, so it
        is not parsed again on its own.
        """
        pasted = set()
        for _, file_name, _ in lines:
            if file_name is not None:
                pasted.add(os.path.abspath(file_name))

        def include(text, line_number, file_name):
            text = text.strip()
            if text.startswith('"') and text.find('"', 1) > 0:
                filename = text[1:text.find('"', 1)]
            elif text.startswith('<') and text.find('>') > 0:
                filename = text[1:text.find('>')]
            else:
                return []
            filename = filename.strip()
            if self._verbose: logger.write('Find Includes %s\n' % filename)
            p = self._resolve_include(filename, current_file=file_name)
            if p is None:
                if self._verbose: logger.write(' # IDL (%s) can not be found.\n' % filename)
                raise self._include_not_found(filename, line_number, file_name)

            abs_p = os.path.abspath(p)
            if abs_p in pasted:
                if self._verbose: logger.write('IDL (%s) already included. Skipped.\n' % filename)
                return []
            pasted.add(abs_p)
            if abs_p not in self._parsed_files:
                self._parsed_files.append(abs_p)
            if self._verbose: logger.write('IDL Found (%s). Including\n' % filename)
            inc_lines = []
            with open(p, 'r') as f:
                for ln, l in enumerate(f, 1):
                    inc_lines.append((ln, p, l))
            # Mark where the file begins and ends, so that a #pragma prefix
            # in it ends with it (issue #135)
            return ([(line_number, file_name, '#pragma %s\n' % idl_pragma.INCLUDE_BEGIN)] +
                    self._clear_comments(inc_lines) +
                    [(line_number, file_name, '#pragma %s\n' % idl_pragma.INCLUDE_END)])

        return include

    def _clear_comments(self, lines):
        """Remove comments and put spaces around punctuation so that each
        token is separated by whitespace.

        Lines are scanned one character at a time. String literals
        (``"..."``) and character literals (``'...'``) are copied as they
        are: ``//`` or ``/*`` inside them is not a comment (issue #50), and
        no spaces are put into them. A ``:`` right after a literal, as in
        ``case 'a':``, is separated like any other ``:`` (issue #49).

        No spaces are put into ``#define`` / ``#if`` / ... lines (see
        :data:`idl_parser.preprocessor.DIRECTIVES`), so that ``F(x)`` and
        ``a <= b`` stay as written (issue #120).
        """
        output_lines = []
        in_comment = False

        for line_number, file_name, line in lines:
            parts = []  # code (formatted) and literals (as they are), in order
            code = ''
            fmt = _format_code
            if not in_comment and idl_preprocessor.is_directive_line(line):
                fmt = lambda c: re.sub(r'\s+', ' ', c)
            i = 0
            n = len(line)
            while i < n:
                if in_comment:
                    end = line.find('*/', i)
                    if end < 0:
                        break  # the comment continues on the next line
                    in_comment = False
                    i = end + 2
                    code = code + ' '
                elif line.startswith('//', i):
                    break  # ignore the rest of this line
                elif line.startswith('/*', i):
                    in_comment = True
                    i = i + 2
                    code = code + ' '
                elif line[i] in '"\'':
                    end = _literal_end(line, i)
                    parts.append(fmt(code))
                    parts.append(line[i:end].rstrip('\r\n'))
                    code = ''
                    i = end
                else:
                    code = code + line[i]
                    i = i + 1
            parts.append(fmt(code))

            output_line = ''.join(parts).strip()
            if len(output_line) > 0:
                output_lines.append((line_number, file_name, output_line + '\n'))

        return output_lines

    def _clear_ifdef(self, lines):
        """Apply ``#define`` / ``#if`` / ..., paste ``#include`` files in the
        branches that are kept and expand macros (issues #120 / #127)."""
        pp = idl_preprocessor.Preprocessor(format_code=_format_code,
                                           include=self._include_function(lines))
        for name, value in self._defines.items():
            pp.define(name, value)
        return pp.preprocess(lines)


    def generate_constructor_python(self, typ):
        """Python expression that builds the default value of ``typ``.

        Intended for generating Python (omniORBpy style) code: ``0`` for
        primitive types, fixed-point types, bitmasks and bitsets, ``None`` for
        ``any``, ``Object`` and ``ValueBase``, ``[]`` for sequences, ``{}`` for
        maps, a list for
        arrays, the first enumerator for enums, ``None`` for native types and
        value types, and
        a constructor call with the member defaults for structs (those of
        the base struct first). Scoped names use ``.``
        (a struct ``M::T { long x; }`` gives ``'M.T(0)'``).

        :param typ: A type or definition node, such as ``member.type``.
        :returns: The expression as a string.
        """
        code = ''
        if typ.is_sequence:
            code = code + '[]'
        if typ.is_map:
            code = code + '{}'
        if typ.is_array:
            code = code + '['
            for i in range(typ.size):
                code = code + self.generate_constructor_python(typ.inner_type)
                if i != typ.size-1:
                    code = code + ', '
            code = code + ']'
        elif typ.is_primitive:
            # any, Object and ValueBase may be nil (issue #119)
            code = code + ('None' if typ.name in idl_type.reference_primitive else '0')
        elif typ.is_fixed:
            code = code + '0'
        elif typ.is_typedef:
            code = code + self.generate_constructor_python(typ.type)
        elif typ.is_enum:
            # IDL enumerators belong to the scope enclosing the enum
            # (module M { enum E { A, B }; } -> M::A), as in omniORBpy
            if typ.values:
                scope = typ.parent.full_path.lstrip(':')  # '::I' for an interface at global scope
                code = code + (scope + '::' if scope else '') + typ.values[0].name
            else:
                code = code + '0'
        elif typ.is_bitmask or typ.is_bitset:
            code = code + '0'
        elif typ.is_native:
            # A native type has no IDL-defined value (issue #93)
            code = code + 'None'
        elif typ.is_valuetype:
            # A value may be null (issue #99)
            code = code + 'None'
        elif typ.is_struct:
            code = code + typ.full_path.lstrip(':') + '('  # '::T' at global scope -> 'T'
            for m in typ.all_members:
                code = code + self.generate_constructor_python(m.type.obj) + ', '
            if typ.all_members:
                code = code[:-2]
            code = code + ')'
        return code.replace('::', '.')
