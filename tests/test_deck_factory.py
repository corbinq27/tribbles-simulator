# -*- coding: utf-8 -*-

import unittest
import os
from deck import Card, Power, Deck


class TestDeckFactory(unittest.TestCase):
    """Basic test cases."""

    def test_card_creation(self):
        p = Power.Poison
        c = Card(1, p, None)
        self.assertTrue(c)

    def test_card_from_string_function(self):

        df = Deck("TestName")
        card_example = "9 1 Tribble - Go"
        count = 0
        for each_card in df.convert_string_to_cards(card_example):
            count += 1
            self.assertEqual(each_card.denomination, 1)
            self.assertEqual(each_card.power, Power.Go)
        self.assertEqual(count, 9)

    def test_deck_import(self):
        df = Deck("Some Dude")
        test_deck_path = os.path.join("..", "decks", "testdeck.json")
        df.deck_import(test_deck_path)

        test_output_path = os.path.join("..", "decks", "testdeckimport.txt")
        with open(test_output_path, "r") as fp:
            expected_output = fp.read()

            for each_card in df.deck:
                card = "%s tribbles %s\n" % (each_card.denomination, each_card.power)
                expected_output = expected_output.replace(card, "")

            self.assertEqual(expected_output, "")


    def test_deck_import_on_init(self):

        test_deck_path = os.path.join("..", "decks", "testdeck.json")
        df = Deck("Some Dude", test_deck_path)

        test_output_path = os.path.join("..", "decks", "testdeckimport.txt")
        with open(test_output_path, "r") as fp:
            expected_output = fp.read()

            for each_card in df.deck:
                card = "%s tribbles %s\n" % (each_card.denomination, each_card.power)
                expected_output = expected_output.replace(card, "")

            self.assertEqual(expected_output, "")

    def test_remove_top_card_object(self):
        test_deck_path = os.path.join("..", "decks", "testdeck.json")
        deck = Deck("Some Dude", test_deck_path)
        deck_size = len(deck.deck)
        card = deck.deck[0]
        deck.remove_card(card)
        self.assertEqual(deck_size, len(deck.deck) + 1)

    def test_remove_top_card_object(self):
        test_deck_path = os.path.join("..", "decks", "testdeck.json")
        deck = Deck("Some Dude", test_deck_path)
        deck_size = len(deck.deck)
        card = deck.get_top_card_and_remove_card()
        self.assertEqual(deck_size, len(deck.deck) + 1)

if __name__ == '__main__':
    unittest.main()