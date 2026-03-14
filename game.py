from deck import Deck, Card, Power
from player import Player
import os
import json
import random
import copy


class Game:

    def __init__(self, game_to_import=None):
        self.dict_of_players = {}
        self.number_of_games_to_play = 0
        self.game_file_path_local_copy = None
        self._number_of_rounds = 5

        if game_to_import is not None:
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
            self._number_of_rounds = game_dict["number_of_rounds"]

    def setup_game(self):
        pass

    # ------------------------------------------------------------------
    # Targeting helpers
    # ------------------------------------------------------------------

    def get_best_player_to_poison(self, players_not_to_poison):
        """Returns the player object with the highest average poison value, excluding players_not_to_poison."""
        best_player = None
        best_value = -1
        for key in self.dict_of_players:
            p = self.dict_of_players[key]
            if p in players_not_to_poison:
                continue
            val = p.deck.get_expected_poison_value()
            if best_player is None or val > best_value:
                best_player = p
                best_value = val
        return best_player

    def _get_next_player_key(self, current_key, player_keys, play_direction):
        """Return the key of the player whose turn comes next given the current direction."""
        idx = player_keys.index(current_key)
        next_idx = (idx + play_direction) % len(player_keys)
        return player_keys[next_idx]

    def _get_best_target_key(self, excluding_key, player_keys):
        """
        Return the key of the opponent with the most combined cards (hand + deck).
        Returns None if no valid opponent exists.
        """
        best_key = None
        best_count = -1
        for k in player_keys:
            if k == excluding_key:
                continue
            count = len(self.dict_of_players[k].deck.deck) + len(self.dict_of_players[k].hand.deck)
            if count > best_count:
                best_count = count
                best_key = k
        return best_key

    def _get_player_with_most_discards(self, excluding_key, player_keys, include_self=False):
        """Return the key of the player with the most cards in their discard pile."""
        best_key = None
        best_count = -1
        for k in player_keys:
            if k == excluding_key and not include_self:
                continue
            count = len(self.dict_of_players[k].discard_pile.deck)
            if count > best_count:
                best_count = count
                best_key = k
        if best_key is None and include_self:
            return excluding_key
        return best_key

    def _get_most_common_opponent_power(self, acting_key, player_keys):
        """Return the Power most frequently appearing in all opponents' hands."""
        power_counts = {}
        for k in player_keys:
            if k == acting_key:
                continue
            for card in self.dict_of_players[k].hand.deck:
                power_counts[card.power] = power_counts.get(card.power, 0) + 1
        if not power_counts:
            return None
        return max(power_counts, key=power_counts.get)

    def _get_most_common_opponent_discard_power(self, acting_key, player_keys):
        """Return the Power most frequently appearing across all players' discard piles."""
        power_counts = {}
        for k in player_keys:
            for card in self.dict_of_players[k].discard_pile.deck:
                power_counts[card.power] = power_counts.get(card.power, 0) + 1
        if not power_counts:
            return None
        return max(power_counts, key=power_counts.get)

    # ------------------------------------------------------------------
    # Power effect dispatcher
    # ------------------------------------------------------------------

    def _apply_power_effect(self, acting_key, played_card, last_card_played, is_chain_broken,
                             player_keys, players_to_skip, play_direction_ref,
                             ante_pot, pending_score, bij_registry, round_num, frozen_ref):
        """
        Apply the game effect of played_card's power.
        Modifies self.dict_of_players in place for targeted effects.
        Returns (last_card_played, is_chain_broken) which may be updated by some powers.
        """
        power = played_card.power

        # ---- Turn-order powers ----

        if power == Power.Skip:
            next_key = self._get_next_player_key(acting_key, player_keys, play_direction_ref[0])
            players_to_skip[next_key] = players_to_skip.get(next_key, 0) + 1

        elif power == Power.Reverse:
            play_direction_ref[0] = -play_direction_ref[0]

        # ---- Play-pile attack powers ----

        elif power == Power.Kill:
            target_key = self._get_best_target_key(acting_key, player_keys)
            if target_key is not None:
                target = self.dict_of_players[target_key]
                if not target.is_fold_protected() and not target.has_fizzbin_protection():
                    killed = target.action_kill_top_play_pile()
                    # Replicate: if the killed card was Replicate, the target may add one card to their pile
                    if killed is not None and killed.power == Power.Replicate:
                        if not target.hand.is_empty():
                            best_card = max(target.hand.deck, key=lambda c: c.denomination)
                            target.hand.remove_card(best_card)
                            target.play_pile.add_card(best_card)

        elif power == Power.Discard:
            # Force an opponent to discard a random hand card; acting player scores the denomination
            target_key = self._get_best_target_key(acting_key, player_keys)
            if target_key is not None:
                target = self.dict_of_players[target_key]
                if not target.is_fold_protected():
                    discarded_denom = target.action_discard_random_hand_card()
                    if discarded_denom > 0:
                        # Tally: if target has Tally in play pile, halve the score and target also scores
                        if target.has_power_in_play_pile(Power.Tally):
                            halved = discarded_denom // 2
                            self.dict_of_players[acting_key].score["round%s" % round_num] += halved
                            target.score["round%s" % round_num] += halved
                        else:
                            self.dict_of_players[acting_key].score["round%s" % round_num] += discarded_denom

        # ---- Battle power ----

        elif power == Power.Battle:
            target_key = self._get_best_target_key(acting_key, player_keys)
            if target_key is not None:
                target = self.dict_of_players[target_key]
                if not target.is_fold_protected():
                    my_total, my_cards = self.dict_of_players[acting_key].action_battle_reveal()
                    their_total, their_cards = target.action_battle_reveal()
                    all_cards = my_cards + their_cards
                    # Tie goes to the Battle card player
                    if my_total >= their_total:
                        self.dict_of_players[acting_key].action_battle_receive_cards(all_cards)
                    else:
                        target.action_battle_receive_cards(all_cards)

        # ---- Deck-cycling powers ----

        elif power == Power.Cache:
            actor = self.dict_of_players[acting_key]
            if not actor.hand.is_empty():
                # AI: cache (cycle away) the smallest denomination card
                card_to_cache = min(actor.hand.deck, key=lambda c: c.denomination)
                actor.action_cache(card_to_cache)

        elif power == Power.Exchange:
            actor = self.dict_of_players[acting_key]
            if not actor.hand.is_empty() and not actor.discard_pile.is_empty():
                card_to_discard = min(actor.hand.deck, key=lambda c: c.denomination)
                card_to_take = max(actor.discard_pile.deck, key=lambda c: c.denomination)
                actor.action_exchange(card_to_discard, card_to_take)

        elif power == Power.Wager:
            self.dict_of_players[acting_key].action_wager(last_card_played, is_chain_broken)

        elif power == Power.Recycle:
            # Target the player (possibly self) with the most discards
            target_key = self._get_player_with_most_discards(acting_key, player_keys, include_self=True)
            if target_key is not None:
                self.dict_of_players[target_key].action_recycle_discard()

        elif power == Power.Flood:
            for k in player_keys:
                self.dict_of_players[k].action_flood()

        elif power == Power.Mutate:
            self.dict_of_players[acting_key].action_mutate()

        elif power == Power.Replay:
            actor = self.dict_of_players[acting_key]
            # AI: replay the highest-denomination card that is not the just-played Replay card
            candidates = [c for c in actor.play_pile.deck if c.power != Power.Replay]
            if candidates:
                card_to_replay = max(candidates, key=lambda c: c.denomination)
                actor.action_replay(card_to_replay)
                last_card_played = actor.play_pile.get_top_card_of_deck()
                is_chain_broken = False

        # ---- Global / multi-player powers ----

        elif power == Power.Party:
            for k in player_keys:
                actor = self.dict_of_players[k]
                if not actor.hand.is_empty():
                    idx = random.randrange(len(actor.hand.deck))
                    card = actor.hand.deck.pop(idx)
                    actor.play_pile.deck.append(card)  # bottom of play pile

        elif power == Power.Stampede:
            # All other players may immediately play the next card in chain sequence
            for k in player_keys:
                if k == acting_key:
                    continue
                actor = self.dict_of_players[k]
                stamped_state = actor.get_state_minimum_cards_in_hand(
                    last_card_played, 0, is_chain_broken
                ).value[1]
                if len(stamped_state.hand.deck) < len(actor.hand.deck):
                    top = stamped_state.play_pile.get_top_card_of_deck()
                    if top is not None:
                        last_card_played = top
                        is_chain_broken = False
                    self.dict_of_players[k] = stamped_state

        elif power == Power.Qapla:
            # All players reveal top card; if all same denomination or power, acting player scores 7× highest
            revealed = {k: self.dict_of_players[k].deck.get_top_card_of_deck() for k in player_keys}
            non_none = [c for c in revealed.values() if c is not None]
            if len(non_none) == len(player_keys):
                all_same_denom = len(set(c.denomination for c in non_none)) == 1
                all_same_power = len(set(c.power for c in non_none)) == 1
                if all_same_denom or all_same_power:
                    max_denom = max(c.denomination for c in non_none)
                    self.dict_of_players[acting_key].score["round%s" % round_num] += 7 * max_denom
                    # Also award ante pot to Qapla winner
                    if ante_pot:
                        max_ante = max(c.denomination for c in ante_pot)
                        self.dict_of_players[acting_key].score["round%s" % round_num] += max_ante
                        ante_pot.clear()

        elif power == Power.Ante:
            # All players place a random hand card into the pot
            for k in player_keys:
                card = self.dict_of_players[k].action_ante()
                if card is not None:
                    ante_pot.append(card)

        # ---- Opponent-information / score-manipulation powers ----

        elif power == Power.Score:
            # If the chosen opponent plays any card on their next turn, acting player scores those points
            target_key = self._get_best_target_key(acting_key, player_keys)
            if target_key is not None:
                pending_score[target_key] = acting_key

        elif power == Power.Sabotage:
            target_key = self._get_best_target_key(acting_key, player_keys)
            if target_key is not None:
                target = self.dict_of_players[target_key]
                if not target.is_fold_protected() and not target.deck.is_empty():
                    sabotaged = target.deck.get_top_card_and_remove_card()
                    target.discard_pile.add_card(sabotaged)
                    # May use the sabotaged card's power (avoid recursion for complex powers)
                    safe_to_recurse = sabotaged.power not in (
                        Power.Sabotage, Power.Copy, Power.Stampede,
                        Power.Flood, Power.Qapla, Power.Ante, Power.Battle
                    )
                    if safe_to_recurse:
                        last_card_played, is_chain_broken = self._apply_power_effect(
                            acting_key, sabotaged, last_card_played, is_chain_broken,
                            player_keys, players_to_skip, play_direction_ref,
                            ante_pot, pending_score, bij_registry, round_num, frozen_ref
                        )

        elif power == Power.Copy:
            # Use the power of the top card on another player's play pile
            target_key = self._get_best_target_key(acting_key, player_keys)
            if target_key is not None:
                target_top = self.dict_of_players[target_key].play_pile.get_top_card_of_deck()
                if target_top is not None and target_top.power not in (Power.Copy, Power.Sabotage):
                    # Create a proxy card that carries the copied power
                    proxy = Card(played_card.denomination, target_top.power, played_card.owner)
                    last_card_played, is_chain_broken = self._apply_power_effect(
                        acting_key, proxy, last_card_played, is_chain_broken,
                        player_keys, players_to_skip, play_direction_ref,
                        ante_pot, pending_score, bij_registry, round_num, frozen_ref
                    )

        elif power == Power.Bij:
            # Place a card from hand face-down under an opponent's play pile
            # If that opponent goes out without playing (owning) it, Bij's owner scores 50,000
            target_key = self._get_best_target_key(acting_key, player_keys)
            if target_key is not None:
                target = self.dict_of_players[target_key]
                actor = self.dict_of_players[acting_key]
                if not target.is_fold_protected() and not actor.hand.is_empty():
                    bij_card = max(actor.hand.deck, key=lambda c: c.denomination)
                    actor.hand.remove_card(bij_card)
                    target.play_pile.deck.append(bij_card)
                    bij_registry.append((bij_card, acting_key, target_key))

        # ---- Disruption powers ----

        elif power == Power.Freeze:
            # Name the most common opponent power; cards with that power can't be played until acting player's next turn
            # AI: target the power most common in opponents' hands
            frozen_power = self._get_most_common_opponent_power(acting_key, player_keys)
            frozen_ref[0] = (frozen_power, acting_key)  # (frozen_power, unfreeze_when_key_plays_again)

        elif power == Power.Rival:
            # Name a power; remove all cards with that power from every player's discard pile (out of play)
            rival_power = self._get_most_common_opponent_discard_power(acting_key, player_keys)
            if rival_power is not None:
                for k in player_keys:
                    p = self.dict_of_players[k]
                    removed = [c for c in p.discard_pile.deck if c.power == rival_power]
                    p.discard_pile.deck = [c for c in p.discard_pile.deck if c.power != rival_power]
                    for c in removed:
                        p.out_of_play_pile.add_card(c)

        # ---- Passive powers (no active effect when played; effects are checked elsewhere) ----
        # Power.Dabo, Power.Shift          — chain mechanics in is_playable()
        # Power.Famine, Power.Advance,     — chain mechanics in is_playable()
        # Power.Clone                      — chain mechanics in is_playable()
        # Power.IDIC, Power.Bonus          — scoring in get_idic_bonus / get_bonus_run_score
        # Power.TimeWarp                   — hand size penalty applied at round start
        # Power.Dance                      — scoring bonus via get_dance_bonus()
        # Power.Safety                     — hand recycled at round end in action_end_round()
        # Power.Roll                       — mulligan offered at round start
        # Power.Fizzbin                    — protects play pile (checked in Kill)
        # Power.Fold                       — protects player while on top (checked in targeting)
        # Power.Replicate                  — triggers when killed card is Replicate (checked in Kill)
        # Power.Tally                      — halves scoring when opponent targets your cards (checked above)
        # Power.Bah                        — handled in Skip processing in the turn loop
        # Power.Go, Power.Rescue           — handled in state tree (is_actionable_power)
        # Power.Poison                     — handled separately in turn loop
        # Power.Shift                      — wildcard in is_playable(); chain continues from its denomination

        return last_card_played, is_chain_broken

    # ------------------------------------------------------------------
    # Main run loop
    # ------------------------------------------------------------------

    def run(self):
        for game_num in range(self.number_of_games_to_play):
            # Reload fresh state for each game
            self.import_game(self.game_file_path_local_copy)
            player_keys = list(range(len(self.dict_of_players)))

            # Shuffle all decks
            for k in player_keys:
                self.dict_of_players[k].deck.shuffle()

            # TimeWarp penalties carry over between rounds; initialise to zero
            time_warp_penalties = {k: 0 for k in player_keys}
            ante_pot = []

            round_num = 1
            while round_num <= self._number_of_rounds:

                # ---- Deal opening hands (apply TimeWarp penalty) ----
                for k in player_keys:
                    hand_size = max(1, 7 - time_warp_penalties[k])
                    time_warp_penalties[k] = 0
                    for _ in range(hand_size):
                        if not self.dict_of_players[k].deck.is_empty():
                            self.dict_of_players[k].action_draw_card()

                # ---- Roll mulligan ----
                for k in player_keys:
                    p = self.dict_of_players[k]
                    if p.has_power_in_play_pile(Power.Roll):
                        current_hand_size = len(p.hand.deck)
                        p.action_mulligan(current_hand_size)

                # ---- Round state ----
                last_card_played = None
                is_chain_broken = False
                play_direction_ref = [1]   # mutable reference so _apply_power_effect can flip it
                players_to_skip = {}       # player_key -> number of turns still to skip
                pending_score = {}         # target_player_key -> scorer_key (Score power)
                bij_registry = []          # list of (card, owner_key, holder_key)
                frozen_ref = [None]        # (frozen_Power, key_of_player_who_froze)

                round_over = False
                current_idx = 0            # index into player_keys

                # Safety guard: at most len(players) * 200 turns per round
                max_turns = len(player_keys) * 200
                turn_count = 0

                while not round_over and turn_count < max_turns:
                    turn_count += 1
                    current_key = player_keys[current_idx]
                    player = self.dict_of_players[current_key]

                    print("It is player %s's turn." % player.name)
                    if last_card_played is not None:
                        print("  Last card: %s %s" % (last_card_played.denomination, last_card_played.power))

                    # ---- Unfreeze if it is the freezing player's turn again ----
                    if frozen_ref[0] is not None:
                        _, frozen_by = frozen_ref[0]
                        if current_key == frozen_by:
                            frozen_ref[0] = None

                    # ---- Skip handling ----
                    if players_to_skip.get(current_key, 0) > 0:
                        players_to_skip[current_key] -= 1
                        print("  Player %s is skipped." % player.name)
                        # Bah: skipped player may place a Bah card from hand under their play pile
                        bah_cards = [c for c in player.hand.deck if c.power == Power.Bah]
                        if bah_cards:
                            player.action_place_card_under_play_pile(bah_cards[0])
                            print("  Player %s placed Bah under their play pile." % player.name)

                    else:
                        # ---- Execute turn ----
                        beginning_hand_size = len(player.hand.deck)

                        target_for_poison = self.get_best_player_to_poison([player])
                        expected_poison = (target_for_poison.deck.get_expected_poison_value()
                                           if target_for_poison else 0)

                        best_node = player.get_state_minimum_cards_in_hand(
                            last_card_played, expected_poison, is_chain_broken
                        )
                        new_player = best_node.value[1]
                        played_card = None

                        if beginning_hand_size == len(new_player.hand.deck):
                            # Player could not play; draw a card
                            print("  Player %s draws a card." % new_player.name)
                            if new_player.deck.is_empty():
                                print("  Player %s is decked. Moving hand to discard." % new_player.name)
                                while not new_player.hand.is_empty():
                                    c = new_player.hand.get_top_card_and_remove_card()
                                    new_player.discard_pile.add_card(c)
                            else:
                                new_player.action_draw_card()
                                # Check if the drawn card enables a play
                                new_node2 = new_player.get_state_minimum_cards_in_hand(
                                    last_card_played, expected_poison, is_chain_broken
                                )
                                new_player2 = new_node2.value[1]
                                if (beginning_hand_size + 1) == len(new_player2.hand.deck):
                                    # Still couldn't play after drawing
                                    is_chain_broken = True
                                    new_player = new_player2
                                else:
                                    is_chain_broken = False
                                    played_card = new_player2.play_pile.get_top_card_of_deck()
                                    last_card_played = played_card
                                    new_player = new_player2
                        else:
                            # Player played one or more cards
                            is_chain_broken = False
                            played_card = new_player.play_pile.get_top_card_of_deck()
                            last_card_played = played_card

                        # ---- Apply power effects while additional_action is still set ----
                        if played_card is not None:
                            # Poison (checked before action_end_turn resets additional_action)
                            if new_player.additional_action == Power.Poison:
                                target = self.get_best_player_to_poison([player])
                                if target and not target.is_fold_protected():
                                    poison_value = target.action_get_poisoned()
                                    if target.has_power_in_play_pile(Power.Tally):
                                        halved = poison_value // 2
                                        new_player.score["round%s" % round_num] += halved
                                        target.score["round%s" % round_num] += halved
                                    else:
                                        new_player.score["round%s" % round_num] += poison_value

                        new_player.action_end_turn()
                        self.dict_of_players[current_key] = copy.deepcopy(new_player)

                        # ---- Pending Score: someone used Score power against this player ----
                        if played_card is not None and current_key in pending_score:
                            scorer_key = pending_score.pop(current_key)
                            self.dict_of_players[scorer_key].score["round%s" % round_num] += played_card.denomination

                        # ---- Dispatch card power effects ----
                        if played_card is not None:
                            last_card_played, is_chain_broken = self._apply_power_effect(
                                current_key, played_card, last_card_played, is_chain_broken,
                                player_keys, players_to_skip, play_direction_ref,
                                ante_pot, pending_score, bij_registry, round_num, frozen_ref
                            )

                        print("  %s hand: %d cards | play pile: %d cards" % (
                            self.dict_of_players[current_key].name,
                            len(self.dict_of_players[current_key].hand.deck),
                            len(self.dict_of_players[current_key].play_pile.deck)
                        ))

                        # ---- Check for round end (player went out) ----
                        if self.dict_of_players[current_key].hand.is_empty():
                            winner_key = current_key
                            print("Player %s went out!" % self.dict_of_players[winner_key].name)

                            # Bij scoring: if the going-out player holds a Bij card belonging to someone else
                            for (bij_card, owner_key, holder_key) in bij_registry:
                                if holder_key == winner_key:
                                    bij_still_in_pile = any(
                                        c.denomination == bij_card.denomination and c.power == Power.Bij
                                        for c in self.dict_of_players[holder_key].play_pile.deck
                                    )
                                    if bij_still_in_pile:
                                        self.dict_of_players[owner_key].score["round%s" % round_num] += 50000
                            bij_registry.clear()

                            # Record TimeWarp penalties BEFORE action_end_round clears the play piles
                            for k in player_keys:
                                time_warp_penalties[k] += self.dict_of_players[k].get_time_warp_penalty()

                            # Score the round
                            self.dict_of_players[winner_key].action_end_round(round_num, is_out=True)
                            print("Round %s score for %s: %s" % (
                                round_num,
                                self.dict_of_players[winner_key].name,
                                self.dict_of_players[winner_key].score["round%s" % round_num]
                            ))
                            for k in player_keys:
                                if k != winner_key:
                                    self.dict_of_players[k].action_end_round(round_num, is_out=False)

                            # Reset round state
                            last_card_played = None
                            is_chain_broken = False
                            play_direction_ref[0] = 1
                            players_to_skip = {}
                            pending_score = {}
                            ante_pot.clear()
                            frozen_ref[0] = None
                            round_num += 1
                            round_over = True

                    # ---- Advance to next player ----
                    if not round_over:
                        current_idx = (current_idx + play_direction_ref[0]) % len(player_keys)

            # ---- Print final scores ----
            print("\n=== Game %s Final Scores ===" % (game_num + 1))
            for k in range(len(self.dict_of_players)):
                total = self.dict_of_players[k].get_players_score()
                print("Player %s (%s): total %s" % (k + 1, self.dict_of_players[k].name, total))
                for r in range(self._number_of_rounds):
                    round_key = "round%s" % (r + 1)
                    if round_key in self.dict_of_players[k].score:
                        print("  Round %s: %s" % (r + 1, self.dict_of_players[k].score[round_key]))


def main():
    game_file_path = os.path.join("games", "test_game.json")
    game = Game(game_file_path)
    game.run()


if __name__ == '__main__':
    main()
