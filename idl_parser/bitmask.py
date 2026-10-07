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
        return self.parent.full_path + sep + self.name

    def to_simple_dic(self):
        return {self.name: self.position}

    def to_dic(self):
        return {'name': self.name,
                'classname': self.classname,
                'position': self.position,
                'value': self.value}


class IDLBitmask(node.IDLNode):

    def __init__(self, name, parent, annotations=None):
        super(IDLBitmask, self).__init__('IDLBitmask', name, parent)
        self._verbose = False
        self._values = []
        self._bit_bound = DEFAULT_BIT_BOUND
        for aname, args in (annotations or []):
            if aname == 'bit_bound' and len(args) == 1:
                self._bit_bound = self._parse_bound(args[0])

    def _parse_bound(self, literal):
        bound = parse_int(literal)
        if bound is None or not 1 <= bound <= MAX_BIT_BOUND:
            raise exception.InvalidIDLSyntaxError(
                message='Invalid @bit_bound(%s) of bitmask "%s" (must be 1..%d)'
                % (literal, self.name, MAX_BIT_BOUND))
        return bound

    @property
    def full_path(self):
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
        for v in self._values:
            if v.name == name:
                return v
        return None

    def to_simple_dic(self, quiet=False, full_path=False, recursive=False, member_only=False):
        name = self.full_path if full_path else self.name
        if quiet:
            return 'bitmask %s' % name
        if member_only:
            return [v.to_simple_dic() for v in self.values]
        return {'bitmask %s' % name: [v.to_simple_dic() for v in self.values]}

    def to_dic(self):
        return {'name': self.name,
                'filepath': self.filepath,
                'classname': self.classname,
                'bit_bound': self.bit_bound,
                'values': [v.to_dic() for v in self.values]}

    def parse_tokens(self, token_buf, filepath=None):
        self._filepath = filepath
        ln, fn, token = token_buf.pop()
        if token != '{':
            raise exception.InvalidIDLSyntaxError(ln, fn, 'No "{" in the declaration of bitmask "%s"' % self.name)

        block = []
        while True:
            ln, fn, token = token_buf.pop()
            if token is None:
                raise exception.InvalidIDLSyntaxError(ln, fn, 'No "}" in the declaration of bitmask "%s"' % self.name)
            elif token == '}':
                if block:
                    self._parse_block(block, ln, fn)
                ln, fn, token = token_buf.pop()
                if token != ';':
                    raise exception.InvalidIDLSyntaxError(ln, fn, 'No ";" after "}" in the declaration of bitmask "%s"' % self.name)
                break
            elif token == ',':
                self._parse_block(block, ln, fn)
                block = []
            else:
                block.append(token)

    def _parse_block(self, block, ln, fn):
        # block: [annotation tokens...] NAME
        annotations, rest = split_annotations(block)
        if len(rest) != 1:
            raise exception.InvalidIDLSyntaxError(ln, fn, 'Invalid value "%s" in bitmask "%s"' % (' '.join(block), self.name))

        if self._values:
            position = self._values[-1].position + 1
        else:
            position = 0
        for aname, args in annotations:
            if aname == 'position' and len(args) == 1:
                position = parse_int(args[0])
                if position is None:
                    raise exception.InvalidIDLSyntaxError(ln, fn, 'Invalid @position(%s) in bitmask "%s"' % (args[0], self.name))

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
        self._values.append(v)


def split_annotations(tokens):
    """Split leading annotations off a token list.

    Returns ``([(name, [args...]), ...], remaining_tokens)``.
    ``['@position', '(', '3', ')', 'X']`` -> ``([('position', ['3'])], ['X'])``.
    """
    annotations = []
    i = 0
    while i < len(tokens) and tokens[i].startswith('@'):
        name = tokens[i][1:]
        args = []
        i += 1
        if i < len(tokens) and tokens[i] == '(':
            i += 1
            arg = []
            while i < len(tokens) and tokens[i] != ')':
                if tokens[i] == ',':
                    args.append(' '.join(arg))
                    arg = []
                else:
                    arg.append(tokens[i])
                i += 1
            if arg:
                args.append(' '.join(arg))
            i += 1  # ')'
        annotations.append((name, args))
    return annotations, tokens[i:]
