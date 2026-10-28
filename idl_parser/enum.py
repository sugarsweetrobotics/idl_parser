"""IDL enums."""
import os, sys, traceback

from . import node, exception
from .bitmask import parse_int
sep = '::'

# Enumerators are 32-bit signed integers (IDL 4.2 7.4.13.4.3.4 / XTypes).
MIN_VALUE = -2**31
MAX_VALUE = 2**31 - 1

class IDLEnumValue(node.IDLNode):
    """An enumerator of an enum.

    :param value: Value of the enumerator: ``@value(n)`` if written,
        otherwise the previous enumerator's value plus 1 (0 for the first one).
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
            node.check_identifier(blocks[0], 'enumerator of enum "%s"' % self.parent.name)
            self._name = blocks[0]
        else:
            sys.stdout.write('Unkown Enum format %s\n' % blocks)
        #name, type = self._name_and_type(blocks)
        #self._name = name
        #self._type = type

    @property
    def full_path(self):
        """Scoped name (``'M::A'``; ``'::A'`` at the global scope).

        As in IDL, the enumerator belongs to the scope enclosing its enum, so
        the enum name is not part of the path.
        """
        return self.parent.parent.full_path + sep + self.name

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
        """Value of the enumerator.

        ``@value(n)`` sets it; an enumerator without ``@value`` takes the
        previous enumerator's value plus 1 (0 for the first one), so with no
        ``@value`` at all it is the ordinal in declaration order.
        """
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
            not valid IDL, or a ``@value`` is not an integer (literal or
            ``const``), is out of the 32-bit signed range or is used twice.
        """
        self._filepath = filepath
        ln, fn, kakko = token_buf.pop()
        if not kakko == '{':
            if self._verbose: sys.stdout.write('# Error. No kakko "{".\n')
            raise exception.InvalidIDLSyntaxError()

        block_tokens = []
        block_ln, block_fn = None, None  # where the enumerator starts
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
                    self._parse_block(block_tokens, block_ln, block_fn)
                break

            if token == ',' and depth == 0:
                self._parse_block(block_tokens, block_ln, block_fn)
                block_tokens = []
                continue
            if not block_tokens:
                block_ln, block_fn = ln, fn
            block_tokens.append(token)

    def _parse_block(self, blocks, ln=None, fn=None):
        v = IDLEnumValue(None, self)
        v.parse_blocks(blocks, self.filepath)
        a = v.annotation_by_name('value')
        if a is not None:
            value = self._parse_value(a, v.name, ln, fn)
        elif self._values:
            value = self._values[-1].value + 1
        else:
            value = 0
        if not MIN_VALUE <= value <= MAX_VALUE:
            raise exception.InvalidIDLSyntaxError(
                ln, fn, 'Value %d of "%s" is out of range of enum "%s" (must be %d..%d)'
                % (value, v.name, self.name, MIN_VALUE, MAX_VALUE))
        for other in self._values:
            if other.value == value:
                raise exception.InvalidIDLSyntaxError(
                    ln, fn, 'Value %d of "%s" is already used by "%s" in enum "%s"'
                    % (value, v.name, other.name, self.name))
        v._value = value
        self._values.append(v)
        node.check_unique_names([e.name for e in self._values], 'enum "%s"' % self.name, ln, fn)

    def _parse_value(self, annotation, name, ln, fn):
        """Integer of ``@value(n)``: an integer literal or the name of a ``const``."""
        literal = annotation.value
        value = parse_int(literal)
        if value is None and literal:
            const = self._find_const(literal)
            value = parse_int(str(const.value)) if const else None
        if value is None:
            raise exception.InvalidIDLSyntaxError(
                ln, fn, 'Invalid %s of "%s" in enum "%s"' % (annotation, name, self.name))
        return value

    def _find_const(self, name):
        from .module import definition_scopes
        consts = {}
        for m in definition_scopes(self.root_node, self):
            for c in m.consts:
                consts[(m.full_path.lstrip(':') + sep + c.name).lstrip(':')] = c
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
            if c in consts:
                return consts[c]
        return None

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
