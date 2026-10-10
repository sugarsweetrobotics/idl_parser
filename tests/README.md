# tests

Tests are grouped by what they check. Each directory is a package; a file
name says what its tests cover. Issue numbers are kept in the module
docstrings, not in file names.

| Directory | What it covers |
|---|---|
| `lexing/` | Comments, string / char literals, token splitting, spacing inside `[ ]` and `< >`, error line numbers, exception messages |
| `include/` | `#include`: circular and diamond includes, sub paths, include directories |
| `scope/` | Modules, reopened modules, scoped and absolute (`::M::X`) type names, `find_types()` |
| `primitive_const/` | Primitive types (including IDL 4.2 `int8` … `uint64`) and `const` definitions |
| `sequence_array/` | `typedef`, `sequence<>` (nested and bounded), arrays, their element types |
| `struct_enum_union/` | `struct`, `enum`, `union` (case / default labels, char literal labels) |
| `bitmask_bitset/` | IDL 4.2 `bitmask` and `bitset` |
| `interface/` | Interfaces, operations, `raises` / `context`, inheritance |
| `forward_declaration/` | Forward declarations of interfaces, structs and unions |
| `annotation/` | IDL 4 annotations |
| `pragma_key/` | `#pragma`, `#pragma keylist`, `@key` |
| `output/` | `to_dic()`, `to_simple_dic()`, `generate_constructor_python()` |
| `examples/` | Every script in `examples/` runs and prints what it should |

`basic_module_test.py` in several directories covers the part of
`idls/basic_module_test.idl` that belongs to that directory.

IDL files used by the tests are in `idls/`. Use `support.IDL_DIR` (and
`support.ROOT` for the repository root) instead of paths built from
`__file__`.

## Running

From the repository root, the same command as CI:

```sh
python -m unittest discover --start-directory tests --pattern '*_test.py' --top-level-directory .
```

One directory or one file:

```sh
python -m unittest discover --start-directory tests/scope --pattern '*_test.py' --top-level-directory .
python -m unittest tests.scope.same_name_resolution_test
```

New test files must end in `_test.py` and go in the directory that matches
what they check.

## Docstrings

Every test class and test method has a docstring in English and Japanese.
The first line is the English summary; `unittest -v` prints it next to the
test name.

```python
class UnionDefaultTest(unittest.TestCase):
    """Category: Structs, enums and unions / カテゴリ: struct・enum・union

    Union members with a "default:" label (issue #48).
    "default:" ラベルを持つ union メンバー(#48)。
    """

    def test_default_only(self):
        """A union with only a default member.

        default メンバーだけの union。
        """
```
