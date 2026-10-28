"""Repository IDs (``IDL:omg.org/CosNaming/NamingContext:1.0``, issue #135).

The repository ID of a definition is available as
:attr:`idl_parser.node.IDLNode.repository_id`. It follows the rules of the
CORBA specification (Repository Identity, "Generation of OMG IDL-Format
IDs"):

- By default it is ``IDL:`` + the scoped name with ``/`` between the
  components + ``:1.0`` (``::M1::T1`` -> ``IDL:M1/T1:1.0``).
- ``#pragma prefix "P"`` applies to the definitions after it, up to the end
  of the scope it is written in (or the next ``#pragma prefix``). The ID is
  ``IDL:P/`` + the scoped name relative to that scope + the version, so a
  prefix written in module ``M2::M3`` gives ``IDL:P2/T3:1.0`` for
  ``M2::M3::T3``. ``#pragma prefix ""`` sets the prefix back to none.
- A prefix is not passed into an ``#include`` file, which starts with no
  prefix, and the prefix of the including file is back after it.
- ``#pragma version N 2.4`` changes the version (``IDL:P1/M2/T4:2.4``).
- ``#pragma ID N "..."`` and ``typeid N "...";`` give the whole ID.
- ``typeprefix N "P";`` applies the prefix ``P`` to the scope ``N`` (a
  module, an interface, a value type, an event type, or ``::``) and to every
  definition in it, with the full scoped name
  (``typeprefix M "x.org";`` -> ``IDL:x.org/M/S:1.0`` for ``M::S``). It
  wins over a ``#pragma prefix``.

Giving one definition two different IDs, two different versions, a version
that does not match its ID, or giving one scope two different type prefixes
is an :class:`~idl_parser.exception.InvalidIDLSyntaxError`.
"""
import re

from .exception import InvalidIDLSyntaxError
from . import pragma as idl_pragma

# Kinds of nodes that have a repository ID. Members, arguments,
# enumerators and type references have none.
classnames = ('IDLModule', 'IDLInterface', 'IDLValueType', 'IDLEventType',
              'IDLStruct', 'IDLException', 'IDLUnion', 'IDLEnum', 'IDLTypedef',
              'IDLConst', 'IDLNative', 'IDLBitmask', 'IDLBitset',
              'IDLAttribute', 'IDLValue')

# Scopes that a typeprefix can name
_typeprefix_classnames = ('IDLModule', 'IDLInterface', 'IDLValueType', 'IDLEventType')

_version = re.compile(r'^\d+\.\d+$')


def repository_id(node):
    """The repository ID of ``node``, or None for a node that has none
    (see :attr:`idl_parser.node.IDLNode.repository_id`)."""
    if node.classname not in classnames or node.parent is None:
        return None
    if node._repo_id is not None:
        return node._repo_id
    prefix, base = node._repo_prefix
    n = node
    while n is not None:
        if n._typeprefix is not None:
            prefix, base = n._typeprefix, None
            break
        n = n.parent
    names = []
    n = node
    while n is not None and n is not base and n.parent is not None:
        names.append(n.name)
        n = n.parent
    body = '/'.join(reversed(names))
    if prefix:
        body = prefix + '/' + body
    return 'IDL:%s:%s' % (body, node._repo_version or '1.0')


def take_pragmas(scope, token_buf):
    """Apply the ``#pragma prefix`` lines (and the ends of ``#include``
    files) that ``token_buf`` has gone past to ``scope``, the scope being
    parsed. Other pragmas remember ``scope``, where their names are
    looked up."""
    for p in token_buf.take_pragmas():
        if p.name == idl_pragma.INCLUDE_BEGIN:
            scope._include_prefixes.append(scope._prefix_state)
            scope._prefix_state = ('', None)
        elif p.name == idl_pragma.INCLUDE_END:
            if scope._include_prefixes:
                scope._prefix_state = scope._include_prefixes.pop()
        else:
            if p._scope_node is None:
                p._scope_node = scope
            if p.is_prefix:
                scope._prefix_state = (p.value, None if scope.parent is None else scope)


def apply_pragma(p, global_module):
    """Apply a ``#pragma ID`` or ``#pragma version`` to its definition.

    Returns True when the definition has been found.
    """
    if p._target is not None:
        return True
    if not p.arguments or p._scope_node is None:
        return False
    target = find_definition(p.arguments[0], p._scope_node)
    if target is None:
        return False
    if p.value is None:
        raise InvalidIDLSyntaxError(p.line_number, p.filepath,
                                    'No value in "#pragma %s %s"' % (p.name, ' '.join(p.arguments)))
    if p.is_id:
        set_id(target, p.value, p.line_number, p.filepath)
    else:
        set_version(target, p.value, p.line_number, p.filepath)
    p._target = target
    return True


def apply_declaration(decl, global_module):
    """Apply a ``typeid`` or ``typeprefix`` declaration
    (a :class:`TypeDeclaration`). Returns True when its scope or
    definition has been found."""
    if decl.target is not None:
        return True
    if decl.name == '::':
        target = global_module
    else:
        target = find_definition(decl.name, decl.scope)
    if target is None:
        return False
    if decl.keyword == 'typeid':
        set_id(target, decl.value, decl.line_number, decl.filepath)
    else:
        if target.parent is not None and target.classname not in _typeprefix_classnames:
            raise InvalidIDLSyntaxError(
                decl.line_number, decl.filepath,
                '"typeprefix %s" does not name a module, an interface, a valuetype or an eventtype'
                % decl.name)
        if target._typeprefix is not None and target._typeprefix != decl.value:
            raise InvalidIDLSyntaxError(
                decl.line_number, decl.filepath,
                'Type prefix of "%s" is already "%s"; can not change it to "%s"'
                % (decl.name, target._typeprefix, decl.value))
        target._typeprefix = decl.value
    decl.target = target
    return True


def set_id(node, value, line_number=None, filepath=None):
    """Give ``node`` the repository ID ``value``."""
    _check_has_id(node, line_number, filepath)
    if node._repo_id is not None and node._repo_id != value:
        raise InvalidIDLSyntaxError(
            line_number, filepath, 'Repository ID of "%s" is already "%s"; can not change it to "%s"'
            % (_name(node), node._repo_id, value))
    if node._repo_version is not None and not _matches_version(value, node._repo_version):
        raise InvalidIDLSyntaxError(
            line_number, filepath, 'Repository ID "%s" of "%s" does not match its version %s'
            % (value, _name(node), node._repo_version))
    node._repo_id = value


def set_version(node, version, line_number=None, filepath=None):
    """Give ``node`` the version ``version`` (``'2.4'``)."""
    _check_has_id(node, line_number, filepath)
    if not _version.match(version):
        raise InvalidIDLSyntaxError(
            line_number, filepath, 'Invalid version "%s" of "%s" (expected <major>.<minor>)'
            % (version, _name(node)))
    if node._repo_version is not None and node._repo_version != version:
        raise InvalidIDLSyntaxError(
            line_number, filepath, 'Version of "%s" is already %s; can not change it to %s'
            % (_name(node), node._repo_version, version))
    if node._repo_id is not None and not _matches_version(node._repo_id, version):
        raise InvalidIDLSyntaxError(
            line_number, filepath, 'Version %s of "%s" does not match its repository ID "%s"'
            % (version, _name(node), node._repo_id))
    node._repo_version = version


def _matches_version(repo_id, version):
    return repo_id.startswith('IDL:') and repo_id.endswith(':' + version)


def _check_has_id(node, line_number, filepath):
    if node.classname not in classnames or node.parent is None:
        raise InvalidIDLSyntaxError(
            line_number, filepath, '"%s" has no repository ID' % _name(node))


def _name(node):
    names = []
    n = node
    while n is not None and n.parent is not None:
        names.append(n.name)
        n = n.parent
    return '::'.join(reversed(names))


def find_definition(name, scope):
    """The definition named ``name`` (``'A'``, ``'A::B'``, ``'::A::B'``)
    as seen from ``scope``: the name is looked up in ``scope`` first, then
    in each enclosing scope. Every kind of definition is found, modules,
    constants, exceptions, operations and attributes included. None if
    nothing is found."""
    name = name.strip()
    absolute = name.startswith('::')
    parts = [x.strip() for x in name.lstrip(':').split('::')]
    if not all(parts):
        return None
    starts = []
    n = scope
    while n is not None:
        if hasattr(n, '_definitions_dic') or n.parent is None:
            starts.append(n)
        n = n.parent
    if absolute:
        starts = starts[-1:]
    for start in starts:
        found = start
        for part in parts:
            found = _child(found, part)
            if found is None:
                break
        if found is not None:
            return found
    return None


def _child(scope, name):
    for kind in ('modules', 'interfaces', 'valuetypes', 'eventtypes', 'structs',
                 'exceptions', 'unions', 'enums', 'typedefs', 'consts', 'natives',
                 'bitmasks', 'bitsets', 'methods', 'attributes'):
        for n in getattr(scope, kind, None) or []:
            if n.name == name:
                return n
    return None


class TypeDeclaration(object):
    """A ``typeid`` or ``typeprefix`` declaration (issue #135).

    :param keyword: ``'typeid'`` or ``'typeprefix'``.
    :param name: The scoped name as written.
    :param value: The string, without quotes.
    :param scope: The scope the declaration is written in.
    """
    def __init__(self, keyword, name, value, scope, line_number=None, filepath=None):
        self.keyword = keyword
        self.name = name
        self.value = value
        self.scope = scope
        self.line_number = line_number
        self.filepath = filepath
        self.target = None


def parse_declaration(keyword, tokens, scope, line_number=None, filepath=None):
    """Read ``typeid NAME "ID"`` or ``typeprefix NAME "P"`` (``tokens`` after
    the keyword, up to, not including, the ``;``) and remember it in the
    global scope; it is applied when the input has been parsed."""
    if len(tokens) != 2 or not (tokens[1].startswith('"') and tokens[1].endswith('"')
                                and len(tokens[1]) >= 2):
        raise InvalidIDLSyntaxError(
            line_number, filepath, 'Invalid declaration "%s %s" (expected %s <scoped name> "<string>")'
            % (keyword, ' '.join(tokens), keyword))
    decl = TypeDeclaration(keyword, tokens[0], tokens[1][1:-1], scope, line_number, filepath)
    scope.root_node._type_declarations.append(decl)
    return decl
