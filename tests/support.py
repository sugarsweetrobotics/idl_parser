"""Paths shared by the tests in the category packages under tests/."""
import os

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TESTS_DIR)
IDL_DIR = os.path.join(TESTS_DIR, 'idls')
