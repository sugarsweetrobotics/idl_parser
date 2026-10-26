"""Conditional directives and macros of the preprocessor (issue #120).

IDL is preprocessed like C++ (IDL 4.2, 7.3). After comments are removed and
``#include`` files are pasted, :func:`preprocess` applies

- ``#define NAME`` / ``#define NAME value`` and ``#undef NAME``,
- ``#ifdef`` / ``#ifndef`` / ``#if`` / ``#elif`` / ``#else`` / ``#endif``,
- ``#error`` (an :class:`~idl_parser.exception.InvalidIDLSyntaxError`) and
  ``#warning`` (a :class:`PreprocessorWarning`),

and expands object-like macros in the remaining lines, so that
``#define N 5`` makes ``long a[N];`` an array of 5 elements.

An ``#if`` / ``#elif`` expression is an integer expression as in C:
integers (decimal, octal, hexadecimal, with ``u`` / ``l`` suffixes),
character literals, ``defined NAME`` / ``defined(NAME)``, the unary
operators ``! ~ - +``, the binary operators ``* / % + - << >> < > <= >=
== != & ^ | && ||``, ``? :`` and parentheses. Macros are expanded first,
and a name that is still left counts as 0 (``true`` is 1 and ``false`` is
0).

Function-like macros (``#define F(x) ...``) are defined, so ``defined(F)``
is true, but they are not expanded; a :class:`PreprocessorWarning` is
issued for each. Other directives (``#pragma``, ``#line``, ...) are kept.
"""
import re
import warnings

from . import exception


class PreprocessorWarning(exception.IDLParserWarning):
    """``#warning`` was found, or a function-like macro (not expanded) was
    defined."""
    pass


# Directive lines whose text is kept as written by the comment remover:
# the punctuation of an expression or of a macro body must not be split.
DIRECTIVES = ('define', 'undef', 'if', 'ifdef', 'ifndef', 'elif', 'else',
              'endif', 'error', 'warning')

_DIRECTIVE_RE = re.compile(r'^#\s*([A-Za-z_]\w*)\b\s*(.*?)\s*$', re.S)
_NAME_RE = re.compile(r'[A-Za-z_]\w*')

# Pieces of a line for macro expansion: literals and numbers are copied,
# names may be expanded.
_LINE_TOKEN_RE = re.compile(r'''
      (?P<str>L?"(?:\\.|[^"\\])*"?)
    | (?P<chr>L?'(?:\\.|[^'\\])*'?)
    | (?P<num>\.?\d(?:[eEpP][+-]|[\w.])*)
    | (?P<name>[A-Za-z_]\w*)
''', re.X)

_EXPR_TOKEN_RE = re.compile(r'''
      (?P<ws>\s+)
    | (?P<num>(?:0[xX][0-9a-fA-F]+|\d+)[uUlL]*)
    | (?P<chr>'(?:\\.|[^'\\])+')
    | (?P<name>[A-Za-z_]\w*)
    | (?P<op>&&|\|\||<<|>>|<=|>=|==|!=|[-+*/%<>!~&|^?:()])
''', re.X)


def is_directive_line(line):
    """True if ``line`` (of raw text) is one of the :data:`DIRECTIVES`."""
    m = _DIRECTIVE_RE.match(line.strip())
    return m is not None and m.group(1) in DIRECTIVES


class _Macro(object):
    def __init__(self, name, body, function_like):
        self.name = name
        self.body = body
        self.function_like = function_like


class Preprocessor(object):
    """Applies conditional directives and expands macros.

    :param format_code: Function that puts spaces around punctuation of an
        expanded macro body, so that it is split into tokens like the rest
        of the line.
    """

    def __init__(self, format_code=None):
        self._macros = {}
        self._format_code = format_code if format_code is not None else (lambda s: s)

    @property
    def macros(self):
        """Defined macros: a dict of name to body (``''`` for ``#define X``).
        A function-like macro is included with its parameters and body as
        written (``'(a, b) a + b'``)."""
        return dict((n, m.body) for n, m in self._macros.items())

    def preprocess(self, lines):
        """Process a list of ``(line_number, file_name, line)`` tuples and
        return the lines that are kept, with macros expanded.

        :raises ~idl_parser.exception.InvalidIDLSyntaxError: An ``#if`` /
            ``#elif`` expression is invalid, ``#else`` / ``#elif`` /
            ``#endif`` has no ``#if``, an ``#if`` has no ``#endif``, or an
            active ``#error`` was found.
        """
        output = []
        # One entry per open #if: [active, taken, seen_else, line_number, file_name]
        # "active": lines of the current branch are kept;
        # "taken": a branch of this #if has already been kept.
        stack = []
        i = 0
        while i < len(lines):
            line_number, file_name, line = lines[i]
            i += 1
            m = _DIRECTIVE_RE.match(line.strip())
            if m is None or m.group(1) not in DIRECTIVES:
                if all(s[0] for s in stack):
                    if m is None:
                        line = self.expand(line)
                    output.append((line_number, file_name, line))
                continue

            directive, rest = m.group(1), m.group(2)
            # A directive continues on the next line after a backslash.
            while rest.endswith('\\') and i < len(lines):
                rest = rest[:-1] + ' ' + lines[i][2].strip()
                i += 1
            rest = rest.rstrip('\\').strip()
            enclosing = all(s[0] for s in stack)

            def error(message):
                return exception.InvalidIDLSyntaxError(line_number, file_name, message)

            if directive in ('ifdef', 'ifndef'):
                name = self._name(rest, directive, error)
                value = (name in self._macros) == (directive == 'ifdef')
                active = enclosing and value
                stack.append([active, active, False, line_number, file_name])
            elif directive == 'if':
                active = enclosing and self._evaluate(rest, error)
                stack.append([active, active, False, line_number, file_name])
            elif directive == 'elif':
                if not stack:
                    raise error('#elif without #if')
                top = stack[-1]
                if top[2]:
                    raise error('#elif after #else')
                outer = all(s[0] for s in stack[:-1])
                if top[1] or not outer:
                    top[0] = False
                else:
                    top[0] = self._evaluate(rest, error)
                    top[1] = top[0]
            elif directive == 'else':
                if not stack:
                    raise error('#else without #if')
                top = stack[-1]
                if top[2]:
                    raise error('#else after #else')
                top[2] = True
                top[0] = all(s[0] for s in stack[:-1]) and not top[1]
                top[1] = True
            elif directive == 'endif':
                if not stack:
                    raise error('#endif without #if')
                stack.pop()
            elif not enclosing:
                pass  # #define, #error, ... in a branch that is skipped
            elif directive == 'define':
                self._define(rest, error, line_number, file_name)
            elif directive == 'undef':
                self._macros.pop(self._name(rest, directive, error), None)
            elif directive == 'error':
                raise error('#error %s' % rest if rest else '#error')
            elif directive == 'warning':
                warnings.warn(exception.IDLParserException(
                    line_number, file_name, '#warning %s' % rest).message,
                    PreprocessorWarning, stacklevel=2)

        if stack:
            _, _, _, line_number, file_name = stack[-1]
            raise exception.InvalidIDLSyntaxError(line_number, file_name,
                                                  '#if without #endif')
        return output

    def define(self, name, value=''):
        """Define an object-like macro, as ``#define name value`` does."""
        if _NAME_RE.fullmatch(name) is None:
            raise ValueError('Invalid macro name: %r' % (name,))
        self._macros[name] = _Macro(name, self._format_body(str(value).strip()), False)

    def _name(self, rest, directive, error):
        m = _NAME_RE.match(rest)
        if m is None:
            raise error('#%s needs a macro name' % directive)
        return m.group(0)

    def _define(self, rest, error, line_number, file_name):
        name = self._name(rest, 'define', error)
        after = rest[len(name):]
        if after.startswith('('):
            # "#define F(x) ..." (no space before "(") is function-like.
            self._macros[name] = _Macro(name, after, True)
            warnings.warn(exception.IDLParserException(
                line_number, file_name,
                'Function-like macro "%s" is not expanded.' % name).message,
                PreprocessorWarning, stacklevel=3)
        else:
            self.define(name, after)

    def _format_body(self, body):
        # Put spaces around the punctuation of a macro body, like the comment
        # remover does for the other lines, but not inside literals.
        parts = []
        pos = 0
        for m in _LINE_TOKEN_RE.finditer(body):
            if m.lastgroup in ('str', 'chr'):
                parts.append(self._format_code(body[pos:m.start()]))
                parts.append(m.group(0))
                pos = m.end()
        parts.append(self._format_code(body[pos:]))
        return re.sub(r'\s+', ' ', ' '.join(parts)).strip()

    def expand(self, text, hidden=frozenset()):
        """Expand the object-like macros in ``text``. Names in string and
        character literals are not expanded, and a macro is not expanded
        again inside its own body."""
        def replace(m):
            name = m.group('name')
            if name is None:
                return m.group(0)
            macro = self._macros.get(name)
            if macro is None or macro.function_like or name in hidden:
                return name
            return self.expand(macro.body, hidden | {name})
        return _LINE_TOKEN_RE.sub(replace, text)

    def _evaluate(self, text, error):
        # "defined X" and "defined(X)" are taken before macros are expanded.
        def defined(m):
            return ' 1 ' if (m.group(1) or m.group(2)) in self._macros else ' 0 '
        text = re.sub(r'\bdefined\s*(?:\(\s*([A-Za-z_]\w*)\s*\)|([A-Za-z_]\w*))',
                      defined, text)
        if re.search(r'\bdefined\b', text):
            raise error('Invalid "defined" in #if: %s' % text.strip())
        text = self.expand(text)
        tokens = []
        pos = 0
        while pos < len(text):
            m = _EXPR_TOKEN_RE.match(text, pos)
            if m is None:
                raise error('Invalid character "%s" in #if expression' % text[pos])
            pos = m.end()
            kind = m.lastgroup
            if kind == 'ws':
                continue
            if kind == 'num':
                tokens.append(('num', int(m.group(0).rstrip('uUlL'), 0)
                               if not re.match(r'0\d', m.group(0))
                               else int(m.group(0).rstrip('uUlL'), 8)))
            elif kind == 'chr':
                tokens.append(('num', _char_value(m.group(0), error)))
            elif kind == 'name':
                tokens.append(('num', 1 if m.group(0) == 'true' else 0))
            else:
                tokens.append(('op', m.group(0)))
        if not tokens:
            raise error('#if with no expression')
        value, pos = _ExpressionParser(tokens, error).parse()
        return value != 0


_ESCAPES = {'n': 10, 't': 9, 'v': 11, 'b': 8, 'r': 13, 'f': 12, 'a': 7,
            '\\': 92, '?': 63, "'": 39, '"': 34, '0': 0}


def _char_value(literal, error):
    body = literal[1:-1]
    if len(body) == 1:
        return ord(body)
    if body[0] == '\\':
        if body[1] in 'xX':
            return int(body[2:], 16)
        if body[1:].isdigit():
            return int(body[1:], 8)
        if len(body) == 2 and body[1] in _ESCAPES:
            return _ESCAPES[body[1]]
    raise error('Invalid character literal %s in #if expression' % literal)


# Binary operators by precedence, lowest first.
_BINARY = [('||',), ('&&',), ('|',), ('^',), ('&',), ('==', '!='),
           ('<', '>', '<=', '>='), ('<<', '>>'), ('+', '-'), ('*', '/', '%')]


class _ExpressionParser(object):
    def __init__(self, tokens, error):
        self._tokens = tokens
        self._pos = 0
        self._error = error

    def parse(self):
        value = self._conditional()
        if self._pos != len(self._tokens):
            raise self._error('Unexpected "%s" in #if expression' % (self._tokens[self._pos][1],))
        return value, self._pos

    def _peek(self):
        if self._pos < len(self._tokens):
            return self._tokens[self._pos]
        return (None, None)

    def _expect(self, op):
        if self._peek() != ('op', op):
            raise self._error('"%s" expected in #if expression' % op)
        self._pos += 1

    def _conditional(self):
        cond = self._binary(0)
        if self._peek() == ('op', '?'):
            self._pos += 1
            a = self._conditional()
            self._expect(':')
            b = self._conditional()
            return a if cond else b
        return cond

    def _binary(self, level):
        if level == len(_BINARY):
            return self._unary()
        value = self._binary(level + 1)
        while self._peek()[0] == 'op' and self._peek()[1] in _BINARY[level]:
            op = self._peek()[1]
            self._pos += 1
            right = self._binary(level + 1)
            value = self._apply(op, value, right)
        return value

    def _apply(self, op, a, b):
        if op in ('/', '%') and b == 0:
            raise self._error('Division by zero in #if expression')
        if op == '/':
            q = abs(a) // abs(b)
            return q if (a < 0) == (b < 0) else -q
        if op == '%':
            return a - b * self._apply('/', a, b)
        return {
            '||': lambda: int(bool(a) or bool(b)),
            '&&': lambda: int(bool(a) and bool(b)),
            '|': lambda: a | b, '^': lambda: a ^ b, '&': lambda: a & b,
            '==': lambda: int(a == b), '!=': lambda: int(a != b),
            '<': lambda: int(a < b), '>': lambda: int(a > b),
            '<=': lambda: int(a <= b), '>=': lambda: int(a >= b),
            '<<': lambda: a << b, '>>': lambda: a >> b,
            '+': lambda: a + b, '-': lambda: a - b, '*': lambda: a * b,
        }[op]()

    def _unary(self):
        kind, value = self._peek()
        if kind == 'op' and value in ('!', '~', '-', '+'):
            self._pos += 1
            operand = self._unary()
            return {'!': int(not operand), '~': ~operand,
                    '-': -operand, '+': operand}[value]
        if kind == 'op' and value == '(':
            self._pos += 1
            result = self._conditional()
            self._expect(')')
            return result
        if kind == 'num':
            self._pos += 1
            return value
        if kind is None:
            raise self._error('Unexpected end of #if expression')
        raise self._error('Unexpected "%s" in #if expression' % value)
