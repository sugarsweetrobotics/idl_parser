"""IDL constants."""
import decimal
import os, sys, traceback

from . import node
from . import const_expr
from . import type as idl_type
from .token_buffer import split_tokens
from .exception import InvalidConstExpressionError
sep = '::'

# Floating-point types and the largest finite value of each (issue #137)
_float_types = {'float': 3.4028234663852886e38, 'double': None, 'long double': None}


class IDLConst(node.IDLNode):
    """A ``const`` definition, such as ``const long MAX = 10;``.

    :param name: Constant name.
    :param typename: Type name as written (``'long'``, ``'string'``, ...).
    :param value: Value as written, which may be an expression (``'1 + 2'``).
        The value of a constant of an integer type is evaluated
        (:attr:`value`, issue #130).
    :param parent: Enclosing :class:`~idl_parser.module.IDLModule`.
    :param filepath: File the constant was defined in.
    """
    def __init__(self, name, typename, value, parent, filepath=None):
        super(IDLConst, self).__init__('IDLConst', name, parent)
        self._typename = typename
        self._verbose = True
        self._value = value
        self._filepath= filepath
        self._int_value = None
        self._typed_value = None
        self._evaluated = False
        self._base_type = None

    def _evaluate(self, line_number=None, file_name=None):
        """Evaluate the value with the type of the constant (issues #130, #137).

        :raises ~idl_parser.exception.InvalidConstExpressionError: The value
            is not a valid value of the type, or is out of its range.
        """
        base = self._resolve_base_type()
        self._base_type = base
        if base is None:
            return  # a type that has no values (or is not defined)
        def error(reason):
            return InvalidConstExpressionError(
                line_number, file_name, 'Invalid value "%s" of const "%s": %s'
                % (self._value, self.name, reason))
        try:
            value = self._evaluate_as(base, error)
        except const_expr.ConstExprError as e:
            raise error(e)
        self._typed_value = value
        self._evaluated = True
        if base in const_expr.integer_types:
            self._int_value = value

    def _resolve_base_type(self):
        """The type the constant's type stands for, typedefs followed: a
        primitive type name (``'long'``, ``'double'``, ``'string'``, ...),
        ``'fixed'``, or an :class:`~idl_parser.enum.IDLEnum`. None for any
        other type."""
        name = ' '.join(self.typename.split())
        scope = self.parent
        self._string_bound = None
        for _ in range(32):  # a typedef of a typedef of ...
            if name in const_expr.integer_types or name in _float_types or \
                    name in ('char', 'wchar', 'boolean', 'string', 'wstring'):
                return name
            bounded = idl_type.parse_bounded_string(name)
            if bounded is not None:
                self._string_bound = const_expr.evaluate_positive(
                    bounded[1], scope, 'bound of "%s"' % name)
                return bounded[0]
            if name == 'fixed' or idl_type.parse_fixed(name) is not None:
                return 'fixed'
            typs = self.root_node.find_types(name, scope=scope)
            if not typs:
                return None
            if typs[0].is_enum:
                return typs[0]
            if not typs[0].is_typedef:
                return None
            scope = typs[0].parent
            name = ' '.join(str(typs[0].type).split())
        return None

    def _evaluate_as(self, base, error):
        """The value of the constant for the type ``base`` (see
        :meth:`_resolve_base_type`)."""
        text = self._value
        if not isinstance(base, str):  # an enum
            value = base.find_enumerator(text)
            if value is None:
                value = self._const_of(text, lambda v: getattr(v, 'parent', None) is base)
            if value is None:
                raise error('not an enumerator of %s' % base.full_path.lstrip(':'))
            return value
        if base in const_expr.integer_types:
            value = const_expr.evaluate(text, self.parent)
            low, high = const_expr.integer_ranges[base]
            if not low <= value <= high:
                raise error('%d is out of the range of %s' % (value, base))
            return value
        if base in _float_types:
            value = const_expr.evaluate_real(text, self.parent, 'float')
            limit = _float_types[base]
            if value != value or value in (float('inf'), float('-inf')) or \
                    (limit is not None and abs(value) > limit):
                raise error('%r is out of the range of %s' % (value, base))
            return value
        if base == 'fixed':
            value = const_expr.evaluate_real(text, self.parent, 'fixed')
            if len(value.as_tuple().digits) > 31:
                raise error('a fixed-point value has at most 31 digits')
            return value
        if base == 'boolean':
            value = const_expr.parse_boolean_literal(text)
            if value is None:
                value = self._const_of(text, lambda v: isinstance(v, bool))
            if value is None:
                raise error('not TRUE or FALSE')
            return value
        if base in ('char', 'wchar'):
            value = const_expr.parse_char_literal(text, wide=base == 'wchar')
            if value is None:
                value = self._const_of(text, lambda v: isinstance(v, str) and len(v) == 1)
            if value is None:
                raise error('not a character literal')
            if base == 'char' and ord(value) > 255:
                raise error('%r is not a char' % value)
            return value
        # string / wstring: adjacent literals are joined ("a" "b" -> "ab")
        parts = []
        for token in split_tokens(text):
            literal = token[1:] if base == 'wstring' and token.startswith('L"') else token
            if len(literal) >= 2 and literal[0] == '"' and literal[-1] == '"':
                parts.append(const_expr.unescape(literal[1:-1]))
                continue
            value = self._const_of(token, lambda v: isinstance(v, str))
            if value is None:
                raise error('not a string literal')
            parts.append(value)
        value = ''.join(parts)
        if base == 'string' and any(ord(c) > 255 for c in value):
            raise error('a string holds only 8-bit characters; use wstring')
        if self._string_bound is not None and len(value) > self._string_bound:
            raise error('%d characters are more than the bound %d' % (len(value), self._string_bound))
        return value

    def _const_of(self, name, accept):
        """The value of the constant named ``name`` if ``accept(value)``,
        otherwise None."""
        try:
            c = const_expr.find_const(name, self.parent)
        except Exception:
            return None
        if c is None or c is self or not c._evaluated or not accept(c._typed_value):
            return None
        return c._typed_value

    @property
    def is_integer(self):
        """True if the type is an integer type (``long``, ``unsigned short``,
        ``int32``, ``octet``, ..., or a typedef of one)."""
        return self._base_type in const_expr.integer_types

    @property
    def int_value(self):
        """The value of a constant of an integer type as an int
        (``const long M = N * 2;`` -> ``6`` when ``N`` is 3), otherwise None."""
        return self._int_value

    def to_simple_dic(self, quiet=False, full_path=False, recursive=False, member_only=False):
        """A compact summary: ``{'const NAME': {'type': ..., 'value': ...}}``.

        :param quiet: Return ``'const TYPE NAME = VALUE'`` instead.
        :param full_path: Use :attr:`full_path` as the name.
        """
        name = self.full_path if full_path else self.name
        if quiet:
            value = self._plain_value()
            if isinstance(value, str) or not self._evaluated:
                value = self.value_string  # keep the quotes of a literal
            return 'const %s %s = %s' % (self.typename, name, value)
        dic = { 'const %s' % name : { 'type' : self.typename,
                                      'value' : self._plain_value() } }
        return dic

    def to_dic(self):
        """The constant as a plain dict (for JSON or YAML output).

        ``'value'`` is :attr:`value`, except that a fixed-point value is a
        string (``'1.25'``) and an enumerator its scoped name (``'M::RED'``).
        """
        dic = { 'name' : self.name,
                'filepath' : self.filepath,
                'classname' : self.classname,
                'typename' : self.typename,
                'value' : self._plain_value() }
        return self._with_annotations(dic)

    def _plain_value(self):
        """:attr:`value` as a str, int, float or bool (for JSON)."""
        value = self.value
        if isinstance(value, decimal.Decimal):
            return str(value)
        if isinstance(value, node.IDLNode):
            return value.full_path.lstrip(':')
        return value

    @property
    def typename(self):
        """Type name as written."""
        return self._typename

    @property
    def type(self):
        """The type of the constant, looked up from the scope of the constant.

        For ``const fixed F = 1.25d;`` it is an
        :class:`~idl_parser.type.IDLFixed` whose digits and scale are those
        of the value (``fixed<3, 2>``, issue #137).
        """
        if ' '.join(self.typename.split()) == 'fixed':
            digits, scale = _fixed_digits(self.value) if self._evaluated else (1, 0)
            return idl_type.IDLFixed(idl_type.fixed_name(digits, scale), self)
        return self.root_node.find_types(self.typename, scope=self)[0]

    @property
    def value(self):
        """Value of the constant, evaluated with its type (issues #130, #137):

        - integer types: an int (``const long X = 1 + 2;`` -> ``3``)
        - ``float`` / ``double`` / ``long double``: a float
          (``const double D = 1.0 / 4;`` -> ``0.25``)
        - ``fixed``: a :class:`decimal.Decimal` (``1.25d`` -> ``Decimal('1.25')``)
        - ``string`` / ``wstring``: a str without the quotes, escapes
          replaced and adjacent literals joined (``"a" "b"`` -> ``'ab'``)
        - ``char`` / ``wchar``: a str of one character
        - ``boolean``: a bool
        - an enum: the :class:`~idl_parser.enum.IDLEnumValue`

        Typedefs of these types are followed, and the names of other
        constants can be used. For other types the value is the text as
        written (see :attr:`value_string`).
        """
        if self._evaluated:
            return self._typed_value
        return self._value

    @property
    def value_string(self):
        """Value as written (a string; ``'1 + 2'`` is kept whole)."""
        return self._value

    @property
    def full_path(self):
        """Scoped name (``'M::MAX'``; ``'::MAX'`` at the global scope)."""
        return self.parent.full_path + sep + self.name


def _fixed_digits(value):
    """(digits, scale) of a fixed-point value: ``Decimal('1.25')`` -> ``(3, 2)``."""
    t = value.as_tuple()
    scale = max(0, -t.exponent)
    digits = len(t.digits) + max(0, t.exponent)
    return max(digits, scale, 1), scale
