from setuptools import setup, find_packages
import sys



long_description = open('README.rst', 'r').read()


setup(name='idl_parser',
      version='0.0.8',
      url = 'http://www.sugarsweetrobotics.com/',
      author = 'ysuga',
      author_email = 'ysuga@ysuga.net',
      description = 'Very simple OMG IDL (Interface Definition Language) parser. This parses IDL files and outputs intermediate class objects.',
      long_description = long_description,
      download_url = 'https://github.com/sugarsweetrobotics/idl_parser',
      packages = ["idl_parser"],
      #py_modules = ["pepper_kinematics"],
      license = 'GPLv3',
      install_requires = [''],
      classifiers = [
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Scientific/Engineering',
        ],
      #test_suite = "foo_test.suite",
      #package_dir = {'': 'src'}
    )
