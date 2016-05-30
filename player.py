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

    def action_use_discard_power(self, card):
        """
        The discard power, when executed, discards a card from hand.

        This discards a copy of the card in parameters from hand.  This also assumes the card passed in is actually
          in hand.  It does NOT check for this.  Normal python exceptions will raise if the card isn't in hand.

        This does NOT force a round end if the hand is now 0 length.
        """
        card_removed = self.hand.remove_card(card)
        self.discard_pile.add_card(card)

    def action_end_round(self, round_number, is_out=False):
        """
        discards player's hand. Shuffles play pile into draw deck.

        if is_out set to True, then counts the play pile and adds the score from the play pile to this player's
        score (must pass in proper round_number to accomplish this as well).
        """
        if is_out:
            self.score["round%s" % round_number] = self.play_pile.get_denomination_sum()

        if not self.hand.is_empty():
            for _ in range(0, len(self.hand.deck)):
                get_card = self.hand.get_top_card_and_remove_card()
                self.discard_pile.add_card(get_card)

        if not self.play_pile.is_empty():
            for _ in range(0, len(self.play_pile.deck)):
                get_card = self.play_pile.get_top_card_and_remove_card()
                self.deck.add_card(get_card)
            self.deck.shuffle()


