#!/usr/bin/env python3

import unittest
import ed
import sys

class TestEdInsert(unittest.TestCase):

    def test_insert_empty_nocursor(self):
        e = ed.editor()
        e.text = []
        e.newText = [["hello"]]
        e.insert([])
        self.assertEqual(e.text, [["hello"]])
        self.assertEqual(e.appendix, [])

    def test_insert_empty_twolines(self):
        e = ed.editor()
        e.text = []
        e.newText = [["hello"], ["goodbye"]]
        e.insert([0])
        self.assertEqual(e.text, [["hello"], ["goodbye"]])
        self.assertEqual(e.appendix, [])

    def test_insert_before_text(self):
        e = ed.editor()
        e.text = []
        e.newText = [["hello"]]
        e.insert([])
        self.assertEqual(e.text, [["hello"]])
        self.assertEqual(e.appendix, [])

if __name__ == "__main__":
    unittest.main()
