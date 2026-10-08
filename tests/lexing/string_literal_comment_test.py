"""Regression tests for issue #50.

"//" and "/*" inside a string literal were taken as comments, so the rest of
the line was dropped. Depending on the IDL this silently lost a const, made
load() never return, or raised a syntax error for an annotation.
"""
import os
import subprocess
import sys
import tempfile
import unittest
from idl_parser import parser
from idl_parser.exception import InvalidIDLSyntaxError
from tests import support


def load(idl):
    return parser.IDLParser().load(idl)


ROOT = support.ROOT

CHILD = '''
import sys
from idl_parser import parser
try:
    parser.IDLParser().load(sys.argv[1])
except Exception:
    pass
'''


def load_with_timeout(idl, seconds=20):
    """load(), but fail instead of hanging the whole test run.

    The hang in issue #50 also kept growing a list, so it is first tried
    in a child process that can be killed.
    """
    env = dict(os.environ)
    env['PYTHONPATH'] = ROOT + os.pathsep + env.get('PYTHONPATH', '')
    try:
        subprocess.run([sys.executable, '-c', CHILD, idl], cwd=ROOT, env=env,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       timeout=seconds)
    except subprocess.TimeoutExpired:
        raise AssertionError('load() did not return: %r' % idl)
    return load(idl)


def consts(g, module='M'):
    return [(c.name, c.value) for c in g.module_by_name(module).consts]


class Issue50Test(unittest.TestCase):
    """Category: Lexing, preprocessing and error line numbers / カテゴリ: 字句解析・前処理・エラー行番号

    "//" and "/*" inside string literals are not comments (issue #50).
    文字列リテラル内の "//" と "/*" はコメントではない(#50)。
    """

    def test_url_const_is_kept(self):
        """"//" in a string is not taken as a comment, so a URL const is kept.

        文字列中の // がコメント扱いされず、URL の const が残る。
        """
        g = load('''module M {
  const string URL = "http://example.com";
  const long N = 1;
};''')
        self.assertEqual(consts(g), [('URL', '"http://example.com"'), ('N', '1')])

    def test_one_line_idl_does_not_hang(self):
        """load() does not hang on a one-line IDL with "//" or "/*" in a string.

        文字列中の // や /* を含む1行 IDL で load() が止まらない。
        """
        cases = {
            'module M { const string S = "http://x"; };': '"http://x"',
            'module M { const string S = "a/*b*/c"; };': '"a/*b*/c"',
            'module M { const string S = "a/*b"; };': '"a/*b"',
            "module M { const char C = '/'; };": "'/'",
        }
        for idl, value in cases.items():
            with self.subTest(idl):
                g = load_with_timeout(idl)
                self.assertEqual(consts(g), [(consts(g)[0][0], value)])

    def test_escaped_quote_in_string(self):
        """A string with an escaped ".

        エスケープした " を含む文字列。
        """
        g = load_with_timeout(r'module M { const string S = "a\"//b"; const long N = 1; };')
        self.assertEqual(consts(g), [('S', r'"a\"//b"'), ('N', '1')])

    def test_punctuation_in_string_is_untouched(self):
        """, ; = ( ) { } : inside a string are left unchanged.

        文字列中の , ; = ( ) { } : が変更されない。
        """
        g = load_with_timeout('module M { const string S = "a,b;c=d(e){f}:g"; };')
        self.assertEqual(consts(g), [('S', '"a,b;c=d(e){f}:g"')])

    def test_annotation_arguments(self):
        """"//" in a string argument of an annotation is kept.

        アノテーション引数の文字列中の // が保持される。
        """
        g = load('module M { @verbatim(language="c++", text="// x") const long C = 3; };')
        a = g.module_by_name('M').const_by_name('C').annotation_by_name('verbatim')
        self.assertEqual(a.params, {'language': '"c++"', 'text': '"// x"'})

        g = load('module M { struct S { @unit("m//s") double v; }; };')
        v = g.module_by_name('M').struct_by_name('S').members[0]
        self.assertEqual(v.annotation_by_name('unit').args, ['"m//s"'])

    def test_comments_are_still_removed(self):
        """Normal // and /* */ comments are still removed.

        通常の // と /* */ コメントは従来どおり除去される。
        """
        g = load('''module M {
  // const long A = 1;
  const string S = "x"; // "trailing" comment
  /* const long B = 2; "*/ const long C = 3; /* multi
     line "comment" */ const long D = 4;
};''')
        self.assertEqual(consts(g), [('S', '"x"'), ('C', '3'), ('D', '4')])

    def test_string_literal_in_included_file(self):
        """"//" in a string is also kept in an included file.

        include したファイルでも文字列中の // が保持される。
        """
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, 'inc.idl'), 'w') as f:
                f.write('module I { const string U = "http://example.com"; };\n')
            g = parser.IDLParser(idl_dirs=[d]).load(
                '#include "inc.idl"\nmodule M { const long N = 1; };')
        self.assertEqual(consts(g, 'I'), [('U', '"http://example.com"')])

    def test_unterminated_input_raises(self):
        """An unterminated string or definition raises an error instead of hanging.

        終端していない文字列・定義でエラー(停止しない)。
        """
        for idl in ['module M { const string S = "x"',
                    'module M { const string S = "x',
                    'module M { const long N = 1']:
            with self.subTest(idl):
                with self.assertRaises(InvalidIDLSyntaxError):
                    load_with_timeout(idl)


if __name__ == '__main__':
    unittest.main()
