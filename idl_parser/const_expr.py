"""Evaluating integer constant expressions (``const_expr`` of IDL 4.2, issue #130).

Array sizes, the bounds of ``string<>``, ``wstring<>``, ``sequence<>`` and
``map<>``, and the values of integer ``const`` definitions are constant
expressions such as ``N * 2`` or ``(1 << 4) - 1``. :func:`evaluate` gives
their integer value.

The operators are ``|`` ``^`` ``&`` ``<<`` ``>>`` ``+`` ``-`` ``*`` ``/``
``%`` and the unary ``-`` ``+`` ``~``, with the precedence of IDL (and C++),
and parentheses. The operands are integer literals (decimal, octal ``017``
and hexadecimal ``0x1F``) and the names of integer constants, scoped names
(``M::N``, ``::N``) included. As in C++, ``/`` rounds toward zero and the
result of ``%`` has the sign of the left operand.
"""
import re

from .exception import InvalidConstExpressionError

sep = '::'

# Integer types whose const values are evaluated (typedefs of them included)
integer_types = frozenset((
    'short', 'long', 'long long',
    'unsigned short', 'unsigned long', 'unsigned long long',
    'octet', 'int8', 'int16', 'int32', 'int64',
    'uint8', 'uint16', 'uint32', 'uint64'))

_token = re.compile(r'\s*(?:'
                    r'(?P<number>0[xX][0-9A-Fa-f]+|[0-9]+)'
                    r'|(?P<name>(?:::)?[A-Za-z_][A-Za-z0-9_]*(?:::[A-Za-z_][A-Za-z0-9_]*)*)'
                    r'|(?P<op><<|>>|[|^&+\-*/%~()]))')

# Binary operators, loosest first (or_expr ... mult_expr of IDL 4.2)
_binary_levels = (('|',), ('^',), ('&',), ('<<', '>>'), ('+', '-'), ('*', '/', '%'))


class ConstExprError(Exception):
    """An expression that is not an integer constant expression."""


def _tokenize(expr):
    tokens = []
    pos = 0
    text = expr.rstrip()
    while pos < len(text):
        m = _token.match(text, pos)
        if not m or m.end() == pos:
            raise ConstExprError('Unexpected "%s"' % text[pos:].strip())
        pos = m.end()
        if m.group('number') is not None:
            tokens.append(('number', m.group('number')))
        elif m.group('name') is not None:
            tokens.append(('name', m.group('name')))
        else:
            tokens.append(('op', m.group('op')))
    return tokens


def parse_int_literal(literal):
    """Value of an IDL integer literal (``10``, ``017``, ``0x1F``), or None."""
    literal = literal.strip()
    if re.match(r'^0[xX][0-9A-Fa-f]+$', literal):
        return int(literal, 16)
    if re.match(r'^0[0-7]*$', literal):
        return int(literal, 8)
    if re.match(r'^[1-9][0-9]*$', literal):
        return int(literal)
    return None


def _div(a, b):
    if b == 0:
        raise ConstExprError('Division by zero')
    q = abs(a) // abs(b)
    return q if (a < 0) == (b < 0) else -q


def _mod(a, b):
    return a - b * _div(a, b)


def _shift(a, b, left):
    if not 0 <= b < 64:
        raise ConstExprError('Shift count %d is out of range (must be 0..63)' % b)
    return a << b if left else a >> b


_apply = {
    '|': lambda a, b: a | b,
    '^': lambda a, b: a ^ b,
    '&': lambda a, b: a & b,
    '<<': lambda a, b: _shift(a, b, True),
    '>>': lambda a, b: _shift(a, b, False),
    '+': lambda a, b: a + b,
    '-': lambda a, b: a - b,
    '*': lambda a, b: a * b,
    '/': _div,
    '%': _mod,
}


class _Parser(object):
    def __init__(self, tokens, lookup):
        self._tokens = tokens
        self._pos = 0
        self._lookup = lookup

    def _peek(self):
        return self._tokens[self._pos] if self._pos < len(self._tokens) else (None, None)

    def _pop(self):
        t = self._peek()
        self._pos += 1
        return t

    def parse(self):
        value = self._binary(0)
        kind, text = self._peek()
        if kind is not None:
            raise ConstExprError('Unexpected "%s"' % text)
        return value

    def _binary(self, level):
        if level == len(_binary_levels):
            return self._unary()
        value = self._binary(level + 1)
        while True:
            kind, text = self._peek()
            if kind != 'op' or text not in _binary_levels[level]:
                return value
            self._pop()
            value = _apply[text](value, self._binary(level + 1))

    def _unary(self):
        kind, text = self._peek()
        if kind == 'op' and text in ('-', '+', '~'):
            self._pop()
            value = self._unary()
            return -value if text == '-' else (~value if text == '~' else value)
        return self._primary()

    def _primary(self):
        kind, text = self._pop()
        if kind == 'number':
            value = parse_int_literal(text)
            if value is None:
                raise ConstExprError('Invalid integer literal "%s"' % text)
            return value
        if kind == 'name':
            return self._lookup(text)
        if kind == 'op' and text == '(':
            value = self._binary(0)
            kind, text = self._pop()
            if (kind, text) != ('op', ')'):
                raise ConstExprError('No ")"')
            return value
        if kind is None:
            raise ConstExprError('Missing operand')
        raise ConstExprError('Unexpected "%s"' % text)


def find_const(name, scope):
    """The ``const`` named ``name`` (``N``, ``M::N`` or ``::M::N``) as seen
    from ``scope``, the node where the name is written, or None.

    The scopes enclosing ``scope`` are searched innermost first, as for type
    names.
    """
    from .module import definition_scopes
    root = scope.root_node
    consts = {}
    for m in definition_scopes(root, scope):
        for c in m.consts:
            consts.setdefault((m.full_path.lstrip(':') + sep + c.name).lstrip(':'), c)
    name = name.strip()
    if name.startswith(sep):
        candidates = [name[len(sep):]]
    else:
        candidates = []
        n = scope
        while n is not None:
            prefix = n.full_path.lstrip(':') if n.parent is not None else ''
            candidates.append(prefix + sep + name if prefix else name)
            n = n.parent
    for c in candidates:
        if c in consts:
            return consts[c]
    if sep not in name:
        # As before issue #130: a constant in the last module, then in the
        # global scope, also when it is not in a scope enclosing ``scope``
        if root.modules and root.modules[-1].const_by_name(name):
            return root.modules[-1].const_by_name(name)
        return root.const_by_name(name)
    return None


def evaluate(expr, scope):
    """Integer value of the constant expression ``expr`` written in ``scope``.

    :param expr: The expression as written (``'N * 2'``); an int is returned as is.
    :param scope: The node where the expression is written; constant names
        are looked up from it (:func:`find_const`).
    :raises ConstExprError: ``expr`` is not an integer constant expression,
        or names a constant that is not defined or not an integer.
    """
    if isinstance(expr, int):
        return expr

    def lookup(name):
        c = find_const(name, scope)
        if c is None:
            raise ConstExprError('Constant "%s" is not defined' % name)
        value = c.int_value
        if value is None:
            raise ConstExprError('Constant "%s" is not an integer' % name)
        return value

    tokens = _tokenize(str(expr))
    if not tokens:
        raise ConstExprError('Empty expression')
    return _Parser(tokens, lookup).parse()


def evaluate_positive(expr, scope, what, ln=None, fn=None):
    """Value of ``expr`` (:func:`evaluate`), which must be a positive integer.

    :param what: What the value is (``'array size'``), for the error message.
    :raises ~idl_parser.exception.InvalidConstExpressionError: The value is not a
        positive integer.
    """
    try:
        value = evaluate(expr, scope)
    except ConstExprError as e:
        raise InvalidConstExpressionError(ln, fn, 'Invalid %s "%s": %s' % (what, expr, e))
    if value <= 0:
        raise InvalidConstExpressionError(ln, fn, 'Invalid %s "%s": %d is not a positive integer'
                                    % (what, expr, value))
    return value
