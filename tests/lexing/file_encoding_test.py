"""Tests for issue #139: IDL files that are not UTF-8.

parse_idl() read files as the locale's encoding (UTF-8), so a file with a
comment in ISO-8859-1, such as OpenRTM-aist's RTC.idl, stopped with
UnicodeDecodeError, and so did the files including it. Files are now read
as UTF-8 and, if that fails, as Latin-1, which keeps every byte; IDL
identifiers are ASCII, so only comments may be garbled.
IDLParser(encoding=...) reads every file, included ones too, with the given
encoding.
"""
import os
import shutil
import tempfile
import unittest

from idl_parser import parser


LATIN1_IDL = ('// Copyright \xa9 2006 \xbbAIST\xab\n'
              'module RTC { struct S { long a; }; const string NAME = "caf\xe9"; };\n')
SJIS_IDL = '// 日本語のコメント\nmodule J { struct T { long b; }; };\n'


class FileEncodingTest(unittest.TestCase):
    """Category: Lexing and preprocessing / カテゴリ: 字句解析・前処理

    IDL files that are not UTF-8 (issue #139).
    UTF-8 以外の文字コードの IDL ファイル(#139)。
    """

    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dir)

    def write(self, name, text, encoding):
        path = os.path.join(self.dir, name)
        with open(path, 'wb') as f:
            f.write(text.encode(encoding))
        return path

    def test_latin1_file(self):
        """A Latin-1 file is read, and its literals keep their characters. / Latin-1 のファイルが読め、リテラルの文字も保たれる。"""
        path = self.write('rtc.idl', LATIN1_IDL, 'latin-1')
        p = parser.IDLParser()
        p.parse_idl(path)
        rtc = p.global_module.module_by_name('RTC')
        self.assertEqual(rtc.structs[0].name, 'S')
        self.assertEqual(rtc.const_by_name('NAME').value, '"caf\xe9"')

    def test_included_latin1_file(self):
        """A Latin-1 file included by a UTF-8 file is read. / UTF-8 のファイルから include した Latin-1 のファイルも読める。"""
        self.write('rtc.idl', LATIN1_IDL, 'latin-1')
        main = self.write('main.idl', '// あ\n#include "rtc.idl"\nmodule M { struct U { RTC::S s; }; };\n', 'utf-8')
        p = parser.IDLParser()
        p.parse_idl(main)
        u = p.global_module.module_by_name('M').structs[0]
        self.assertEqual(u.members[0].type.full_path, 'RTC::S')
        self.assertEqual(p.includes(main), [os.path.join(self.dir, 'rtc.idl')])

    def test_shift_jis_without_encoding(self):
        """A Shift_JIS file is read without an encoding (comments may be garbled). / Shift_JIS のファイルも encoding なしで読める(コメントは化ける)。"""
        path = self.write('j.idl', SJIS_IDL, 'shift_jis')
        p = parser.IDLParser()
        p.parse_idl(path)
        self.assertEqual(p.global_module.module_by_name('J').structs[0].name, 'T')

    def test_explicit_encoding(self):
        """IDLParser(encoding=...) reads the files, and literals, with it. / IDLParser(encoding=...) で指定した文字コードで読む。"""
        path = self.write('j.idl', SJIS_IDL + 'const wstring W = L"あ";\n', 'shift_jis')
        p = parser.IDLParser(encoding='shift_jis')
        self.assertEqual(p.encoding, 'shift_jis')
        p.parse_idl(path)
        self.assertEqual(p.global_module.const_by_name('W').value, 'L"あ"')

    def test_wrong_explicit_encoding(self):
        """A file that is not valid in the given encoding raises UnicodeDecodeError. / 指定した文字コードで読めないファイルは UnicodeDecodeError。"""
        path = self.write('rtc.idl', LATIN1_IDL, 'latin-1')
        with self.assertRaises(UnicodeDecodeError):
            parser.IDLParser(encoding='utf-8').parse_idl(path)

    def test_utf8_with_bom(self):
        """A UTF-8 file with a BOM is read. / BOM 付き UTF-8 のファイルも読める。"""
        path = self.write('bom.idl', '﻿module B { struct S { long a; }; };\n', 'utf-8')
        p = parser.IDLParser()
        p.parse_idl(path)
        self.assertEqual(p.global_module.modules[0].name, 'B')

    def test_line_numbers_and_newlines(self):
        """CRLF and form feeds do not change the line numbers. / CRLF や改ページ文字で行番号はずれない。"""
        path = self.write('nl.idl', 'module A {\r\n\x0c struct S { long a; };\r\n#pragma keylist S a\r\n};\r\n', 'utf-8')
        p = parser.IDLParser()
        p.parse_idl(path)
        self.assertEqual(p.pragmas[0].line_number, 3)


if __name__ == '__main__':
    unittest.main()
