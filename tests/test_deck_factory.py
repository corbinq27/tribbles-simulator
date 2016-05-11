# -*- coding: utf-8 -*-

import unittest
from deck_factory import Card, Power, DeckFactory


class TestDeckFactory(unittest.TestCase):
    """Basic test cases."""

    def test_card_creation(self):
        p = Power.Poison
        c = Card(1, p, None)
        self.assertTrue(c)

    def test_card_from_string_function(self):

        df = DeckFactory("TestName")
        card_example = "9 1 Tribble - Go"
        count = 0
        for each_card in df.convert_string_to_cards(card_example):
            count += 1
            self.assertEqual(each_card.denomination, 1)
            self.assertEqual(each_card.power, Power.Go)
        self.assertEqual(count, 9)

if __name__ == '__main__':
    unittest.main()