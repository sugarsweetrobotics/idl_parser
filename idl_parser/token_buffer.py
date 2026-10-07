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
    that starts with ``]`` or ``>`` is joined with the previous one. String
    and character literals are never joined, so the spaces in
    ``"[ x ]"`` are kept (issue #53). The joined token keeps the line
    number of its first part.
    """
    out = []
    join_next = False
    for line_number, file_name, t in tokens:
        literal = _is_literal(t)
        if out and not literal and not _is_literal(out[-1][2]) and \
                (join_next or t[0] in ']>'):
            ln, fn, prev = out[-1]
            out[-1] = (ln, fn, prev + t)
        else:
            out.append((line_number, file_name, t))
        last = out[-1][2]
        join_next = not _is_literal(last) and last[-1] in '[<'
    return out


class TokenBuffer():

    def __init__(self, lines):
        self._tokens = []
        self._token_offset = 0
        for line_number, file_name, line in lines:
            for t in split_tokens(line):
                self._tokens.append((line_number, file_name, t))
        self._tokens = join_brackets(self._tokens)

    @property
    def t_debug(self):
        return self._tokens

    def pop(self):
        if len(self._tokens) == self._token_offset:
            return (-1, '', None)
        t = self._tokens[self._token_offset]#.strip()
        self._token_offset = self._token_offset + 1
        return t

    def peek(self):
        """Return the next token without consuming it (same format as pop)."""
        if len(self._tokens) == self._token_offset:
            return (-1, '', None)
        return self._tokens[self._token_offset]
