"""Splitting preprocessed IDL lines into tokens."""
def _literal_end(line, start):
    """Index just after the string or character literal starting at
    ``line[start]`` (a ``"`` or ``'``). A backslash escapes the next
    character, so ``"a\\"b"`` and ``'\\''`` are read as one literal.
    An unterminated literal runs to the end of the line."""
    quote = line[start]
    i = start + 1
    while i < len(line):
        c = line[i]
        if c == '\\':
            i = i + 2
        elif c == quote:
            return i + 1
        elif c in '\r\n':
            return i
        else:
            i = i + 1
    return len(line)


def split_tokens(line):
    """Split a line into tokens at whitespace, keeping each string or
    character literal whole, spaces included (issue #52).

    ``'const string S = "hello world" ;'`` gives
    ``['const', 'string', 'S', '=', '"hello world"', ';']``.
    Characters next to a literal with no space between, as in
    ``L"wide"``, stay in the same token.
    """
    tokens = []
    token = ''
    i = 0
    n = len(line)
    while i < n:
        c = line[i]
        if c in '"\'':
            end = _literal_end(line, i)
            token = token + line[i:end]
            i = end
        elif c.isspace():
            if token:
                tokens.append(token)
                token = ''
            i = i + 1
        else:
            token = token + c
            i = i + 1
    if token:
        tokens.append(token)
    return tokens


def _is_literal(token):
    return '"' in token or "'" in token


def join_brackets(tokens):
    """Join tokens across the spaces just inside ``[ ]`` and ``< >``,
    so that ``long a[ 5 ]`` and ``string< 8 >`` give ``a[5]`` and
    ``string<8>``, also when the brackets span lines.

    ``tokens`` is a list of ``(line_number, file_name, token)``. A token
    that ends with ``[`` or ``<`` is joined with the next one, and a token
    that starts with ``]`` or ``>`` is joined with the previous one, and the
    tokens between ``[`` and ``]`` are joined (``a[N * 2]`` gives
    ``a[N*2]``, issue #130). String
    and character literals are never joined, so the spaces in
    ``"[ x ]"`` are kept (issue #53). The joined token keeps the line
    number of its first part.
    """
    out = []
    join_next = False
    # A #pragma kept in place (issue #135) is not joined; it is put after
    # the token being joined, as if it were written after it
    held = []
    for line_number, file_name, t in tokens:
        if not isinstance(t, str):
            held.append((line_number, file_name, t))
            continue
        literal = _is_literal(t)
        if out and not literal and not _is_literal(out[-1][2]) and \
                (join_next or t[0] in ']>'):
            ln, fn, prev = out[-1]
            out[-1] = (ln, fn, prev + t)
        else:
            out.extend(held)
            held = []
            out.append((line_number, file_name, t))
        last = out[-1][2]
        # Inside "[ ]" the tokens of a size expression are joined too, so
        # that "a[N * 2]" gives "a[N*2]" (issue #130)
        join_next = not _is_literal(last) and \
            (last[-1] in '[<' or last.count('[') > last.count(']'))
    return out + held


class TokenBuffer():
    """The tokens of the input, read one by one by the parser.

    Each token is a ``(line_number, file_name, token)`` tuple. At the end of
    the input, :meth:`pop` and :meth:`peek` return ``(-1, '', None)``.

    A ``#pragma`` kept in place (an :class:`~idl_parser.pragma.IDLPragma`
    instead of a line, issue #135) is not a token: :meth:`pop` and
    :meth:`peek` skip it, and the pragmas that :meth:`pop` has gone past are
    returned by :meth:`take_pragmas`.

    :param lines: List of ``(line_number, file_name, line)`` tuples; ``line``
        may be an :class:`~idl_parser.pragma.IDLPragma`.
    """
    def __init__(self, lines):
        self._tokens = []
        self._token_offset = 0
        self._passed_pragmas = []
        for line_number, file_name, line in lines:
            if not isinstance(line, str):
                self._tokens.append((line_number, file_name, line))
                continue
            for t in split_tokens(line):
                self._tokens.append((line_number, file_name, t))
        self._tokens = join_brackets(self._tokens)

    @classmethod
    def from_tokens(cls, tokens):
        """A buffer holding ``tokens``, a list of ``(line_number, file_name, token)``
        tuples that are already split (issue #121)."""
        buf = cls([])
        buf._tokens = list(tokens)
        return buf

    @property
    def t_debug(self):
        """All the tokens, for debugging."""
        return self._tokens

    def pop(self):
        """Return the next token and consume it."""
        while len(self._tokens) > self._token_offset and \
                not isinstance(self._tokens[self._token_offset][2], str):
            self._passed_pragmas.append(self._tokens[self._token_offset][2])
            self._token_offset = self._token_offset + 1
        if len(self._tokens) == self._token_offset:
            return (-1, '', None)
        t = self._tokens[self._token_offset]#.strip()
        self._token_offset = self._token_offset + 1
        return t

    def peek(self, ahead=0):
        """Return the next token without consuming it (same format as pop).

        :param ahead: Number of tokens to look past; ``peek(1)`` returns the
            token after the next one.
        """
        i = self._token_offset
        while i < len(self._tokens):
            t = self._tokens[i]
            i = i + 1
            if not isinstance(t[2], str):
                continue
            if ahead == 0:
                return t
            ahead = ahead - 1
        return (-1, '', None)

    def take_pragmas(self):
        """The pragmas kept in place that :meth:`pop` has gone past since the
        last call, in order (issue #135)."""
        pragmas, self._passed_pragmas = self._passed_pragmas, []
        return pragmas
