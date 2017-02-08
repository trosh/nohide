#!/usr/bin/env python3

import unittest
import ed

class TestEdGlob(unittest.TestCase):

    def test_simple_pattern_delete(self):
        e = ed.editor()
        e.text = [["a"], ["b"], ["a"]]
        e.parse("g/a/d")
        self.assertEqual(e.text, [[["a\n"], "b"]])
        self.assertEqual(e.appendix, ["a\n"])

if __name__ == "__main__":
    unittest.main()
