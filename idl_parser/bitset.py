"""IDL 4.2 bitset type (issue #39).

::

    bitset Header : BaseHeader {
        bitfield<3> kind;
        bitfield<1> a, b;          // several bitfields of the same size
        bitfield<4>;               // unnamed bitfield (padding)
        bitfield<8, short> level;  // explicit destination type
    };

Bitfields are laid out from the least significant bit in declaration order,
after the bits of the base bitset. A bitset holds at most 64 bits.
"""
import re

from . import node, exception
from .bitmask import parse_int, split_annotations
sep = '::'

MAX_BITS = 64

_bitfield = re.compile(r'^bitfield\s*<\s*([^,>]+?)\s*(?:,\s*([^>]+?)\s*)?>\s*(.*)$')


def default_bitfield_type(bits):
    """Destination type used when a bitfield does not specify one (IDL 4.2)."""
    if bits == 1:
        return 'boolean'
    elif bits <= 8:
        return 'octet'
    elif bits <= 16:
        return 'unsigned short'
    elif bits <= 32:
        return 'unsigned long'
    return 'unsigned long long'


class IDLBitfield(node.IDLNode):
    """A bitfield of a bitset. ``name`` is None for an unnamed bitfield."""

    def __init__(self, name, bits, typename, offset, parent):
        super(IDLBitfield, self).__init__('IDLBitfield', name, parent)
        self._bits = bits
        self._typename = typename
        self._offset = offset

    @property
    def bits(self):
        """Number of bits of this bitfield."""
        return self._bits

    @property
    def type(self):
        """Destination type name (given explicitly, or the IDL 4.2 default for its size)."""
        return self._typename if self._typename else default_bitfield_type(self._bits)

    @property
    def is_type_explicit(self):
        return self._typename is not None

    @property
    def position(self):
        """Position of the lowest bit within the bitset, counting the base bitset's bits."""
        return self.parent.base_bits + self._offset

    @property
    def mask(self):
        """Integer mask of this bitfield within the bitset."""
        return ((1 << self._bits) - 1) << self.position

    @property
    def full_path(self):
        return self.parent.full_path + sep + (self.name or '')

    def to_simple_dic(self):
        return {(self.name or ''): 'bitfield<%d, %s>' % (self.bits, self.type)}

    def to_dic(self):
        return {'name': self.name,
                'classname': self.classname,
                'bits': self.bits,
                'type': self.type,
                'position': self.position}


class IDLBitset(node.IDLNode):

    def __init__(self, name, parent):
        super(IDLBitset, self).__init__('IDLBitset', name, parent)
        self._verbose = False
        self._bitfields = []
        self._base = None
        self._own_bits = 0

    @property
    def full_path(self):
        return self.parent.full_path + sep + self.name

    @property
    def base(self):
        """Base bitset (:class:`IDLBitset`), or None."""
        return self._base

    @property
    def base_bits(self):
        """Number of bits taken by the base bitset(s)."""
        return self._base.bit_size if self._base else 0

    @property
    def bit_size(self):
        """Total number of bits, including the base bitset and unnamed bitfields."""
        return self.base_bits + self._own_bits

    @property
    def bitfields(self):
        """All bitfields of this bitset (not of the base), including unnamed ones."""
        return self._bitfields

    @property
    def members(self):
        """Named bitfields, base bitset's first."""
        own = [b for b in self._bitfields if b.name]
        return (self._base.members if self._base else []) + own

    def bitfield_by_name(self, name):
        for b in self.members:
            if b.name == name:
                return b
        return None

    def to_simple_dic(self, quiet=False, full_path=False, recursive=False, member_only=False):
        name = self.full_path if full_path else self.name
        if quiet:
            return 'bitset %s' % name
        fields = [b.to_simple_dic() for b in self.members]
        if member_only:
            return fields
        return {'bitset %s' % name: fields}

    def to_dic(self):
        return {'name': self.name,
                'filepath': self.filepath,
                'classname': self.classname,
                'base': self._base.full_path if self._base else None,
                'bit_size': self.bit_size,
                'bitfields': [b.to_dic() for b in self.bitfields]}

    def parse_tokens(self, token_buf, filepath=None):
        self._filepath = filepath
        ln, fn, token = token_buf.pop()
        if token == ':':
            ln, fn, base_name = token_buf.pop()
            self._base = self._find_base(base_name, ln, fn)
            ln, fn, token = token_buf.pop()
        if token != '{':
            raise exception.InvalidIDLSyntaxError(ln, fn, 'No "{" in the declaration of bitset "%s"' % self.name)

        block = []
        while True:
            ln, fn, token = token_buf.pop()
            if token is None:
                raise exception.InvalidIDLSyntaxError(ln, fn, 'No "}" in the declaration of bitset "%s"' % self.name)
            elif token == '}':
                if block:
                    raise exception.InvalidIDLSyntaxError(ln, fn, 'No ";" after "%s" in bitset "%s"' % (' '.join(block), self.name))
                ln, fn, token = token_buf.pop()
                if token != ';':
                    raise exception.InvalidIDLSyntaxError(ln, fn, 'No ";" after "}" in the declaration of bitset "%s"' % self.name)
                break
            elif token == ';':
                self._parse_bitfield(block, ln, fn)
                block = []
            else:
                block.append(token)

    def _parse_bitfield(self, block, ln, fn):
        _, rest = split_annotations(block)
        decl = ' '.join(rest)
        m = _bitfield.match(decl)
        if not m:
            raise exception.InvalidIDLSyntaxError(ln, fn, 'Invalid bitfield "%s" in bitset "%s"' % (decl, self.name))
        size_literal, typename, names = m.group(1), m.group(2), m.group(3)

        bits = parse_int(size_literal)
        if bits is None:
            const = self._find_const(size_literal)
            bits = parse_int(str(const.value)) if const else None
        if bits is None or not 1 <= bits <= MAX_BITS:
            raise exception.InvalidIDLSyntaxError(ln, fn, 'Invalid size "%s" of bitfield in bitset "%s"' % (size_literal, self.name))
        if typename:
            typename = ' '.join(typename.split())

        names = [n.strip() for n in names.split(',')] if names.strip() else [None]
        for n in names:
            if n == '':
                raise exception.InvalidIDLSyntaxError(ln, fn, 'Invalid bitfield "%s" in bitset "%s"' % (decl, self.name))
            b = IDLBitfield(n, bits, typename, self._own_bits, self)
            b._filepath = self.filepath
            self._bitfields.append(b)
            self._own_bits += bits

        if self.bit_size > MAX_BITS:
            raise exception.InvalidIDLSyntaxError(
                ln, fn, 'Bitset "%s" has %d bits (must be %d or less)' % (self.name, self.bit_size, MAX_BITS))

    def _scopes(self, name):
        """Candidate full names (without leading '::'), innermost scope first."""
        if name.startswith(sep):
            return [name[len(sep):]]
        candidates = []
        scope = self.parent
        while scope is not None:
            prefix = scope.full_path.lstrip(':')
            candidates.append(prefix + sep + name if prefix else name)
            scope = scope.parent
        return candidates

    def _find_base(self, name, ln, fn):
        bitsets = {}
        def collect(m):
            for b in m.bitsets:
                bitsets[b.full_path.lstrip(':')] = b
            for sub in m.modules:
                collect(sub)
        collect(self.root_node)
        for c in self._scopes(name):
            if c in bitsets:
                return bitsets[c]
        raise exception.IDLCanNotFindException(
            ln, fn, 'Can not find "%s" bitset which is the base of "%s"' % (name, self.name))

    def _find_const(self, name):
        consts = {}
        def collect(m):
            for c in m.consts:
                consts[(m.full_path.lstrip(':') + sep + c.name).lstrip(':')] = c
            for sub in m.modules:
                collect(sub)
        collect(self.root_node)
        for c in self._scopes(name):
            if c in consts:
                return consts[c]
        return None
