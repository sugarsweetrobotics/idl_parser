import os, sys
import re

from . import  module, token_buffer, pragma as idl_pragma
from .token_buffer import _literal_end
from . import type as idl_type
from . import exception 


class ConsoleTracker():
    def __init__(self):
        self._indent = 0
        pass

    def write(self, *args):
        sys.stdout.write('  ' * self._indent)
        sys.stdout.write(*args)

    def indent(self):
        self._indent = self._indent+1

    def deindent(self):
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

    def __init__(self, idl_dirs=[], verbose=False):
        self._global_module = module.IDLModule()
        self._dirs = idl_dirs
        self._verbose = verbose
        self._parsed_files = []
        self._pragmas = []

    @property
    def global_module(self):
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
        if except_string:
            if idl_type.is_string(name):
                return False
        return idl_type.is_primitive(name)

    @property
    def dirs(self):
        return self._dirs

    def prepare_input(self, data):
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
        self._dirs = self._dirs + include_dirs
        input_str = self.prepare_input(input_str)
        lines = [(i+1, filepath, l) for i, l in enumerate(input_str.split('\n'))]
        self.parse_lines(lines, filepath=filepath)
        return self._global_module

    def parse(self, idls=[], idl_dirs=[], except_files=[]):
        """ Parse IDL files. Result of parsing can be accessed via global_module property.
        :param idls: List of IDL files. Must be fullpath.
        :param idl_dirs: List of directory which contains target IDL files. Must be fullpath.
        :param except_files: List of IDL files that should be ignored. Do not have to use fullpath.
        :returns: None
        """
        if self._verbose:
            logger.write('parse(\n')
            logger.write('  idls=%s\n' % idls)
            logger.indent()
        self.for_each_idl(self.parse_idl, except_files=except_files, idls=idls, idl_dirs=idl_dirs)
        if self._verbose: logger.deindent()

    def parse_idl(self, idl_path):
        if idl_path in self._parsed_files:
            if self._verbose:
                logger.write('Parsing IDL(%s) but ALREADY PARSED.\n' % idl_path)
            return
            pass
        if self._verbose: 
            logger.write('Parsing IDL(%s)\n' % idl_path) #sys.stdout.write(' - Parsing IDL (%s)\n' % idl_path)
            logger.indent()
        # Mark as parsed BEFORE parsing so that mutually including files
        # do not re-enter parse_idl() endlessly (issue #6).
        self._parsed_files.append(idl_path)
        lines = []
        with open(idl_path, 'r') as f:
            for line_number, line in enumerate(f, 1):
                lines.append((line_number, idl_path, line))

        self.parse_lines(lines)

        if self._verbose: 
            logger.deindent()
            logger.write('Parsed IDL (%s)\n' % idl_path)

    def parse_lines(self, lines, filepath=None):
        lines = self._clear_comments(lines)
        lines = self._paste_include(lines)
        lines = self._clear_ifdef(lines)
        lines = self._extract_pragmas(lines)

        self._token_buf = token_buffer.TokenBuffer(lines)
        self._global_module.parse_tokens(self._token_buf, filepath=filepath)
        self._apply_pragmas()

    def _extract_pragmas(self, lines):
        """Remove ``#pragma`` lines and remember them (issues #10 / #28)."""
        lines, pragmas = idl_pragma.extract_pragmas(lines)
        # An included file is parsed on its own and also pasted into the
        # including file, so the same pragma can be seen twice.
        known = set((p.filepath, p.line_number) for p in self._pragmas)
        for p in pragmas:
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

    def includes(self, idl_path):
        included_filepaths = []
        with open(idl_path, 'r') as f:
            for line in f:
                if line.find('#include') >= 0:
                    if line.find('"') >= 0:
                        file = line[line.find('"')+1:line.rfind('"')].strip()
                    elif line.find('<') >= 0:
                        file = line[line.find('<')+1:line.rfind('>')].strip()
                    else:
                        continue
                    p = self._resolve_include(file, current_file=idl_path)
                    if p is None:
                        raise exception.IDLCanNotFindException()
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

    def _paste_include(self, lines, pasted=None):
        """ Expand #include directives in-place.

        :param pasted: Set of absolute paths already expanded in this
            translation unit. Each file is pasted at most once (like
            ``#pragma once``), which also stops infinite recursion when
            IDL files include each other (issue #6).
        """
        if pasted is None:
            pasted = set()
            for _, file_name, _ in lines:
                if file_name is not None:
                    pasted.add(os.path.abspath(file_name))
        output_lines = []
        for line_number, file_name, line in lines:
            output_line = ''
            if line.startswith('#include'):
                if line.find('"') >= 7:
                    filename = line[line.find('"')+1 : line.rfind('"')]
                elif line.find('<') >= 7:
                    filename = line[line.find('<')+1 : line.rfind('>')]
                else:
                    filename = None

                if filename is not None:
                    if self._verbose: logger.write('Find Includes %s\n' % filename)
                    p = self._resolve_include(filename.strip(), current_file=file_name)
                    if p is None:
                        if self._verbose: logger.write(' # IDL (%s) can not be found.\n' % filename)
                        raise exception.IDLCanNotFindException

                    abs_p = os.path.abspath(p)
                    if abs_p in pasted:
                        if self._verbose: logger.write('IDL (%s) already included. Skipped.\n' % filename)
                    else:
                        pasted.add(abs_p)
                        if self._verbose: logger.write('IDL Found (%s). Parsing\n' % filename)
                        self.parse_idl(idl_path = p)
                        if self._verbose: logger.write('Including IDL Parsing End.\n')

                        inc_lines = []
                        with open(p, 'r') as f:
                            for ln, l in enumerate(f, 1):
                                inc_lines.append((ln, p, l))
                        inc_lines = self._clear_comments(inc_lines)
                        inc_lines = self._paste_include(inc_lines, pasted)
                        output_lines = output_lines + inc_lines

            else:
                output_line = line

            output_lines.append((line_number, file_name, output_line))

        return output_lines



    def _clear_comments(self, lines):
        """Remove comments and put spaces around punctuation so that each
        token is separated by whitespace.

        Lines are scanned one character at a time. String literals
        (``"..."``) and character literals (``'...'``) are copied as they
        are: ``//`` or ``/*`` inside them is not a comment (issue #50), and
        no spaces are put into them. A ``:`` right after a literal, as in
        ``case 'a':``, is separated like any other ``:`` (issue #49).
        """
        output_lines = []
        in_comment = False

        for line_number, file_name, line in lines:
            parts = []  # code (formatted) and literals (as they are), in order
            code = ''
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
                    parts.append(_format_code(code))
                    parts.append(line[i:end].rstrip('\r\n'))
                    code = ''
                    i = end
                else:
                    code = code + line[i]
                    i = i + 1
            parts.append(_format_code(code))

            output_line = ''.join(parts).strip()
            if len(output_line) > 0:
                output_lines.append((line_number, file_name, output_line + '\n'))

        return output_lines

    def _clear_ifdef(self, lines):
        output_lines = []
        def_tokens = []
        global offset
        offset = 0
        def _parse(flag):
            global offset
            while offset < len(lines):
                line_number, file_name, line = lines[offset]
                if line.startswith('#define'):
                    def_token = line.split()[1]
                    def_tokens.append(def_token)
                    offset = offset + 1
                elif line.startswith('#ifdef'):
                    def_token = line.split()[1]
                    offset = offset + 1
                    _parse(def_token in def_tokens)

                elif line.startswith('#ifndef'):
                    def_token = line.split()[1]
                    offset = offset + 1
                    _parse(not def_token in def_tokens)

                elif line.startswith('#endif'):
                    offset = offset + 1
                    return

                else:
                    offset = offset + 1
                    if flag:
                        output_lines.append((line_number, file_name, line))

        _parse(True)
        return output_lines


    def generate_constructor_python(self, typ):
        code = ''
        if typ.is_sequence:
            code = code + '[]'
        if typ.is_array:
            code = code + '['
            for i in range(typ.size):
                code = code + self.generate_constructor_python(typ.inner_type)
                if i != typ.size-1:
                    code = code + ', '
            code = code + ']'
        elif typ.is_primitive:
            code = code + '0'
        elif typ.is_typedef:
            code = code + self.generate_constructor_python(typ.type)
        elif typ.is_struct:
            code = code + typ.full_path + '('
            for m in typ.members:
                if m.type.is_primitive:
                    code = code + self.generate_constructor_python(m.type) + ', '
                else:
                    code = code + self.generate_constructor_python(m.type.obj) + ', '
            code = code[:-2] + ')'
        return code.replace('::', '.')
