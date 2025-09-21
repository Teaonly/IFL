import unittest
from IFL.utils import do_search_replace

class TestSearchReplace(unittest.TestCase):
    def test_do_search_replace_single_block(self):
        original = "line1\nline2\nline3\n"
        blocks = """<<<<<<< SEARCH
line2
=======
new_line2\n>>>>>>> REPLACE"""
        success, result = do_search_replace(original, blocks)
        self.assertTrue(success)
        self.assertEqual(result, "line1\nnew_line2\nline3\n")

    def test_do_search_replace_multiple_blocks(self):
        original = "a\nb\nc\nd\n"
        blocks = """<<<<<<< SEARCH
b
=======
B\n>>>>>>> REPLACE
<<<<<<< SEARCH
c
=======
C\n>>>>>>> REPLACE"""
        success, result = do_search_replace(original, blocks)
        self.assertTrue(success)
        self.assertEqual(result, "a\nB\nC\nd\n")

    def test_do_search_replace_no_match(self):
        original = "foo\nbar\nbaz\n"
        blocks = """<<<<<<< SEARCH
notfound
=======
whatever\n>>>>>>> REPLACE"""
        success, result = do_search_replace(original, blocks)
        self.assertFalse(success)
        self.assertIn("Cannot find matching context", result)

    def test_do_search_replace_malformed_missing_search(self):
        original = "x\ny\nz\n"
        blocks = """=======
replace\n>>>>>>> REPLACE"""
        success, result = do_search_replace(original, blocks)
        self.assertFalse(success)
        self.assertIn("missing <<<<<<< SEARCH", result)

    def test_do_search_replace_malformed_empty_search(self):
        original = "x\ny\nz\n"
        blocks = """<<<<<<< SEARCH
=======
replace\n>>>>>>> REPLACE"""
        success, result = do_search_replace(original, blocks)
        self.assertFalse(success)
        self.assertIn("empty SEARCH section", result)

    def test_do_search_replace_malformed_missing_replace(self):
        original = "x\ny\nz\n"
        blocks = """<<<<<<< SEARCH
y\n=======
"""
        success, result = do_search_replace(original, blocks)
        self.assertFalse(success)
        self.assertIn("missing >>>>>>> REPLACE", result)

    def test_do_search_replace_similar_match(self):
        original = "int main() {\n    printf(\"hello\\n\");\n    return 0;\n}\n"
        blocks = """<<<<<<< SEARCH
    printf("hello\\n");
=======
    printf("HELLO\\n");\n>>>>>>> REPLACE"""
        success, result = do_search_replace(original, blocks)
        self.assertTrue(success)
        self.assertEqual(result, "int main() {\n    printf(\"HELLO\\n\");\n    return 0;\n}\n")


if __name__ == '__main__':
    unittest.main()
