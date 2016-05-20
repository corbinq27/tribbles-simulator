from deck import Deck, Card, Power

class Player:

    def __init__(self, name, deck_file_path, number_of_rounds):
        self.name = name
        self.deck = Deck(self.name, deck_file_path)
        self.hand = Deck(self.name)
        self.play_pile = Deck(self.name)
        self.discard_pile = Deck(self.name)
        self.out_of_play_pile = Deck(self.name)

        self.score = {}
        for i in range(0, number_of_rounds):
            self.score["round%s" % (i+1)] = 0 # { "round1" : 0, "round2" : 0}

    #methods to get the state of a player

    #actions the player can take

    def action_draw_card(self):
        """
        simply moves the top card of the deck to the hand.
        """
        card_to_hand = self.deck.get_top_card_and_remove_card()
        self.hand.add_card(card_to_hand)

    def action_play_card(self, card):
        """
        No checking is done to ensure the playing of the card is legal.

        Finds a copy of the passed in card in self.hand.  removes it from that deck.  adds that card to the top of
        the play pile.
        """
        card_to_play = self.hand.remove_card(card)
        self.play_pile.add_card(card_to_play)

    def action_get_poisoned(self):
        """
        Discard the top card of the deck and return the denomination of the card.
        """
        card_to_discard = self.deck.get_top_card_and_remove_card()
        denomination = card_to_discard.denomination
        self.discard_pile.add_card(card_to_discard)
        return denomination
