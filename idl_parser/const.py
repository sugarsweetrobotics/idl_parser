"""IDL constants."""
import os, sys, traceback

from . import node
from . import const_expr
from .exception import InvalidConstExpressionError
sep = '::'


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

    def _evaluate(self, line_number=None, file_name=None):
        """Evaluate the value of a constant of an integer type (issue #130).

        :raises ~idl_parser.exception.InvalidConstExpressionError: The value
            is not an integer constant expression.
        """
        if not self.is_integer:
            return
        try:
            self._int_value = const_expr.evaluate(self._value, self.parent)
        except const_expr.ConstExprError as e:
            raise InvalidConstExpressionError(
                line_number, file_name, 'Invalid value "%s" of const "%s": %s'
                % (self._value, self.name, e))

    @property
    def is_integer(self):
        """True if the type is an integer type (``long``, ``unsigned short``,
        ``int32``, ``octet``, ..., or a typedef of one)."""
        name = ' '.join(self.typename.split())
        scope = self.parent
        for _ in range(32):  # a typedef of a typedef of ...
            if name in const_expr.integer_types:
                return True
            typs = self.root_node.find_types(name, scope=scope)
            if not typs or not typs[0].is_typedef:
                return False
            scope = typs[0].parent
            name = ' '.join(str(typs[0].type).split())
        return False

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
            return 'const %s %s = %s' % (self.typename, name, self.value)
        dic = { 'const %s' % name : { 'type' : self.typename,
                                      'value' : self.value } }
        return dic

    def to_dic(self):
        """The constant as a plain dict (for JSON or YAML output)."""
        dic = { 'name' : self.name,
                'filepath' : self.filepath,
                'classname' : self.classname,
                'typename' : self.typename,
                'value' : self.value }
        return self._with_annotations(dic)

    @property
    def typename(self):
        """Type name as written."""
        return self._typename

    @property
    def type(self):
        """The type of the constant, looked up from the scope of the constant."""
        return self.root_node.find_types(self.typename, scope=self)[0]
    @property
    def value(self):
        """Value of the constant.

        For an integer type it is the evaluated value, an int
        (``const long X = 1 + 2;`` -> ``3``, issue #130). For other types it
        is the value as written, a string: a string literal keeps its quotes
        (``'"hi"'``).
        """
        if self._int_value is not None:
            return self._int_value
        return self._value

    @property
    def value_string(self):
        """Value as written (a string; ``'1 + 2'`` is kept whole)."""
        return self._value

    @property
    def full_path(self):
        """Scoped name (``'M::MAX'``; ``'::MAX'`` at the global scope)."""
        return self.parent.full_path + sep + self.name

