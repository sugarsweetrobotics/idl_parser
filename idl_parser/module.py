import os, sys, traceback

from . import node, type
from . import struct, typedef, interface, enum, const, union, bitmask, bitset
from .exception import InvalidIDLSyntaxError
global_namespace = '__global__'
sep = '::'

class IDLModule(node.IDLNode):

    def __init__(self, name=None, parent = None):
        super(IDLModule, self).__init__('IDLModule', name, parent)
        self._verbose = False
        if name is None:
            self._name = global_namespace

        self._interfaces = []
        self._forward_interfaces = []
        self._typedefs = []
        self._structs = []
        self._enums = []
        self._bitmasks = []
        self._bitsets = []
        self._unions = []
        self._consts = []
        self._modules = []

    @property
    def is_global(self):
        return self.name == global_namespace

    @property
    def full_path(self):
        if self.parent is None:
            return '' # self.name
        else:
            if len(self.parent.full_path) == 0:
                return self.name
            return self.parent.full_path + sep + self.name

    def to_simple_dic(self, quiet=False):
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

                value_ = values[-1]
                name_ = values[-3]
                typename = ''
                for t in values[:-3]:
                    typename = typename + ' ' + t
                typename = typename.strip()
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
        return self._modules

    def module_by_name(self, name):
        for m in self.modules:
            if m.name == name:
                return m
        return None

    def for_each_module(self, func):
        retval = []
        for m in self.modules:
            retval.append(func(m))
        return retval

    @property
    def interfaces(self):
        return self._interfaces

    def interface_by_name(self, name):
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
        retval = []
        for m in self.interfaces:
            retval.append(func(m))
        return retval

    @property
    def structs(self):
        return self._structs

    def struct_by_name(self, name):
        for s in self.structs:
            if s.name == name:
                return s
        return None

    def for_each_struct(self, func, filter=None):
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
        return self._enums

    def enum_by_name(self, name):
        for e in self.enums:
            if e.name == name:
                return e
        return None

    def for_each_enum(self, func):
        retval = []
        for m in self.enums:
            retval.append(func(m))
        return retval

    @property
    def bitmasks(self):
        return self._bitmasks

    def bitmask_by_name(self, name):
        for b in self.bitmasks:
            if b.name == name:
                return b
        return None

    def for_each_bitmask(self, func):
        return [func(b) for b in self.bitmasks]

    @property
    def bitsets(self):
        return self._bitsets

    def bitset_by_name(self, name):
        for b in self.bitsets:
            if b.name == name:
                return b
        return None

    def for_each_bitset(self, func):
        return [func(b) for b in self.bitsets]

    @property
    def unions(self):
        return self._unions

    def union_by_name(self, name):
        for u in self.unions:
            if u.name == name:
                return u
        return None

    def for_each_union(self, func):
        retval = []
        for m in self.unions:
            retval.append(func(m))
        return retval

    @property
    def consts(self):
        return self._consts

    def const_by_name(self, name):
        for c in self.consts:
            if c.name == name:
                return c
        return None

    def for_each_const(self, func):
        retval = []
        for m in self.consts:
            retval.append(func(m))
        return retval


    @property
    def typedefs(self):
        return self._typedefs

    def typedef_by_name(self, name):
        for t in self.typedefs:
            if t.name == name:
                return t
        return None

    def for_each_typedef(self, func):
        retval = []
        for m in self.typedefs:
            retval.append(func(m))

    def find_types(self, full_typename, parent=None):
        if type.is_primitive(full_typename):
            return [type.IDLType(full_typename, self)]
        typenode = []

        def parse_node(s, name=str(full_typename)):
            if parent:
                if parent.full_path + '::' + name.strip() == s.full_path or name.strip() == s.full_path:
                    typenode.append(s)
            else:
                if s.name == name.strip() or s.full_path == name.strip():
                    typenode.append(s)

        def parse_module(m):
            m.for_each_module(parse_module)
            m.for_each_struct(parse_node)
            m.for_each_typedef(parse_node)
            m.for_each_enum(parse_node)
            m.for_each_bitmask(parse_node)
            m.for_each_bitset(parse_node)
            m.for_each_union(parse_node)
            m.for_each_interface(parse_node)

        parse_module(self)

        return typenode
