"""#if / #elif / #else and macro expansion (issue #120).

Only #define NAME, #ifdef, #ifndef and #endif were handled: "#if" was an
unknown word in the global scope, and "#define N 5" did not make "long
a[N];" an array of 5 elements. A #define in a skipped branch was still
defined, and a branch nested in a skipped branch was kept.
"""
import os
import tempfile
import unittest
import warnings
from idl_parser import parser
from idl_parser.exception import InvalidIDLSyntaxError
from idl_parser.preprocessor import PreprocessorWarning


def load(idl):
    return parser.IDLParser().load(idl)


def struct_names(idl):
    return [s.name for s in load(idl).structs]


def error_of(idl):
    try:
        load(idl)
    except InvalidIDLSyntaxError as e:
        return e
    return None


class ConditionalTest(unittest.TestCase):
    """Category: Lexing, preprocessing and error line numbers / カテゴリ: 字句解析・前処理・エラー行番号

    #if / #elif / #else select the lines that are parsed (issue #120).
    #if / #elif / #else で解析する行が選ばれる(#120)。
    """

    def test_if_else(self):
        """The branch of #if or the one of #else is kept.

        #if の分岐か #else の分岐のどちらかが残る。
        """
        self.assertEqual(struct_names('#if 1\nstruct A {};\n#else\nstruct B {};\n#endif\n'), ['A'])
        self.assertEqual(struct_names('#if 0\nstruct A {};\n#else\nstruct B {};\n#endif\n'), ['B'])

    def test_elif(self):
        """Only the first true branch of #if / #elif is kept.

        #if / #elif のうち最初に真になった分岐だけが残る。
        """
        idl = ('#if V == 1\nstruct A {};\n#elif V == 2\nstruct B {};\n'
               '#elif V >= 2\nstruct C {};\n#else\nstruct D {};\n#endif\n')
        for v, expected in (('1', ['A']), ('2', ['B']), ('3', ['C']), ('0', ['D'])):
            with self.subTest(v):
                self.assertEqual(struct_names('#define V %s\n' % v + idl), expected)

    def test_defined(self):
        """defined X and defined(X) tell whether X is defined.

        defined X と defined(X) で X が定義されているかを調べられる。
        """
        for expr, expected in (('defined(X)', ['A']), ('defined X', ['A']),
                               ('!defined(Y)', ['A']), ('defined(Y)', ['B']),
                               ('defined(X) && defined(Y)', ['B']),
                               ('defined(X) || defined(Y)', ['A'])):
            with self.subTest(expr):
                idl = '#define X\n#if %s\nstruct A {};\n#else\nstruct B {};\n#endif\n' % expr
                self.assertEqual(struct_names(idl), expected)

    def test_expressions(self):
        """Integer expressions are evaluated as in C.

        整数式が C と同じように評価される。
        """
        for expr, value in (('2 + 3 * 4 == 14', True), ('(2 + 3) * 4 == 20', True),
                            ('0x10 == 16', True), ('010 == 8', True), ('10UL > 9L', True),
                            ('7 / 2 == 3 && 7 % 2 == 1', True), ('-7 / 2 == -3', True),
                            ('1 << 4 == 16', True), ('~0 == -1', True),
                            ('(5 & 3) == 1 && (5 | 3) == 7 && (5 ^ 3) == 6', True),
                            ('1 ? 0 : 1', False), ("'A' == 65", True),
                            ('UNKNOWN', False), ('UNKNOWN == 0', True),
                            ('true', True), ('false', False),
                            ('!1', False), ('1 != 1', False), ('2 <= 1', False)):
            with self.subTest(expr):
                idl = '#if %s\nstruct A {};\n#endif\n' % expr
                self.assertEqual(struct_names(idl), ['A'] if value else [])

    def test_nested(self):
        """A branch nested in a skipped branch is skipped, even when its
        condition is true.

        読み飛ばす分岐の中の分岐は、条件が真でも読み飛ばされる。
        """
        idl = ('#if 0\n#if 1\nstruct A {};\n#else\nstruct B {};\n#endif\n'
               '#ifndef X\nstruct C {};\n#endif\n#else\nstruct D {};\n#endif\n')
        self.assertEqual(struct_names(idl), ['D'])

    def test_define_in_skipped_branch(self):
        """#define and #undef in a skipped branch have no effect.

        読み飛ばす分岐の #define と #undef は効かない。
        """
        idl = ('#define Y\n#ifdef X\n#define Z\n#undef Y\n#endif\n'
               '#if defined(Z) || !defined(Y)\nstruct A {};\n#endif\n')
        self.assertEqual(struct_names(idl), [])

    def test_undef(self):
        """#undef removes a macro.

        #undef でマクロが削除される。
        """
        idl = '#define X\n#undef X\n#ifdef X\nstruct A {};\n#endif\n'
        self.assertEqual(struct_names(idl), [])

    def test_spaces_and_comments(self):
        """Spaces after "#", indentation and comments are allowed.

        "#" の後の空白、字下げ、コメントがあってもよい。
        """
        idl = ('  #  if 1 /* comment */ // comment\n struct A {};\n'
               '  # else\nstruct B {};\n  #  endif\n')
        self.assertEqual(struct_names(idl), ['A'])

    def test_line_continuation(self):
        """A directive continues on the next line after a backslash.

        バックスラッシュで次の行に続けられる。
        """
        idl = '#if 1 && \\\n    0\nstruct A {};\n#else\nstruct B {};\n#endif\n'
        self.assertEqual(struct_names(idl), ['B'])

    def test_line_numbers_kept(self):
        """Errors after a conditional keep the right line number.

        条件分岐の後のエラーでも行番号が正しい。
        """
        e = error_of('#if 0\nstruct A {};\n#endif\nstrcut B {};\n')
        self.assertIsNotNone(e)
        self.assertEqual(e.line_number, 4)

    def test_include_guard(self):
        """An include guard with #ifndef / #define still works.

        #ifndef / #define によるインクルードガードが使える。
        """
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, 'a.idl'), 'w') as f:
                f.write('#ifndef A_IDL\n#define A_IDL\n#define SIZE 4\nstruct A { long v[SIZE]; };\n#endif\n')
            with open(os.path.join(d, 'b.idl'), 'w') as f:
                f.write('#include "a.idl"\n#if SIZE == 4\nstruct B { A a; long w[SIZE]; };\n#endif\n')
            p = parser.IDLParser(idl_dirs=[d])
            p.parse(idls=[os.path.join(d, 'b.idl')])
            g = p.global_module
            self.assertEqual(sorted(s.name for s in g.structs), ['A', 'B'])
            self.assertEqual(g.struct_by_name('B').member_by_name('w').type.name, 'long [4]')

    def test_errors(self):
        """An unbalanced or invalid directive is an error with its line number.

        対応の取れない、または不正なディレクティブは行番号つきのエラーになる。
        """
        for idl, line, message in (
                ('struct A {};\n#endif\n', 2, '#endif without #if'),
                ('#else\n', 1, '#else without #if'),
                ('#elif 1\n', 1, '#elif without #if'),
                ('#if 1\n#else\n#else\n#endif\n', 3, '#else after #else'),
                ('#if 1\n#else\n#elif 1\n#endif\n', 3, '#elif after #else'),
                ('#if 1\nstruct A {};\n', 1, '#if without #endif'),
                ('#if\n#endif\n', 1, '#if with no expression'),
                ('#if (1\n#endif\n', 1, '")" expected'),
                ('#if 1 +\n#endif\n', 1, 'Unexpected end'),
                ('#if 1 / 0\n#endif\n', 1, 'Division by zero'),
                ('#if 1 = 1\n#endif\n', 1, 'Invalid character "="'),
                ('#ifdef\n#endif\n', 1, '#ifdef needs a macro name'),
                ('#define V 1\n#error V is not supported\n', 2, '#error V is not supported')):
            with self.subTest(idl):
                e = error_of(idl)
                self.assertIsNotNone(e)
                self.assertEqual(e.line_number, line)
                self.assertIn(message, str(e))

    def test_error_in_skipped_branch(self):
        """#error in a skipped branch is ignored.

        読み飛ばす分岐の #error は無視される。
        """
        self.assertEqual(struct_names('#if 0\n#error no\n#endif\nstruct A {};\n'), ['A'])

    def test_warning(self):
        """#warning issues a PreprocessorWarning.

        #warning で PreprocessorWarning が出る。
        """
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always')
            self.assertEqual(struct_names('#warning old IDL\nstruct A {};\n'), ['A'])
        self.assertEqual([str(x.message) for x in w if x.category is PreprocessorWarning],
                         ['line 1, (IDLParserException):"#warning old IDL"'])


class MacroTest(unittest.TestCase):
    """Category: Lexing, preprocessing and error line numbers / カテゴリ: 字句解析・前処理・エラー行番号

    Object-like macros are expanded (issue #120).
    オブジェクト形式マクロが展開される(#120)。
    """

    def test_array_size(self):
        """"#define N 5" makes "long a[N];" an array of 5 elements.

        "#define N 5" で "long a[N];" が要素数5の配列になる。
        """
        g = load('#define N 5\nstruct S { long a[N]; };\n')
        self.assertEqual(g.struct_by_name('S').member_by_name('a').type.name, 'long [5]')

    def test_nested_macros(self):
        """A macro body is expanded again; a macro is not expanded in its own body.

        マクロ本体はさらに展開され、自分自身の中では展開されない。
        """
        g = load('#define LEN SIZE\n#define SIZE 8\n#define T T\n'
                 'typedef sequence<long, LEN> Seq;\nstruct T { long x; };\n')
        self.assertEqual(g.typedef_by_name('Seq').type.bound, 8)
        self.assertEqual(struct_names('#define T T\nstruct T { long x; };\n'), ['T'])

    def test_type_and_value(self):
        """A macro may stand for a type name or a constant value with punctuation.

        マクロで型名や記号を含む定数値を表せる。
        """
        g = load('#define INT long long\n#define NAME "a;b{c}"\n#define ZERO (0)\n'
                 'module M { const INT X = ZERO; const string S = NAME; };\n')
        m = g.module_by_name('M')
        self.assertEqual(m.const_by_name('X').type.name, 'long long')
        self.assertEqual(m.const_by_name('S').value, '"a;b{c}"')

    def test_literals_and_names_kept(self):
        """Names in literals and parts of longer names are not expanded.

        リテラル中の名前や長い名前の一部は展開されない。
        """
        g = load('#define N 5\nmodule M { const string S = "N"; const char C = \'N\'; '
                 'const long NN = 1; struct S2 { long N_; }; };\n')
        m = g.module_by_name('M')
        self.assertEqual(m.const_by_name('S').value, '"N"')
        self.assertEqual(m.const_by_name('C').value, "'N'")
        self.assertEqual(m.const_by_name('NN').value, 1)
        self.assertEqual(m.struct_by_name('S2').members[0].name, 'N_')

    def test_redefine_and_undef(self):
        """The macro in effect at each line is used.

        各行ではその時点のマクロが使われる。
        """
        g = load('#define N 2\nstruct A { long a[N]; };\n#undef N\n#define N 3\n'
                 'struct B { long b[N]; };\n')
        self.assertEqual(g.struct_by_name('A').members[0].type.name, 'long [2]')
        self.assertEqual(g.struct_by_name('B').members[0].type.name, 'long [3]')

    def test_function_like_macro(self):
        """A function-like macro is defined but not expanded, with a warning.

        関数形式マクロは定義されるが展開されず、警告が出る。
        """
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always')
            names = struct_names('#define F(x) x\n#if defined(F)\nstruct A {};\n#endif\n')
        self.assertEqual(names, ['A'])
        self.assertEqual(len([x for x in w if x.category is PreprocessorWarning]), 1)
        self.assertIn('Function-like macro "F" is not expanded.', str(w[0].message))

    def test_pragma_not_expanded(self):
        """Macros are not expanded in #pragma lines.

        #pragma の行ではマクロは展開されない。
        """
        p = parser.IDLParser()
        p.load('#define K id\nstruct S { long id; long K2; };\n#pragma keylist S K2\n')
        self.assertEqual(p.pragmas[0].arguments, ['S', 'K2'])


class DefinesTest(unittest.TestCase):
    """Category: Lexing, preprocessing and error line numbers / カテゴリ: 字句解析・前処理・エラー行番号

    Macros given with IDLParser(defines=...) (issue #120).
    IDLParser(defines=...) で与えるマクロ(#120)。
    """

    IDL = ('#ifdef USE_B\nstruct B { long b[N]; };\n#else\nstruct A {};\n#endif\n')

    def test_dict(self):
        """A dict gives names and values.

        dict で名前と値を与える。
        """
        g = parser.IDLParser(defines={'USE_B': '', 'N': 3}).load(self.IDL)
        self.assertEqual(g.struct_by_name('B').members[0].type.name, 'long [3]')
        self.assertIsNone(g.struct_by_name('A'))

    def test_list(self):
        """A list gives names defined as 1.

        list で 1 として定義される名前を与える。
        """
        g = parser.IDLParser(defines=['USE_B', 'N']).load(self.IDL)
        self.assertEqual(g.struct_by_name('B').members[0].type.name, 'long [1]')

    def test_not_given(self):
        """Without defines, nothing is defined.

        defines を与えなければ何も定義されない。
        """
        self.assertEqual(struct_names(self.IDL), ['A'])

    def test_overridden_by_idl(self):
        """#undef and #define in the IDL win over defines.

        IDL の #undef と #define が defines より優先される。
        """
        g = parser.IDLParser(defines={'USE_B': '', 'N': 3}).load('#undef N\n#define N 7\n' + self.IDL)
        self.assertEqual(g.struct_by_name('B').members[0].type.name, 'long [7]')

    def test_invalid_name(self):
        """An invalid macro name is a ValueError.

        不正なマクロ名は ValueError になる。
        """
        with self.assertRaises(ValueError):
            parser.IDLParser(defines={'1X': ''}).load('struct A {};')


if __name__ == '__main__':
    unittest.main()
