import os, sys
import re

from . import  module, token_buffer
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

class IDLParser():

    def __init__(self, idl_dirs=[], verbose=False):
        self._global_module = module.IDLModule()
        self._dirs = idl_dirs
        self._verbose = verbose
        self._parsed_files = []

    @property
    def global_module(self):
        return self._global_module

    def is_primitive(self, name, except_string=False):
        if except_string:
            if name == 'string' or name == 'wstring':
                return False
        return idl_type.is_primitive(name)

    @property
    def dirs(self):
        return self._dirs

    def prepare_input(self, data):
        from re import compile, UNICODE, MULTILINE
        flags = UNICODE | MULTILINE

        pattern = compile('\[[ \n]+', flags)
        data = pattern.sub('[', data)

        pattern = compile('[ \n]+\]', flags)
        data = pattern.sub(']', data)

        pattern = compile('\<[ \n]+', flags)
        data = pattern.sub('<', data)

        pattern = compile('[ \n]+\>', flags)
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
        f = open(idl_path, 'r')
        lines = []
        line_number = 1
        for line in f:
            lines.append((line_number, idl_path, line))
            line_number = line_number + 1

        self.parse_lines(lines)

        if self._verbose: 
            logger.deindent()
            logger.write('Parsed IDL (%s)\n' % idl_path)        
        self._parsed_files.append(idl_path)

    def parse_lines(self, lines, filepath=None):
        lines = self._clear_comments(lines)
        lines = self._paste_include(lines)
        lines = self._clear_ifdef(lines)

        self._token_buf = token_buffer.TokenBuffer(lines)
        self._global_module.parse_tokens(self._token_buf, filepath=filepath)

    def includes(self, idl_path):
        included_filepaths = []
        included_filenames = []
        f = open(idl_path, 'r')
        lines = []
        for line in f:
            if line.find('#include') >= 0:
                if line.find('"') >= 0:
                    file = line[line.find('"')+1:line.rfind('"')].strip()
                elif line.find('<') >= 0:
                    file = line[line.find('<')+1:line.rfind('>')].strip()
                included_filenames.append(file)
        def get_fullpath(idl_path):
            if os.path.basename(idl_path) in included_filenames:
                included_filepaths.append(idl_path)
                included_filenames.remove(os.path.basename(idl_path))

        self.for_each_idl(get_fullpath, find_all=True)
        if len(included_filenames) > 0:
            raise exception.IDLCanNotFindException()

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

    def _paste_include(self, lines):
        output_lines = []
        for line_number, file_name, line in lines:
            output_line = ''
            if line.startswith('#include'):
                def _include_paste(filepath):
                    return filepath

                if line.find('"') >= 7:
                    filename = line[line.find('"')+1 : line.rfind('"')]
                    if self._verbose: logger.write('Find Includes %s\n' % filename)
                    p = self._find_idl(filename, _include_paste)
                    if p is None:
                        if self._verbose:logger.write(' # IDL (%s) can not be found.\n' % filename)
                        raise exception.IDLCanNotFindException
                    if self._verbose: logger.write('IDL Found (%s). Parsing\n'% filename)
                    self.parse_idl(idl_path = p)
                    if self._verbose: logger.write('Including IDL Parsing End.\n')

                    inc_lines = []
                    f = open(p, 'r')
                    ln = 1
                    for l in f:
                        inc_lines.append((ln, p, l))
                        ln = ln + 1
                    inc_lines = self._clear_comments(inc_lines)
                    inc_lines = self._paste_include(inc_lines)
                    output_lines = output_lines + inc_lines

                elif line.find('<') >= 7:
                    filename = line[line.find('<')+1 : line.rfind('>')]
                    if self._verbose: sys.stdout.write(' -- Includes %s\n' % filename)
                    p = self._find_idl(filename, _include_paste)
                    if p is None:
                        if self._verbose:sys.stdout.write(' # IDL (%s) can not be found.\n' % filename)
                        raise exception.IDLCanNotFindException
                    inc_lines = []

                    self.parse_idl(idl_path = p)

                    f = open(p, 'r')
                    ln = 1
                    for l in f:
                        inc_lines.append((ln, p, l))
                        ln = ln + 1
                    inc_lines = self._clear_comments(inc_lines)
                    inc_lines = self._paste_include(inc_lines)
                    output_lines = output_lines + inc_lines

            else:
                output_line = line

            output_lines.append((line_number, file_name, output_line))

        return output_lines



    def _clear_comments(self, lines):
        output_lines = []
        in_comment = False

        for line_number, file_name, line in lines:
            line = line.strip()
            output_line = ''
            if line.find('//') >= 0:
                line = line[:line.find('//')]

            for token in line.split(' '):

                if in_comment and token.find('*/') >= 0:
                    in_comment = False
                    output_line = output_line + ' ' + token[token.find('*/')+2:].strip()

                elif in_comment:
                    continue

                elif token.startswith('//'):
                    break # ignore this line

                elif token.find('/*') >= 0:
                    in_comment = True
                    output_line = output_line + ' ' + token[0: token.find('/*')]
                else:
                    if token.find('{') >= 0:
                        token = token.replace('{', ' { ')
                    if token.find(':') >= 0:
                        token = re.sub(r'([a-zA-Z0-9_]{1}):([a-zA-Z0-9_]{1}|$)', r'\1 : \2', token)
                    if token.find(';') >= 0:
                        token = token.replace(';', ' ;')
                    if token.find('(') >= 0:
                        token = token.replace('(', ' ( ')
                    token = token.replace(',', ' , ')
                    token = token.replace(')', ' ) ')
                    token = token.replace('}', ' } ')
                    output_line = output_line + ' ' + token.strip()
            if len(output_line.strip()) > 0:
                output_lines.append((line_number, file_name, output_line.strip() + '\n'))

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
                    def_token = line.split(' ')[1]
                    def_tokens.append(def_token)
                    offset = offset + 1
                elif line.startswith('#ifdef'):
                    def_token = line.split(' ')[1]
                    offset = offset + 1
                    _parse(def_token in def_tokens)

                elif line.startswith('#ifndef'):
                    def_token = line.split(' ')[1]
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
