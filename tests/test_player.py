# -*- coding: utf-8 -*-

import unittest
import os
from player import Player
from deck import Power, Card, Deck
import copy

class TestPlayer(unittest.TestCase):
    """Basic test cases."""

    def test_deck_import(self):
        test_deck_path = os.path.join("..", "decks", "testdeckold.json")
        p = Player("dude", test_deck_path, 5)

        #top card of test deck is 100 tribbles rescue
        self.assertEqual(p.deck.deck[0].denomination, 100)
        self.assertEqual(p.deck.deck[0].power, Power.Rescue)

        #draw that card
        p.action_draw_card()

        #only card in hand should be that card

        self.assertEqual(p.hand.deck[0].denomination, 100)
        self.assertEqual(p.hand.deck[0].power, Power.Rescue)

    def test_draw_card(self):
        test_deck_path = os.path.join("..", "decks", "testdeckold.json")
        p = Player("dude", test_deck_path, 5)

        #what is the top card of the deck?
        top_card_of_deck = p.deck.deck[0]

        #do the draw
        p.action_draw_card()

        #that card should now be the only card in the hand deck.
        self.assertEqual(len(p.hand.deck), 1)

        #it should be the same card as seen before.
        self.assertEqual(top_card_of_deck, p.hand.get_top_card_and_remove_card())

    def test_play_card(self):
        test_deck_path = os.path.join("..", "decks", "testdeckold.json")
        p = Player("dude", test_deck_path, 5)

        # what is the top card of the deck?
        top_card_of_deck = p.deck.deck[0]

        # do the draw
        p.action_draw_card()

        # play card in hand
        p.action_play_card(p.hand.deck[0])

        # hand should be empty
        self.assertEqual(len(p.hand.deck), 0)

        # play pile should be one card in length
        self.assertEqual(len(p.play_pile.deck), 1)

        # only card in play pile should be the same card as top_card_of_deck from before
        self.assertEqual(p.play_pile.get_top_card_and_remove_card(), top_card_of_deck)

    def test_get_poisoned(self):
        test_deck_path = os.path.join("..", "decks", "testdeckold.json")
        p = Player("dude", test_deck_path, 5)

        #top card of test deck is 100 tribbles rescue
        self.assertEqual(p.deck.deck[0].denomination, 100)
        self.assertEqual(p.deck.deck[0].power, Power.Rescue)

        #that card gets poisoned.
        self.assertEqual(p.action_get_poisoned(), 100)

        #only card in hand should be the discard pile
        self.assertEqual(p.discard_pile.deck[0].denomination, 100)
        self.assertEqual(p.discard_pile.deck[0].power, Power.Rescue)

    def test_end_round_not_out(self):
        test_deck_path = os.path.join("..", "decks", "testdeckold.json")
        p = Player("dude", test_deck_path, 5)

        size_of_deck = len(p.deck.deck)

        p.action_draw_card()
        p.action_draw_card()

        p.action_play_card(p.hand.deck[0])

        card_in_hand = p.hand.deck[0]

        p.action_end_round(1)

        self.assertEqual(p.score["round1"], 0)
        self.assertEqual(p.discard_pile.get_top_card_and_remove_card(), card_in_hand)
        self.assertEqual(len(p.hand.deck), 0)
        self.assertEqual(len(p.play_pile.deck), 0)
        self.assertEqual(len(p.deck.deck), size_of_deck - 1)


    def test_end_round_went_out(self):
        test_deck_path = os.path.join("..", "decks", "testdeckold.json")
        p = Player("dude", test_deck_path, 5)

        size_of_deck = len(p.deck.deck)

        p.action_draw_card()

        p.action_play_card(p.hand.deck[0])

        denomination_of_play_pile_card = p.play_pile.deck[0].denomination

        p.action_end_round(1, is_out=True)

        self.assertEqual(p.score["round1"], denomination_of_play_pile_card)
        self.assertEqual(len(p.hand.deck), 0)
        self.assertEqual(len(p.play_pile.deck), 0)
        self.assertEqual(len(p.deck.deck), size_of_deck)

    def test_discard_power(self):
        test_deck_path = os.path.join("..", "decks", "testdeckold.json")
        p = Player("dude", test_deck_path, 5)

        p.action_draw_card()

        card_in_hand = p.hand.deck[0]

        p.action_use_discard_power(card_in_hand)

        self.assertEqual(len(p.hand.deck), 0)
        self.assertEqual(p.discard_pile.deck[0], card_in_hand)

    def test_rescue_power(self):
        test_deck_path = os.path.join("..", "decks", "testdeckold.json")
        p = Player("dude", test_deck_path, 5)

        top_card_of_deck = copy.deepcopy(p.deck.deck[0])

        #make a copy of the top_card_of_deck but make its denomination *10 higher.
        new_card = copy.deepcopy(p.deck.deck[0])

        new_card.denomination = (top_card_of_deck.denomination * 10)

        p.discard_pile.add_card(new_card)

        p.action_rescue_card(new_card)

        latest_top_card_of_deck = p.deck.get_top_card_and_remove_card()
        self.assertEqual(latest_top_card_of_deck.denomination, top_card_of_deck.denomination * 10)
        self.assertEqual(latest_top_card_of_deck.power, top_card_of_deck.power)

    def test_state_of_all_deterministic_actions(self):
        test_deck_path = os.path.join("..", "decks", "test_tree_deck.json")
        p = Player("dude", test_deck_path, 5)

        for i in range(0, 20):
            p.action_draw_card()

        p.discard_pile.add_card(Card(1000, Power.Rescue, "none"))
        p.discard_pile.add_card(Card(10000, Power.Go, "none"))

        current_card = Card(1, Power.Go, "nobody")

        tree = p.state_of_all_deterministic_actions(current_card)
        tree.print_this_tree()

    def test_get_all_end_nodes(self):
        """
        This tree is expected to have four "end nodes."  We go through
        and create a list of the same cards and remove each from a deck
        made of the end node cards.  If the deck is empty then the test passes.
        :return:
        """
        test_deck_path = os.path.join("..", "decks", "test_tree_deck.json")
        p = Player("dude", test_deck_path, 5)

        for i in range(0, 20):
            p.action_draw_card()

        p.discard_pile.add_card(Card(1000, Power.Rescue, "dude"))
        p.discard_pile.add_card(Card(10000, Power.Go, "dude"))

        current_card = Card(1, Power.Go, "dude")

        tree = p.state_of_all_deterministic_actions(current_card)
        list_of_end_nodes = tree.get_all_end_nodes()
        deck_of_cards_in_end_nodes = Deck("dude")
        for each_node in list_of_end_nodes:
            deck_of_cards_in_end_nodes.add_card(each_node.value[0])

        self.assertEqual(len(list_of_end_nodes), 4)
        list_of_expected_cards = [Card(10000, Power.Rescue, "dude"),
                                  Card(100000, Power.Clone, "dude"),
                                  Card(100000, Power.Clone, "dude"),
                                  Card(100, Power.Poison, "dude")]

        for each_card in list_of_expected_cards:
            deck_of_cards_in_end_nodes.remove_card(each_card)

        self.assertTrue(deck_of_cards_in_end_nodes.is_empty())

    def test_get_state_minimum_cards_in_hand(self):
        """
        This tree is expected to have four "end nodes."  We go through
        and create a list of the same cards and remove each from a deck
        made of the end node cards.  If the deck is empty then the test passes.
        :return:
        """
        test_deck_path = os.path.join("..", "decks", "test_tree_deck.json")
        p = Player("dude", test_deck_path, 5)

        for i in range(0, 20):
            p.action_draw_card()

        p.discard_pile.add_card(Card(1000, Power.Rescue, "dude"))
        p.discard_pile.add_card(Card(10000, Power.Go, "dude"))

        current_card = Card(1, Power.Go, "dude")
        best_state = p.get_state_minimum_cards_in_hand(current_card, 6666)

        self.assertEqual(131110, best_state.value[1].play_pile.get_denomination_sum())

    def test_get_players_score(self):
        p = Player("what", None, 5)
        p.score["round1"] = 100
        p.score["round2"] = 1000
        p.score["round3"] = 10000
        p.score["round4"] = 1
        p.score["round5"] = 100000

        self.assertEqual(p.get_players_score(), 111101)

    def test_player_cannot_play(self):
        p = Player('what', None, 5)
        last_card = Card(1000, Power.Rescue, "blah")
        p1 = p.get_state_minimum_cards_in_hand(last_card, 1)

    def test_player_copy(self):
        test_deck_path = os.path.join("..", "decks", "testdeckold.json")
        p = Player("dude", test_deck_path, 5)
        pcopy = p.get_copy()

        # what is the top card of the deck?
        top_card_of_deck = pcopy.deck.deck[0]

        # do the draw
        pcopy.action_draw_card()

        # play card in hand
        pcopy.action_play_card(pcopy.hand.deck[0])

        # hand should be empty
        self.assertEqual(len(pcopy.hand.deck), 0)

        # play pile should be one card in length
        self.assertEqual(len(pcopy.play_pile.deck), 1)

        # only card in play pile should be the same card as top_card_of_deck from before
        self.assertEqual(pcopy.play_pile.get_top_card_and_remove_card(), top_card_of_deck)

    def test_copy_player(self):
        test_deck_path = os.path.join("..", "decks", "testdeckold.json")
        p = Player("dude", test_deck_path, 5)

        p_copy = p.get_copy()

        #top card of test deck is 100 tribbles rescue
        self.assertEqual(p_copy.deck.deck[0].denomination, 100)
        self.assertEqual(p_copy.deck.deck[0].power, Power.Rescue)

        #draw that card
        p_copy.action_draw_card()

        #only card in hand should be that card

        self.assertEqual(p_copy.hand.deck[0].denomination, 100)
        self.assertEqual(p_copy.hand.deck[0].power, Power.Rescue)

if __name__ == '__main__':
    unittest.main()