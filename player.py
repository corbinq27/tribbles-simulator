from deck import Deck, Card, Power
import copy
import sys
import random


class Player:
    def __init__(self, name, deck_file_path, number_of_rounds):
        self.name = name
        self.deck = Deck(self.name, deck_file_path)
        self.hand = Deck(self.name)
        self.play_pile = Deck(self.name)
        self.discard_pile = Deck(self.name)
        self.out_of_play_pile = Deck(self.name)
        self.can_go_out = False
        self.last_played_card_denomination = 0
        self.last_played_card_power = None
        self._number_of_rounds = number_of_rounds
        self.additional_action = None

        self.score = {}
        for i in range(0, self._number_of_rounds):
            self.score["round%s" % (i + 1)] = 0  # { "round1" : 0, "round2" : 0}

    # ------------------------------------------------------------------
    # State tree / decision making
    # ------------------------------------------------------------------

    def state_of_all_deterministic_actions(self, last_card_played, is_chain_broken=False):
        """
        Creates a tree of tuples of the form (card_played, player) where a tuple represents the card played and the
        player object that would exist after that card is played.  We generate the entire tree of all deterministic
        actions and return it.
        """
        root = GameStateNode(None, self)

        for each_card in self.hand.get_all_unique_cards():
            if each_card.is_playable(last_card_played, is_chain_broken):
                player_state = self.get_copy()
                card_played = each_card.get_copy()
                player_state.action_play_card(card_played)
                root.add_child(GameStateNode(card_played, player_state))

        for each_child_node in root.children:
            self._populate_children_for_node(each_child_node)
        return root

    def _populate_children_for_node(self, node):
        last_played_card = node.value[0].get_copy()
        last_player_state = node.value[1].get_copy()
        if last_player_state.additional_action == Power.Rescue:
            if not last_player_state.discard_pile.is_empty():
                for each_card in last_player_state.discard_pile.get_all_unique_cards():
                    if each_card.is_playable(last_played_card):
                        last_player_state.action_play_card_from_discard_pile(each_card)
                        card_played = each_card.get_copy()
                        new_node = GameStateNode(card_played, last_player_state)
                        node.add_child(new_node)
                        self._populate_children_for_node(new_node)
        if last_player_state.additional_action == Power.Go:
            if not last_player_state.hand.is_empty():
                for each_card in last_player_state.hand.get_all_unique_cards():
                    if each_card.is_playable(last_played_card):
                        last_player_state.action_play_card(each_card)
                        card_played = each_card.get_copy()
                        new_node = GameStateNode(card_played, last_player_state)
                        node.add_child(new_node)
                        self._populate_children_for_node(new_node)

    def get_state_minimum_cards_in_hand(self, last_card_played, expected_value_of_poison, is_chain_broken=False):
        """
        Finds all the deterministic states the player can be in.  Looking only at
        nodes at the end of the tree (The nodes where the player has no more possible
        moves), returns the node where the player has the fewest cards in hand, the most
        expected bonus points, and, If a tie is determined, then then the state with the most
        cards in the discard pile is chosen.  If a tie remains, then the state with the
        largest sum of denominations in the play pile is performed. If a tie is still determined, then the node
        will be determined randomly from the final tie.
        """
        tree = self.state_of_all_deterministic_actions(last_card_played, is_chain_broken)
        list_of_all_final_outcomes = tree.get_all_end_nodes()

        best_state = list_of_all_final_outcomes[0]

        for each_state in list_of_all_final_outcomes:
            each_state_player_object = each_state.value[1]
            best_state_player_object = best_state.value[1]
            if len(each_state_player_object.hand.deck) < len(best_state_player_object.hand.deck):
                best_state = each_state
            elif len(each_state_player_object.hand.deck) == len(best_state_player_object.hand.deck):
                if each_state_player_object.additional_action == Power.Poison:
                    poison_value = expected_value_of_poison
                else:
                    poison_value = 0
                if (
                    each_state_player_object.get_players_score() + poison_value) > best_state_player_object.get_players_score():
                    best_state = each_state
                elif each_state_player_object.get_players_score() == best_state_player_object.get_players_score():
                    if len(each_state_player_object.discard_pile.deck) > len(
                            best_state_player_object.discard_pile.deck):
                        best_state = each_state
                    elif each_state_player_object.play_pile.get_denomination_sum() > best_state_player_object.play_pile.get_denomination_sum():
                        best_state = each_state
                    elif each_state_player_object.play_pile.get_denomination_sum == best_state_player_object.play_pile.get_denomination_sum():
                        if random.randrange(2) == 0:
                            best_state = each_state

        if len(tree.children) > 0:
            top_play_card = best_state.value[1].play_pile.get_top_card_and_remove_card()
            best_state.value[1].last_played_card_denomination = top_play_card.denomination
            best_state.value[1].last_played_card_power = top_play_card.power
            best_state.value[1].play_pile.add_card(top_play_card)
        return best_state

    # ------------------------------------------------------------------
    # Core card actions
    # ------------------------------------------------------------------

    def action_draw_card(self):
        """Move the top card of the deck to the hand."""
        card_to_hand = self.deck.get_top_card_and_remove_card()
        self.hand.add_card(card_to_hand)

    def action_play_card(self, card):
        """
        No checking is done to ensure the playing of the card is legal.
        Removes card from hand and adds to top of play pile.
        Sets additional_action based on the card's power.
        """
        try:
            card_to_play = self.hand.remove_card(card)
        except (ValueError):
            print("Couldn't find card %s tribbles %s in hand.  Hand: %s" % (card.denomination,
                                                                             card.power,
                                                                             self.hand.pretty_print()))
            sys.exit()
        self.play_pile.add_card(card_to_play)
        if card_to_play.is_actionable_power():
            self.additional_action = card_to_play.power
        elif card_to_play.power == Power.Poison:
            self.additional_action = Power.Poison
        else:
            self.additional_action = None

    def action_play_card_from_discard_pile(self, card):
        """
        Removes card from discard pile and adds to top of play pile.
        Sets additional_action if the card has an actionable power.
        """
        card_to_play = self.discard_pile.remove_card(card)
        self.play_pile.add_card(card_to_play)
        if card_to_play.is_actionable_power():
            self.additional_action = card_to_play.power

    def action_get_poisoned(self):
        """Discard the top card of the deck and return its denomination."""
        card_to_discard = self.deck.get_top_card_and_remove_card()
        denomination = card_to_discard.denomination
        self.discard_pile.add_card(card_to_discard)
        return denomination

    def action_use_discard_power(self, card):
        """
        The Discard power: discards a card from this player's hand into discard pile.
        Used when another player targets this player with the Discard power.
        """
        card_removed = self.hand.remove_card(card)
        self.discard_pile.add_card(card_removed)

    def action_rescue_card(self, card):
        """
        Move a card from the discard pile to the top of the draw deck.
        Does not automatically play it.
        """
        self.discard_pile.remove_card(card)
        self.deck.add_card(card)

    def action_end_turn(self):
        """Resets the player's additional_action to None. Does NOT draw a card."""
        self.additional_action = None

    def action_end_round(self, round_number, is_out=False):
        """
        Discards player's hand (or shuffles to deck if Safety is in play pile).
        Shuffles play pile into draw deck.

        If is_out=True: scores the play pile + IDIC + Bonus run + Dance bonuses.
        """
        if is_out:
            self.score["round%s" % round_number] = (
                self.play_pile.get_denomination_sum()
                + self.get_idic_bonus()
                + self.get_bonus_run_score()
                + self.get_dance_bonus()
            )

        # Safety: if Safety is in the play pile, shuffle hand into deck instead of discarding
        if not self.hand.is_empty():
            if self.has_power_in_play_pile(Power.Safety):
                self.action_safety_shuffle_hand()
            else:
                for _ in range(0, len(self.hand.deck)):
                    get_card = self.hand.get_top_card_and_remove_card()
                    self.discard_pile.add_card(get_card)

        if not self.play_pile.is_empty():
            for _ in range(0, len(self.play_pile.deck)):
                get_card = self.play_pile.get_top_card_and_remove_card()
                self.deck.add_card(get_card)
            self.deck.shuffle()

    # ------------------------------------------------------------------
    # Deck-manipulation power actions
    # ------------------------------------------------------------------

    def action_cache(self, card):
        """
        Cache power: remove a card from hand and place it face-down under the draw deck,
        then draw one new card from the top of the deck.
        """
        card_removed = self.hand.remove_card(card)
        self.deck.deck.append(card_removed)  # bottom of deck
        if not self.deck.is_empty():
            self.action_draw_card()

    def action_exchange(self, card_from_hand, card_from_discard):
        """
        Exchange power: discard a card from hand, take any card from the discard pile into hand.
        """
        removed = self.hand.remove_card(card_from_hand)
        self.discard_pile.add_card(removed)
        taken = self.discard_pile.remove_card(card_from_discard)
        self.hand.add_card(taken)

    def action_replay(self, card):
        """
        Replay power: search the play pile for a card and move it to the top of the play pile,
        effectively 'replaying' it to update the chain position.
        """
        found = self.play_pile.remove_card(card)
        self.play_pile.add_card(found)

    def action_recycle_discard(self):
        """Recycle power: shuffle the discard pile into the draw deck."""
        cards = list(self.discard_pile.deck)
        self.discard_pile.deck = []
        for c in cards:
            self.deck.deck.append(c)
        self.deck.shuffle()

    def action_flood(self):
        """
        Flood power: place all hand cards face-down under the draw deck,
        then draw three new cards.
        """
        cards = list(self.hand.deck)
        self.hand.deck = []
        for c in cards:
            self.deck.deck.append(c)
        for _ in range(min(3, len(self.deck.deck))):
            self.action_draw_card()

    def action_mutate(self):
        """
        Mutate power: count the cards in the play pile, place those cards face-down
        under the draw deck, then draw that many new cards.
        """
        count = len(self.play_pile.deck)
        cards = list(self.play_pile.deck)
        self.play_pile.deck = []
        for c in cards:
            self.deck.deck.append(c)
        for _ in range(min(count, len(self.deck.deck))):
            self.action_draw_card()

    def action_wager(self, last_card_played, is_chain_broken):
        """
        Wager power: look at the top 3 cards of the draw deck and rearrange them.
        AI heuristic: put the most chain-useful card on top, least useful at bottom.
        """
        top3 = []
        for _ in range(min(3, len(self.deck.deck))):
            top3.append(self.deck.get_top_card_and_remove_card())
        playable = [c for c in top3 if c.is_playable(last_card_played, is_chain_broken)]
        not_playable = [c for c in top3 if not c.is_playable(last_card_played, is_chain_broken)]
        # Playable cards go on top; among non-playable, put smallest denom first (soonest useful)
        not_playable.sort(key=lambda c: c.denomination)
        ordered = playable + not_playable
        for c in reversed(ordered):
            self.deck.deck.insert(0, c)

    # ------------------------------------------------------------------
    # Opponent-targeting power actions (called on the target player)
    # ------------------------------------------------------------------

    def action_discard_random_hand_card(self):
        """
        Discard power (targeting): force this player to discard a random card from their hand.
        Returns the denomination of the discarded card (0 if hand is empty).
        """
        if self.hand.is_empty():
            return 0
        idx = random.randrange(len(self.hand.deck))
        card = self.hand.deck.pop(idx)
        self.discard_pile.add_card(card)
        return card.denomination

    def action_kill_top_play_pile(self):
        """
        Kill power: discard the top card of this player's play pile to their discard pile.
        Returns the killed card, or None if play pile is empty.
        """
        if self.play_pile.is_empty():
            return None
        card = self.play_pile.get_top_card_and_remove_card()
        self.discard_pile.add_card(card)
        return card

    def action_battle_reveal(self):
        """
        Battle power: reveal the top 3 cards of the draw deck (remove them).
        Returns (total_denomination, list_of_cards).
        """
        cards = []
        for _ in range(min(3, len(self.deck.deck))):
            cards.append(self.deck.get_top_card_and_remove_card())
        total = sum(c.denomination for c in cards)
        return (total, cards)

    def action_battle_receive_cards(self, cards):
        """Add a list of cards (battle winnings) to this player's hand."""
        for c in cards:
            self.hand.add_card(c)

    def action_ante(self):
        """
        Ante power: place a random card from hand into the communal ante pot.
        Returns the card, or None if hand is empty.
        """
        if self.hand.is_empty():
            return None
        idx = random.randrange(len(self.hand.deck))
        return self.hand.deck.pop(idx)

    def action_place_card_under_play_pile(self, card):
        """
        Bij / Bah: remove a card from hand and place it face-down at the bottom of the play pile.
        """
        removed = self.hand.remove_card(card)
        self.play_pile.deck.append(removed)

    # ------------------------------------------------------------------
    # Round-start power actions
    # ------------------------------------------------------------------

    def action_mulligan(self, hand_size):
        """
        Roll power: discard current hand and draw up to hand_size new cards.
        Used as a mulligan at the start of a round.
        """
        for c in list(self.hand.deck):
            self.discard_pile.add_card(c)
        self.hand.deck = []
        for _ in range(min(hand_size, len(self.deck.deck))):
            self.action_draw_card()

    def action_safety_shuffle_hand(self):
        """
        Safety power: shuffle remaining hand cards back into the draw deck
        instead of discarding them at round end.
        """
        cards = list(self.hand.deck)
        self.hand.deck = []
        for c in cards:
            self.deck.deck.append(c)
        self.deck.shuffle()

    # ------------------------------------------------------------------
    # Query / helper methods
    # ------------------------------------------------------------------

    def has_power_in_play_pile(self, power):
        """Return True if any card with the given power is in the play pile."""
        return any(card.power == power for card in self.play_pile.deck)

    def is_fold_protected(self):
        """Return True if the top card of the play pile has the Fold power."""
        top = self.play_pile.get_top_card_of_deck()
        return top is not None and top.power == Power.Fold

    def has_fizzbin_protection(self):
        """Return True if any Fizzbin card is in the play pile (protects all play pile cards)."""
        return self.has_power_in_play_pile(Power.Fizzbin)

    def get_dance_bonus(self):
        """
        Dance power: returns 100,000 if the top 6 cards of the play pile form the pattern
        Skip, Reverse, Skip, Reverse, Skip, Reverse (in that exact order from the top).
        """
        if len(self.play_pile.deck) < 6:
            return 0
        pattern = [Power.Skip, Power.Reverse, Power.Skip, Power.Reverse, Power.Skip, Power.Reverse]
        top6_powers = [card.power for card in self.play_pile.deck[:6]]
        if top6_powers == pattern:
            return 100000
        return 0

    def get_idic_bonus(self):
        """
        Returns IDIC bonus points if the player has an IDIC Tribble in their play pile.
        IDIC is worth 10,000 points for each different Tribble power in the play pile (including IDIC itself).
        Multiple IDIC Tribbles of the same denomination do not stack; only unique denominations count.
        Returns 0 if no IDIC card is in the play pile.
        """
        idic_denoms_seen = set()
        has_idic = False
        for card in self.play_pile.deck:
            if card.power == Power.IDIC:
                if card.denomination not in idic_denoms_seen:
                    has_idic = True
                    idic_denoms_seen.add(card.denomination)

        if not has_idic:
            return 0

        unique_powers = set(card.power for card in self.play_pile.deck)
        return len(unique_powers) * 10000

    def get_bonus_run_score(self):
        """
        Returns 100,000 if the player's play pile contains Bonus cards of denominations
        1, 10, 100, and 1,000 (a full run).  A player can only score Bonus once per round.
        Returns 0 if the run is incomplete or no Bonus cards are present.
        """
        bonus_denoms = set(
            card.denomination for card in self.play_pile.deck
            if card.power == Power.Bonus
        )
        if {1, 10, 100, 1000}.issubset(bonus_denoms):
            return 100000
        return 0

    def get_time_warp_penalty(self):
        """
        Returns the number of cards to subtract from the opening hand in the next round.
        Time Warp Tribbles of the same denomination are not cumulative; only unique denominations count.
        """
        time_warp_denoms = set(
            card.denomination for card in self.play_pile.deck
            if card.power == Power.TimeWarp
        )
        return len(time_warp_denoms)

    def get_players_score(self):
        score_to_return = 0
        for round_number, score in self.score.items():
            score_to_return += score
        return score_to_return

    def get_copy(self):
        """Returns a new instance of this Player class in the same state as itself."""
        player_to_return = Player(self.name, None, 0)
        player_to_return.deck = self.deck.get_copy()
        player_to_return.hand = self.hand.get_copy()
        player_to_return.play_pile = self.play_pile.get_copy()
        player_to_return.discard_pile = self.discard_pile.get_copy()
        player_to_return.out_of_play_pile = self.out_of_play_pile.get_copy()
        player_to_return.can_go_out = self.can_go_out
        player_to_return.additional_action = self.additional_action
        player_to_return.last_played_card_denomination = self.last_played_card_denomination
        player_to_return.last_played_card_power = self.last_played_card_power
        for key, value in self.score.items():
            player_to_return.score[key] = value
        return player_to_return


class GameStateNode:
    def __init__(self, card, player):
        self.value = (card, player)
        self.children = []

    def get_card(self):
        return self.value[0]

    def get_player_state(self):
        return self.value[1]

    def __repr__(self):
        return 'Node({!r})'.format(self.value)

    def add_child(self, node):
        self.children.append(node)

    def __iter__(self):
        return iter(self.children)

    def depth_first(self):
        yield self
        for c in self:
            yield from c.depth_first()

    def get_all_end_nodes(self):
        """Returns a list of all leaf nodes of this tree."""
        to_return = []
        self.get_all_end_nodes_internal(to_return)
        return to_return

    def get_all_end_nodes_internal(self, rlist):
        if not self.children:
            rlist.append(self)
        else:
            for each_child in self.children:
                each_child.get_all_end_nodes_internal(rlist)

    def print_this_tree(self, level=0):
        if self.get_card():
            print("\t" * level + "%s Tribbles %s" % (self.get_card().denomination, self.get_card().power))
        if self.children:
            lvl = level + 1
            for each_child in self.children:
                each_child.print_this_tree(lvl)
