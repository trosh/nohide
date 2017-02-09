#!/usr/bin/env python3

import unittest
import ed
import random

class TestEdAddressing(unittest.TestCase):

    def test_abs_line(self):
        e = ed.editor()
        letters = "abcdefghij"
        e.text = [[c] for c in letters]
        for test in range(10):
            line = random.randrange(len(letters))
            e.parse(str(line+1))
            letter = letters[line]
            self.assertEqual(e.text[e.cursor], [letter])

    def test_abs_range(self):
        e = ed.editor()
        letters = "abcdefghij"
        e.text = [[c] for c in letters]
        for test in range(10):
            start = random.randrange(len(letters))
            end   = random.randrange(len(letters))
            if start > end:
                start, end = end, start
            gen = e.print([start, end])
            output = [ret for ret in gen]
            expected = [c+"\n" for c in letters[start:end+1]]
            self.assertEqual(output, expected)

if __name__ == "__main__":
    unittest.main()
