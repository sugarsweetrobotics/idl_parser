"""IDL constants."""
import os, sys, traceback

from . import node
sep = '::'


class IDLConst(node.IDLNode):
    """A ``const`` definition, such as ``const long MAX = 10;``.

    :param name: Constant name.
    :param typename: Type name as written (``'long'``, ``'string'``, ...).
    :param value: Value as written, which may be an expression (``'1 + 2'``).
    :param parent: Enclosing :class:`~idl_parser.module.IDLModule`.
    :param filepath: File the constant was defined in.
    """
    def __init__(self, name, typename, value, parent, filepath=None):
        super(IDLConst, self).__init__('IDLConst', name, parent)
        self._typename = typename
        self._verbose = True
        self._value = value
        self._filepath= filepath

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
        """Value as written (a string; not evaluated).

        A string literal keeps its quotes (``'"hi"'``); an expression is kept
        whole (``'1 + 2'``).
        """
        return self._value

    @property
    def value_string(self):
        """Same as :attr:`value`."""
        return self._value

    @property
    def full_path(self):
        """Scoped name (``'M::MAX'``; ``'::MAX'`` at the global scope)."""
        return self.parent.full_path + sep + self.name

