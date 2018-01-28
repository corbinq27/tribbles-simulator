# -*- coding: utf-8 -*-

import unittest
import os
from player import Player
from deck import Power, Card, Deck
from game import Game

class TestGame(unittest.TestCase):
    """Basic test cases."""

    def test_create_game_object(self):
        game_file_path = os.path.join("..", "games", "test_game.json")
        game = Game(game_file_path)
        self.assertEqual(2, len(game.dict_of_players))
        self.assertEqual(game.dict_of_players[0].name, "player_1")
        self.assertEqual(game.dict_of_players[1].name, "player_2")
        self.assertEqual(len(game.dict_of_players[0].deck.deck), 100)
        #self.assertEqual(10, game.number_of_games_to_play)
        game.run()


if __name__ == '__main__':
    unittest.main()