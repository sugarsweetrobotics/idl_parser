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


class TokenBuffer():

    def __init__(self, lines):
        self._tokens = []
        self._token_offset = 0
        for line_number, file_name, line in lines:
            for t in split_tokens(line):
                self._tokens.append((line_number, file_name, t))

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
