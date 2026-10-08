"""IDL 4.2 bitmask type (issue #39).

::

    @bit_bound(8) bitmask Flags { FLAG_A, @position(4) FLAG_B, FLAG_C };

Each value is a single bit. Positions start at 0 and follow the previous
value unless given with ``@position(n)``. ``@bit_bound`` (default 32) is the
number of bits the bitmask can hold.
"""

from . import node, exception
sep = '::'

DEFAULT_BIT_BOUND = 32
MAX_BIT_BOUND = 64


def parse_int(literal):
    """Integer value of an IDL integer literal (decimal, hex 0x.., octal 0..)."""
    try:
        return int(literal, 0)
    except (TypeError, ValueError):
        try:
            return int(literal, 8)  # e.g. '010' (IDL octal)
        except (TypeError, ValueError):
            return None


class IDLBitValue(node.IDLNode):
    """A value (flag) of a bitmask."""

    def __init__(self, name, position, parent):
        super(IDLBitValue, self).__init__('IDLBitValue', name, parent)
        self._position = position

    @property
    def position(self):
        """Bit position of this flag (0 is the least significant bit)."""
        return self._position

    @property
    def value(self):
        """Integer value of this flag (``1 << position``)."""
        return 1 << self._position

    @property
    def full_path(self):
        """Scoped name (``'M::Flags::FLAG_A'``)."""
        return self.parent.full_path + sep + self.name

    def to_simple_dic(self):
        """A compact summary: ``{name: position}``."""
        return {self.name: self.position}

    def to_dic(self):
        """The value as a plain dict (for JSON or YAML output)."""
        return self._with_annotations({'name': self.name,
                'classname': self.classname,
                'position': self.position,
                'value': self.value})


class IDLBitmask(node.IDLNode):
    """A ``bitmask`` and its values.

    :param name: Bitmask name.
    :param parent: Enclosing :class:`~idl_parser.module.IDLModule`.
    :param annotations: Annotations written before the bitmask; ``@bit_bound``
        sets :attr:`bit_bound`.
    :raises ~idl_parser.exception.InvalidIDLSyntaxError: ``@bit_bound`` is not
        in 1..64.
    """
    def __init__(self, name, parent, annotations=None):
        super(IDLBitmask, self).__init__('IDLBitmask', name, parent)
        self._verbose = False
        self._values = []
        self._bit_bound = DEFAULT_BIT_BOUND
        self._add_annotations(annotations or [])
        a = self.annotation_by_name('bit_bound')
        if a is not None:
            self._bit_bound = self._parse_bound(a.value)

    def _parse_bound(self, literal):
        bound = parse_int(literal)
        if bound is None or not 1 <= bound <= MAX_BIT_BOUND:
            raise exception.InvalidIDLSyntaxError(
                message='Invalid @bit_bound(%s) of bitmask "%s" (must be 1..%d)'
                % (literal, self.name, MAX_BIT_BOUND))
        return bound

    @property
    def full_path(self):
        """Scoped name (``'M::Flags'``; ``'::Flags'`` at the global scope)."""
        return self.parent.full_path + sep + self.name

    @property
    def bit_bound(self):
        """Number of bits the bitmask can hold (``@bit_bound``, default 32)."""
        return self._bit_bound

    @property
    def values(self):
        """Flags in declaration order (list of :class:`IDLBitValue`)."""
        return self._values

    def value_by_name(self, name):
        """The value named ``name`` (an :class:`IDLBitValue`), or None."""
        for v in self._values:
            if v.name == name:
                return v
        return None

    def to_simple_dic(self, quiet=False, full_path=False, recursive=False, member_only=False):
        """A compact summary: ``{'bitmask NAME': [{name: position}, ...]}``.

        :param quiet: Return only ``'bitmask NAME'``.
        :param full_path: Use :attr:`full_path` as the name.
        :param member_only: Return only the list of value summaries.
        """
        name = self.full_path if full_path else self.name
        if quiet:
            return 'bitmask %s' % name
        if member_only:
            return [v.to_simple_dic() for v in self.values]
        return {'bitmask %s' % name: [v.to_simple_dic() for v in self.values]}

    def to_dic(self):
        """The bitmask as a plain dict (for JSON or YAML output)."""
        return self._with_annotations({'name': self.name,
                'filepath': self.filepath,
                'classname': self.classname,
                'bit_bound': self.bit_bound,
                'values': [v.to_dic() for v in self.values]})

    def parse_tokens(self, token_buf, filepath=None):
        """Parse the bitmask from ``token_buf``, starting after its name, up to ``};``.

        :raises ~idl_parser.exception.InvalidIDLSyntaxError: The declaration is
            not valid IDL, or a position is out of :attr:`bit_bound` or used twice.
        """
        self._filepath = filepath
        ln, fn, token = token_buf.pop()
        if token != '{':
            raise exception.InvalidIDLSyntaxError(ln, fn, 'No "{" in the declaration of bitmask "%s"' % self.name)

        block = []
        depth = 0  # inside the parentheses of an annotation, e.g. @foo(a, b)
        while True:
            ln, fn, token = token_buf.pop()
            if token is None:
                raise exception.InvalidIDLSyntaxError(ln, fn, 'No "}" in the declaration of bitmask "%s"' % self.name)
            elif token == '}' and depth == 0:
                if block:
                    self._parse_block(block, ln, fn)
                ln, fn, token = token_buf.pop()
                if token != ';':
                    raise exception.InvalidIDLSyntaxError(ln, fn, 'No ";" after "}" in the declaration of bitmask "%s"' % self.name)
                break
            elif token == ',' and depth == 0:
                self._parse_block(block, ln, fn)
                block = []
            else:
                if token == '(':
                    depth += 1
                elif token == ')':
                    depth -= 1
                block.append(token)

    def _parse_block(self, block, ln, fn):
        # block: [annotation tokens...] NAME
        annotations, rest = node.parse_annotations(block)
        if len(rest) != 1:
            raise exception.InvalidIDLSyntaxError(ln, fn, 'Invalid value "%s" in bitmask "%s"' % (' '.join(block), self.name))

        if self._values:
            position = self._values[-1].position + 1
        else:
            position = 0
        for a in annotations:
            if a.name == 'position':
                position = parse_int(a.value)
                if position is None:
                    raise exception.InvalidIDLSyntaxError(ln, fn, 'Invalid %s in bitmask "%s"' % (a, self.name))

        if not 0 <= position < self.bit_bound:
            raise exception.InvalidIDLSyntaxError(
                ln, fn, 'Position %s of "%s" is out of @bit_bound(%d) of bitmask "%s"'
                % (position, rest[0], self.bit_bound, self.name))
        for v in self._values:
            if v.position == position:
                raise exception.InvalidIDLSyntaxError(
                    ln, fn, 'Position %d of "%s" is already used by "%s" in bitmask "%s"'
                    % (position, rest[0], v.name, self.name))

        v = IDLBitValue(rest[0], position, self)
        v._filepath = self.filepath
        v._add_annotations(annotations)
        self._values.append(v)

