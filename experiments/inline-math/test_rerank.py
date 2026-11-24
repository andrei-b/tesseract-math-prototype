"""Exercise the choice gate independently of English model accuracy."""
import unittest
import cv2
import numpy as np
from rerank import shape, suggestion
from symbols import Symbol


class RerankTest(unittest.TestCase):
    def setUp(self):
        self.box = (0, 0, 48, 48)
        self.gray = {}
        self.bank = {}
        for label in ("z", "2"):
            gray = np.full((48, 48), 255, dtype=np.uint8)
            cv2.putText(gray, label, (4, 39), cv2.FONT_HERSHEY_SIMPLEX, 1.5, 0, 3)
            self.gray[label] = gray
            self.bank[label] = [shape(gray, self.box)]

    def predict(self, label, choices, word="2"):
        symbol = Symbol("2", self.box, False, False, word, choices)
        return suggestion(symbol, self.gray[label], self.bank)

    def test_ambiguous_position(self):
        self.assertEqual(self.predict("z", {"z": 75, "2": 80}), "z")
        self.assertEqual(self.predict("2", {"z": 75, "2": 80}), "2")

    def test_abstention(self):
        self.assertEqual(self.predict("z", {"2": 80}), "2")
        self.assertEqual(self.predict("z", {"z": 20, "2": 80}), "2")
        self.assertEqual(self.predict("z", {"z": 75, "2": 80}, "Bé2out"), "2")


if __name__ == "__main__":
    unittest.main()
