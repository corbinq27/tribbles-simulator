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

    def test_deck_empty_at_instantiation(self):
        df = Deck("blah")
        self.assertTrue(df.is_empty())

    def test_deck_not_empty(self):
        test_deck_path = os.path.join("..", "decks", "testdeck.json")
        df = Deck("Some Dude", test_deck_path)
        self.assertFalse(df.is_empty())

    def test_deck_empty_after_filling(self):
        test_deck_path = os.path.join("..", "decks", "testdeck.json")
        df = Deck("Some Dude", test_deck_path)
        self.assertFalse(df.is_empty())
        while not df.is_empty():
            df.get_top_card_and_remove_card()
        self.assertTrue(df.is_empty())

    def test_denomination_sum(self):
        test_deck_path = os.path.join("..", "decks", "smalltestdeck.json")
        d = Deck("whatever", test_deck_path)
        deck_value = d.get_denomination_sum()
        self.assertEqual(deck_value, 140610)

    def test_shuffle_retains_deck_length(self):
        test_deck_path = os.path.join("..", "decks", "testdeck.json")
        deck = Deck("Some Dude", test_deck_path)
        deck_size = len(deck.deck)
        deck.shuffle()
        self.assertEqual(deck_size, len(deck.deck))

    def test_deck_retains_integrity_after_shuffle(self):
        test_deck_path = os.path.join("..", "decks", "testdeck.json")
        df = Deck("Some Dude", test_deck_path)
        df.shuffle()

        test_output_path = os.path.join("..", "decks", "testdeckimport.txt")
        with open(test_output_path, "r") as fp:
            expected_output = fp.read()

            for each_card in df.deck:
                card = "%s tribbles %s\n" % (each_card.denomination, each_card.power)
                expected_output = expected_output.replace(card, "")

            self.assertEqual(expected_output, "")

    def test_deck_shuffles(self):
        test_deck_path = os.path.join("..", "decks", "smalltestdeck.json")
        df = Deck("Some Dude", test_deck_path)
        df.shuffle(3)
        test_shuffle_output = os.path.join("..", "decks", "smalltestdeckshuffletest.txt")
        with open(test_shuffle_output, "r") as fp:
            expected_output = fp.readlines()
            for i in range(0,len(df.deck)):
                self.assertIn(str(df.deck[i].power), expected_output[i])
                self.assertIn(str(df.deck[i].denomination), expected_output[i])

    def test_is_playable_next_denom(self):
        last_card_played = Card(10, Power.Go, None)
        next_card = Card(100, Power.Rescue, None)
        self.assertTrue(next_card.is_playable(last_card_played))

    def test_is_playable_next_denom_again(self):
        last_card_played = Card(100, Power.Rescue, None)
        next_card = Card(1000, Power.Rescue, None)
        self.assertTrue(next_card.is_playable(last_card_played))

    def test_is_playable_one_after_big_money(self):
        last_card_played = Card(100000, Power.Discard, None)
        next_card = Card(1, Power.Bonus, None)
        self.assertTrue(next_card.is_playable(last_card_played))

    def test_is_playable_big_clone_after_big_money(self):
        last_card_played = Card(100000, Power.Discard, None)
        next_card = Card(100000, Power.Clone, None)
        self.assertTrue(next_card.is_playable(last_card_played))

    def test_is_playable_one_clone_after_big_money(self):
        last_card_played = Card(100000, Power.Discard, None)
        next_card = Card(1, Power.Clone, None)
        self.assertTrue(next_card.is_playable(last_card_played))

    def test_is_playable_negative_clone_tests(self):
        last_card_played = Card(100000, Power.Discard, None)
        next_card = Card(10, Power.Clone, None)
        self.assertFalse(next_card.is_playable(last_card_played))

        last_card_played = Card(100000, Power.Discard, None)
        next_card = Card(100, Power.Clone, None)
        self.assertFalse(next_card.is_playable(last_card_played))

        last_card_played = Card(100000, Power.Discard, None)
        next_card = Card(1000, Power.Clone, None)
        self.assertFalse(next_card.is_playable(last_card_played))

        last_card_played = Card(100000, Power.Discard, None)
        next_card = Card(10000, Power.Clone, None)
        self.assertFalse(next_card.is_playable(last_card_played))

    def test_is_playable_negative_denomination_tests(self):
        last_card_played = Card(100, Power.Rescue, None)
        next_card = Card(10, Power.Go, None)
        self.assertFalse(next_card.is_playable(last_card_played))

        last_card_played = Card(10000, Power.Clone, None)
        next_card = Card(10000, Power.Rescue, None)
        self.assertFalse(next_card.is_playable(last_card_played))

        last_card_played = Card(100000, Power.Clone, None)
        next_card = Card(100000, Power.Rescue, None)
        self.assertFalse(next_card.is_playable(last_card_played))

        last_card_played = Card(1, Power.Discard, None)
        next_card = Card(1, Power.Go, None)
        self.assertFalse(next_card.is_playable(last_card_played))

    def test_is_actionable_card(self):
        card = Card(100, Power.Go, None)
        self.assertTrue(card.is_actionable_power())

        card = Card(1000, Power.Rescue, None)
        self.assertTrue(card.is_actionable_power())

    def test_negative_is_actionable_card(self):
        card = Card(1, Power.Clone, None)
        self.assertFalse(card.is_actionable_power())

        card = Card(1000, Power.Skip, None)
        self.assertFalse(card.is_actionable_power())

    def test_all_unique_cards(self):
        test_deck_path = os.path.join("..", "decks", "smalltestdeck.json")
        df = Deck("Some Dude", test_deck_path)

        unique_cards = df.get_all_unique_cards()

        categorizations_only = []
        for each_card in unique_cards:
            categorizations_only.append(each_card.get_card_categorization())

        expected_categorizations_only_list = ["100 Power.Rescue", "10 Power.Go", "100 Power.Poison", "10000 Power.Go",
                                              "100000 Power.Clone"]

        self.assertEqual(categorizations_only, expected_categorizations_only_list)

if __name__ == '__main__':
    unittest.main()