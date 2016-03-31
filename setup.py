from setuptools import setup, find_packages
import sys


setup(name='idl_parser',
      version='0.0.1',
      url = 'http://www.sugarsweetrobotics.com/',
      author = 'ysuga',
      author_email = 'ysuga@ysuga.net',
      description = 'OMG IDL Parser',
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
