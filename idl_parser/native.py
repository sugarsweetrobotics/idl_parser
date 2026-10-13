"""IDL native type declarations."""
from . import node
sep = '::'


class IDLNative(node.IDLNode):
    """A ``native`` declaration, such as ``native Cookie;`` (issue #93).

    A native type has a name only; its representation is left to the
    language mapping. It is found by
    :meth:`~idl_parser.module.IDLModule.find_types`, so it can be the type of
    a member, an argument or a typedef.

    :param name: Type name.
    :param parent: Enclosing :class:`~idl_parser.module.IDLModule`.
    :param filepath: File the type was declared in.
    """
    def __init__(self, name, parent, filepath=None):
        super(IDLNative, self).__init__('IDLNative', name, parent)
        self._filepath = filepath

    @property
    def full_path(self):
        """Scoped name (``'M::N'``; ``'::N'`` at the global scope)."""
        return self.parent.full_path + sep + self.name

    def to_simple_dic(self, quiet=False, full_path=False, recursive=False, member_only=False):
        """A compact summary: ``'native NAME'``.

        :param full_path: Use :attr:`full_path` as the name.
        """
        name = self.full_path if full_path else self.name
        if member_only:
            return []
        return 'native %s' % name

    def to_dic(self):
        """The declaration as a plain dict (for JSON or YAML output)."""
        dic = { 'name' : self.name,
                'filepath' : self.filepath,
                'classname' : self.classname }
        return self._with_annotations(dic)
