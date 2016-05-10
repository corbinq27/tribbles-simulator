# -*- coding: utf-8 -*-

import unittest
from deck_factory import Card, Power


class TestDeckFactory(unittest.TestCase):
    """Basic test cases."""

    def test_card_creation(self):
        p = Power.Poison
        c = Card(1, p, None)
        self.assertTrue(c)

if __name__ == '__main__':
    unittest.main()