import sys
from . import node
from . import exception

from . import type as idl_type

sep = '::'

class IDLArgument(node.IDLNode):
    def __init__(self, parent):
        super(IDLArgument, self).__init__('IDLArgument', '', parent)
        self._verbose = True
        self._dir = 'in'
        self._type = None

    def parse_blocks(self, blocks, filepath=None):
        self._filepath= filepath
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
        dic = '%s %s %s' % (self.direction, self.type, self.name)
        return dic

    def to_dic(self):
        dic = { 'name' : self.name,
                'classname' : self.classname,
                'type' : str(self.type),
                'direction' : self.direction,
                'filepath' : self.filepath }
        return dic

    @property
    def direction(self):
        return self._dir

    @property
    def type(self):
        return self._type

    def post_process(self):
        self._type._name = self.refine_typename(self.type)



class IDLMethod(node.IDLNode):
    def __init__(self, parent):
        super(IDLMethod, self).__init__('IDLValue', '', parent)
        self._verbose = True
        self._returns = None
        self._arguments = []

    def parse_blocks(self, blocks, filepath=None):
        self._filepath=filepath

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

        index = 3
        argument_blocks = []
        while True:
            if index == len(blocks):
                break
            token = blocks[index]
            if token == ',' or token == ')':
                if len(argument_blocks) == 0:
                    break

                a = IDLArgument(self)
                self._arguments.append(a)
                a.parse_blocks(argument_blocks, self.filepath)

                argument_blocks = []
            else:
                argument_blocks.append(token)
            index = index + 1

    def to_simple_dic(self):
        return {self.name : {
                'returns' : str(self.returns),
                'params' : [a.to_simple_dic() for a in self.arguments]}}

    def to_dic(self):
        dic = { 'name' : self.name,
                'filepath' : self.filepath,
                'classname' : self.classname,
                'returns' : str(self._returns),
                'arguments' : [a.to_dic() for a in self.arguments]}
        return dic

    @property
    def returns(self):
        return self._returns

    @property
    def arguments(self):
        return self._arguments

    def argument_by_name(self, name):
        for a in self.arguments:
            if a.name == name:
                return a

        return None


    def forEachArgument(self, func):
        for a in self.arguments:
            func(a)

    def post_process(self):
        #self._returns = self.refine_typename(self.returns)
        #self.forEachArgument(lambda a : a.post_process())
        pass

class IDLInterface(node.IDLNode):

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
        return self.parent.full_path + sep + self.name

    def to_simple_dic(self, quiet=False, full_path=False, recursive=False, member_only=False):
        if quiet:
            return 'interface %s' % self.name
        dic = { 'interface ' + self.name : [m.to_simple_dic() for m in self.methods] }
        return dic

    def to_dic(self):
        dic = { 'name' : self.name,
                'filepath' : self.filepath,
                'classname' : self.classname,
                'inheritances' : [i.full_path for i in self.inheritances],
                'methods' : [m.to_dic() for m in self.methods] }
        return dic

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
        return self._methods

    def method_by_name(self, name):
        for m in self.methods:
            if name == m.name:
                return m
        return None

    def forEachMethod(self, func):
        for m in self.methods:
            func(m)


