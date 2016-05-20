# -*- coding: utf-8 -*-

import unittest
import os
from player import Player
from deck import Power


class TestPlayer(unittest.TestCase):
    """Basic test cases."""

    def test_deck_import(self):
        test_deck_path = os.path.join("..", "decks", "testdeck.json")
        p = Player("dude", test_deck_path, 5)

        #top card of test deck is 100 tribbles rescue
        self.assertEqual(p.deck.deck[0].denomination, 100)
        self.assertEqual(p.deck.deck[0].power, Power.Rescue)

        #draw that card
        p.action_draw_card()

        #only card in hand should be that card

        self.assertEqual(p.hand.deck[0].denomination, 100)
        self.assertEqual(p.hand.deck[0].power, Power.Rescue)

    def test_get_poisoned(self):
        test_deck_path = os.path.join("..", "decks", "testdeck.json")
        p = Player("dude", test_deck_path, 5)

        #top card of test deck is 100 tribbles rescue
        self.assertEqual(p.deck.deck[0].denomination, 100)
        self.assertEqual(p.deck.deck[0].power, Power.Rescue)

        #that card gets poisoned.
        self.assertEqual(p.action_get_poisoned(), 100)

        #only card in hand should be the discard pile
        self.assertEqual(p.discard_pile.deck[0].denomination, 100)
        self.assertEqual(p.discard_pile.deck[0].power, Power.Rescue)
if __name__ == '__main__':
    unittest.main()