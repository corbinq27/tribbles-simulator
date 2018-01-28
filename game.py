from deck import Deck, Card, Power
from player import Player
import os
import json
import random
import copy

class Game:

    def __init__(self, game_to_import = None):
        self.dict_of_players = {}
        self.number_of_games_to_play = 0
        self.game_file_path_local_copy = None

        if game_to_import != None:
            self.import_game(game_to_import)

    def import_game(self, game_file_path):
        """An example game might look like this:
            {
              "players":
              [
                        {
                          "deck_file" : "testdeck.json",
                          "player_name" : "player_1"
                        },
                        {
                          "deck_file" : "testdeck.json",
                          "player_name" : "player_2"
                        }
                ],

              "games_to_play": 10,
              "number_of_rounds": 5
            }
        """
        with open(game_file_path, "r") as fp:
            self.game_file_path_local_copy = game_file_path
            game_dict = json.load(fp)
            for i, each_item in enumerate(game_dict["players"]):
                deck_file_path = os.path.join("decks", each_item["deck_file"])
                player_to_add = Player(each_item["player_name"], deck_file_path, game_dict["number_of_rounds"])
                self.dict_of_players[i] = player_to_add
            self.number_of_games_to_play = game_dict["games_to_play"]

    def setup_game(self):
        """
        At the start of each game of tribbles, a player is determined to go first
        based on the value of a cut card in their deck.

        This must only be run after the initial game import.
        :return:
        """

    def get_best_player_to_poison(self, players_not_to_poison):
        """
        returns the player object for the player who has the highest average poison value
        """
        best_player = self.dict_of_players[0]

        for each_key in self.dict_of_players.keys():
            if self.dict_of_players[each_key] in players_not_to_poison:
                pass
            else:
                if self.dict_of_players[each_key].deck.get_expected_poison_value() > best_player.deck.get_expected_poison_value():
                    best_player = self.dict_of_players[each_key]

        return best_player

    def run(self):

        player_keys = []
        last_card_played = None
        is_chain_broken = False

        for i in range(0,len(self.dict_of_players)):
            player_keys.append(i)
        #play all the games
        for i in range(0, self.number_of_games_to_play):
            # setup (shuffle)
            self.import_game(self.game_file_path_local_copy)
            for each_key in player_keys:
                self.dict_of_players[each_key].deck.shuffle()
                for n in range(0, 7):
                    self.dict_of_players[each_key].action_draw_card()
            round = 1
            while round <= 5:
                    for each_key in player_keys:
                        if round >= 6:
                            break
                        print("It is player %s turn." % self.dict_of_players[each_key].name)
                        if last_card_played != None:
                            print("The last card played is %s %s" % (last_card_played.denomination, last_card_played.power ))
                        begining_size_of_hand = len(self.dict_of_players[each_key].hand.deck)
                        print("the player has %s cards in hand." % begining_size_of_hand)
                        expected_value_of_poison = self.get_best_player_to_poison([self.dict_of_players[each_key]]).deck.get_expected_poison_value()
                        print("the expected value of a poison is %s" % expected_value_of_poison)
                        print("the player has %s cards in deck." % len(self.dict_of_players[each_key].deck.deck))
                        new_instance_of_player = self.dict_of_players[each_key].get_state_minimum_cards_in_hand(last_card_played, expected_value_of_poison, is_chain_broken).value[1]

                        #If the player didn't play a card on his or her turn, draw a card
                        if begining_size_of_hand == len(new_instance_of_player.hand.deck):
                            print("the player is drawing a card since he didn't play a card.")
                            #deal with getting decked
                            if len(new_instance_of_player.deck.deck) <= 0:
                                print("player is decked.  Moving hand to discard pile.")
                                if not new_instance_of_player.hand.is_empty():
                                    for _ in range(0, len(new_instance_of_player.hand.deck)):
                                        get_card = new_instance_of_player.hand.get_top_card_and_remove_card()
                                        new_instance_of_player.discard_pile.add_card(get_card)
                            else:
                                print("the card drawn is %s %s" % (new_instance_of_player.deck.get_top_card_of_deck().denomination, new_instance_of_player.deck.get_top_card_of_deck().power))
                                new_instance_of_player.action_draw_card()

                                #if the player drew something he can play, check for that.
                                new_new_instance_of_player = new_instance_of_player.get_state_minimum_cards_in_hand(last_card_played, expected_value_of_poison, is_chain_broken).value[1]
                                if (begining_size_of_hand + 1) == len(new_new_instance_of_player.hand.deck):
                                    is_chain_broken = True
                                #else we assume one or more cards were played and therefore check for poison points and
                                #take note of which card was last played.
                                else:
                                    is_chain_broken = False
                                    last_card_played = new_new_instance_of_player.play_pile.get_top_card_of_deck()
                                    if new_new_instance_of_player.additional_action == Power.Poison:
                                        poison_value = self.get_best_player_to_poison([self.dict_of_players[each_key]]).action_get_poisoned()
                                        new_new_instance_of_player.score["round%s" % round] += poison_value
                                    new_new_instance_of_player.action_end_turn()
                                    self.dict_of_players.pop(each_key)
                                    self.dict_of_players[each_key] = copy.deepcopy(new_new_instance_of_player)
                        # else we assume one or more cards were played and therefore check for poison points and
                        # take note of which card was last played.
                        else:
                            is_chain_broken = False
                            last_card_played = new_instance_of_player.play_pile.get_top_card_of_deck()
                            if new_instance_of_player.additional_action == Power.Poison:
                                poison_value = self.get_best_player_to_poison(
                                    [self.dict_of_players[each_key]]).action_get_poisoned()
                                new_instance_of_player.score["round%s" % round] += poison_value
                            new_instance_of_player.action_end_turn()
                            self.dict_of_players.pop(each_key)
                            self.dict_of_players[each_key] = copy.deepcopy(new_instance_of_player)
                        print("status: player %s hand: %s" % (self.dict_of_players[each_key].name, self.dict_of_players[each_key].hand.pretty_print()))
                        print("status: player %s play_pile %s" % (self.dict_of_players[each_key].name, self.dict_of_players[each_key].play_pile.pretty_print(4)))
                        print("last played card: %s" % last_card_played)
                        #print("status: player %s deck %s" % (self.dict_of_players[each_key].name, self.dict_of_players[each_key].deck.pretty_print()))

                        if self.dict_of_players[each_key].hand.is_empty():

                            self.dict_of_players[each_key].action_end_round(round, is_out=True)
                            last_card_played = None
                            is_chain_broken = False
                            for all_keys in player_keys:
                                if self.dict_of_players[all_keys] != self.dict_of_players[each_key]:
                                    self.dict_of_players[all_keys].action_end_round(round)
                                    print("Round %s score for %s is %s" % (
                                round, self.dict_of_players[each_key].name, self.dict_of_players[each_key].score["round%s" % round]))
                            round += 1

                            for each_key in player_keys:
                                self.dict_of_players[each_key].deck.shuffle()
                                for n in range(0, 7):
                                    self.dict_of_players[each_key].action_draw_card()
            for i in range(0, len(self.dict_of_players)):
                for each_round in range(0,len(self.dict_of_players[i].score)):
                    print("Player %s final score in round %s : %s" % (i+1, each_round+1, self.dict_of_players[i].score["round%s" % (each_round+1)]))


def main():
    game_file_path = os.path.join("games", "test_game.json")
    game = Game(game_file_path)
    game.run()

if __name__ == '__main__':
    main()
