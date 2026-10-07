import os
import unittest
from idl_parser import parser

idl_dir = 'idls/issue12_subpath'


class Issue12SubPathIncludeTest(unittest.TestCase):
    """#include with a sub path, e.g. "std/msg/Header.idl" (issue #12)."""

    def _check_header(self, m, struct_module, struct_name):
        header = m.module_by_name('std').module_by_name('msg').struct_by_name('Header')
        self.assertEqual([mem.name for mem in header.members], ['stamp', 'frame_id'])
        s = struct_module.struct_by_name(struct_name)
        self.assertEqual(s.member_by_name('header').type.full_path, 'std::msg::Header')

    def test_subpath_from_include_dir(self):
        """Sub path is resolved relative to an include directory."""
        parser_ = parser.IDLParser(idl_dirs=[idl_dir])
        path = os.path.join(idl_dir, 'sensor_msgs/msg/Imu.idl')
        with open(path, 'r') as f:
            m = parser_.load(f.read(), filepath=path)
        self._check_header(m, m.module_by_name('sensor_msgs').module_by_name('msg'), 'Imu')

    def test_subpath_relative_to_including_file(self):
        """Sub path is resolved relative to the including file, no include dirs needed."""
        parser_ = parser.IDLParser()
        parser_.parse(idls=[os.path.join(idl_dir, 'relative_include.idl')])
        m = parser_.global_module
        self._check_header(m, m.module_by_name('relative'), 'Stamped')

    def test_includes_returns_subpath_file(self):
        parser_ = parser.IDLParser(idl_dirs=[idl_dir])
        paths = parser_.includes(os.path.join(idl_dir, 'sensor_msgs/msg/Imu.idl'))
        self.assertEqual([os.path.normpath(p) for p in paths],
                         [os.path.normpath(os.path.join(idl_dir, 'std/msg/Header.idl'))])


if __name__ == '__main__':
    unittest.main()
