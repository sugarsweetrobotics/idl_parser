"""IDL enums."""
import os, sys, traceback

from . import node, exception
sep = '::'

class IDLEnumValue(node.IDLNode):
    """An enumerator of an enum.

    :param value: Ordinal of the enumerator (0 for the first one).
    :param parent: The :class:`IDLEnum` it belongs to.
    """
    def __init__(self, value, parent):
        super(IDLEnumValue, self).__init__('IDLEnumValue', '', parent)
        self._verbose = True
        self._value = value

    def parse_blocks(self, blocks, filepath=None):
        """Read the enumerator from its tokens (annotations and the name)."""
        self._filepath = filepath
        annotations, blocks = node.parse_annotations(blocks)
        self._add_annotations(annotations)
        if len(blocks) == 1:
            self._name = blocks[0]
        else:
            sys.stdout.write('Unkown Enum format %s\n' % blocks)
        #name, type = self._name_and_type(blocks)
        #self._name = name
        #self._type = type

    @property
    def full_path(self):
        return self.full_path + '.' + self.name

    def to_simple_dic(self):
        """A compact summary: ``{name: value}``."""
        dic = {self.name : self.value }
        return dic

    def to_dic(self):
        """The enumerator as a plain dict (for JSON or YAML output)."""
        dic = { 'name' : self.name,
                'filepath' : self.filepath,
                'classname' : self.classname,
                'value' : self.value }
        return self._with_annotations(dic)
    @property
    def value(self):
        """Ordinal of the enumerator, counted from 0 in declaration order."""
        return self._value




class IDLEnum(node.IDLNode):
    """An ``enum`` and its enumerators.

    As in IDL, the enumerators belong to the scope enclosing the enum
    (``module M { enum E { A }; };`` defines ``M::A``).

    :param name: Enum name.
    :param parent: Enclosing :class:`~idl_parser.module.IDLModule`.
    """
    def __init__(self, name, parent):
        super(IDLEnum, self).__init__('IDLEnum', name, parent)
        self._verbose = True
        self._values = []

    def to_simple_dic(self, quiet=False, full_path=False, recursive=False, member_only=False):
        """A compact summary: ``{'enum NAME': [{name: value}, ...]}``.

        :param quiet: Return only ``'enum NAME'``.
        :param full_path: Use :attr:`full_path` as the name.
        :param member_only: Return only the list of enumerator summaries.
        """
        name = self.full_path if full_path else self.name
        if quiet:
            return 'enum %s' % name
        dic = { 'enum %s' % name : [v.to_simple_dic() for v in self.values] }
        if member_only:
            return list(dic.values())[0]
        return dic


    def to_dic(self):
        """The enum as a plain dict (for JSON or YAML output)."""
        dic = { 'name' : self.name,
                'classname' : self.classname,
                'values' : [v.to_dic() for v in self.values] }
        return self._with_annotations(dic)

    @property
    def full_path(self):
        """Scoped name (``'M::E'``; ``'::E'`` at the global scope)."""
        return self.parent.full_path + sep + self.name

    def parse_tokens(self, token_buf, filepath=None):
        """Parse the enum from ``token_buf``, starting after its name, up to ``};``.

        :raises ~idl_parser.exception.InvalidIDLSyntaxError: The declaration is
            not valid IDL.
        """
        self._filepath = filepath
        self._counter = 0
        ln, fn, kakko = token_buf.pop()
        if not kakko == '{':
            if self._verbose: sys.stdout.write('# Error. No kakko "{".\n')
            raise exception.InvalidIDLSyntaxError()

        block_tokens = []
        depth = 0  # inside the parentheses of an annotation, e.g. @foo(a, b)
        while True:
            ln, fn, token = token_buf.pop()
            if token == None:
                if self._verbose: sys.stdout.write('# Error. No kokka "}".\n')
                raise exception.InvalidIDLSyntaxError()

            elif token == '(':
                depth += 1
            elif token == ')':
                depth -= 1

            if token == '}' and depth == 0:
                ln, fn, token = token_buf.pop()
                if not token == ';':
                    if self._verbose: sys.stdout.write('# Error. No semi-colon after "}".\n')
                    raise exception.InvalidIDLSyntaxError()

                if len(block_tokens) > 0:
                    self._parse_block(block_tokens)
                break

            if token == ',' and depth == 0:
                self._parse_block(block_tokens)
                block_tokens = []
                continue
            block_tokens.append(token)

    def _parse_block(self, blocks):
        v = IDLEnumValue(self._counter, self)
        self._counter = self._counter+ 1
        v.parse_blocks(blocks, self.filepath)
        self._values.append(v)

    @property
    def values(self):
        """Enumerators (list of :class:`IDLEnumValue`), in order."""
        return self._values


    def value_by_name(self, name):
        """The enumerator named ``name``, or None."""
        for m in self.values:
            if m.name == name:
                return m
        return None
