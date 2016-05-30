from deck import Deck, Card, Power
import copy

class Player:

    def __init__(self, name, deck_file_path, number_of_rounds):
        self.name = name
        self.deck = Deck(self.name, deck_file_path)
        self.hand = Deck(self.name)
        self.play_pile = Deck(self.name)
        self.discard_pile = Deck(self.name)
        self.out_of_play_pile = Deck(self.name)
        self.can_go_out = False
        self.additional_action = None

        self.score = {}
        for i in range(0, number_of_rounds):
            self.score["round%s" % (i+1)] = 0 # { "round1" : 0, "round2" : 0}

    #methods to get the state of a player

    def state_all_possible_actions(self, last_played_card):
        """
        Returns a list of all possible actions the player can take.
        Possible Actions:
        DRAW_A_CARD: the player has more than one card in his deck.
        PLAY_A_CARD: given the last played card, this is returned if the player has a legal card to play.
        CAN_GO_OUT: given the last played card, this is returned if the player can empty his hand.  This will go through
                    all of the actions available to him in a single turn, and if he can deterministically empty his
                    hand, this is returned.

        """
        pass #TODO

    def state_of_all_deterministic_actions(self, last_card_played):
        """
        Creates a tree of tuples of the form (card_played, player) where a tuple represents the card played and the
        player object that would exist after that card is played.  We generate the entire tree of all deterministic
        actions and return it.
        """
        root = GameStateNode(None, self)
        for each_card in self.hand.deck:
            if each_card.is_playable(last_card_played):
                player_state = copy.deepcopy(self)
                player_state.action_play_card(each_card)
                root.add_child(each_card.denomination, player_state)
        # the root now has all the first level children and the player will state in "self.additional_action" some
        # additional follow-up action that could cause the player to play an additional card.  To deal with this,
        # we recursively go through each player state and populate this root with all possible follow-up actions.
        for each_child in root.depth_first():
            if each_child.value[1] == Power.Rescue:


    def _populate_actionable_followup(self, game_node):


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

        if the played card is a card that has an actionable power, then set self.additional_action to the power enum.
        """
        card_to_play = self.hand.remove_card(card)
        self.play_pile.add_card(card_to_play)
        if card_to_play.is_actionable_power():
            self.additional_action = card_to_play.power

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
          in hand.  It does NOT check for this.  If this occurs, the behavior is undefined.

        This does NOT force a round end if the hand is now 0 length.
        """
        card_removed = self.hand.remove_card(card)
        self.discard_pile.add_card(card)

    def action_rescue_card(self, card):
        """
        The Rescue power, when executed, returns a card to the top of the deck.  If that card can be played, it may
        be played if the player so decides.

        This function simply finds a copy of the passed in card from the discard pile and places it on top of the
        deck.  It does NOT somehow then play that card if it is possible.  It also assumes this action is only
        executed when the card passed into this function is actually in the discard pile.  If it is not, then the
        behavior is undefined.
        """
        self.discard_pile.remove_card(card)
        self.deck.add_card(card)

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

class GameStateNode:
    def __init__(self, card, player):
        self.value = (card, player)
        self._children = []

    def __repr__(self):
        return 'Node({!r})'.format(self.value)

    def add_child(self, node):
        self._children.append(node)

    def __iter__(self):
        return iter(self._children)

    def depth_first(self):
        yield self
        for c in self:
            yield from c.depth_first()
