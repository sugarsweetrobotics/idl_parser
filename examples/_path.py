"""Make the examples use the idl_parser of this source checkout.

``python examples/xxx.py`` puts ``examples/`` (not the repository root) on
``sys.path``, so ``import idl_parser`` would fail without installing the
package, or would pick up an older installed version. When the examples sit
in a checkout next to the ``idl_parser`` package, that package is used.
Copied elsewhere, the examples use the installed ``idl_parser``.
"""
import os
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if os.path.isdir(os.path.join(_root, 'idl_parser')) and _root not in sys.path:
    sys.path.insert(0, _root)
