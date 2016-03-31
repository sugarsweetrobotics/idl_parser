

class TokenBuffer():
    
    def __init__(self, lines):
        self._tokens = []
        self._token_offset = 0
        for line in lines:
            ts = line.split(' ')
            for t in ts:
                if len(t.strip()) != 0:
                    self._tokens.append(t.strip())

    @property
    def t_debug(self):
        return self._tokens

    def pop(self):
        if len(self._tokens) == self._token_offset:
            return None
        t = self._tokens[self._token_offset].strip()
        self._token_offset = self._token_offset + 1
        return t.strip()

    
