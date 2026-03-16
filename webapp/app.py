"""
Flask web app for the Tribbles Card Game Simulator.

Features:
  - Configure number of players, decks, and games to simulate
  - Upload custom deck files
  - Interactive mode: play against computer opponents
  - Watch fully-simulated games at variable speed (1-10000 plays/sec)
  - View detailed game log after completion
"""

import os
import sys
import json
import uuid
import copy
import random
import threading

# Ensure the project root is on sys.path so we can import game modules
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from flask import (
    Flask, render_template, request, redirect, url_for,
    jsonify, session, send_from_directory,
)
from deck import Deck, Card, Power
from player import Player
from game import Game

app = Flask(__name__)
app.secret_key = "tribbles-simulator-secret-key"

DECKS_DIR = os.path.join(PROJECT_ROOT, "decks")
GAMES_DIR = os.path.join(PROJECT_ROOT, "games")
UPLOAD_DIR = os.path.join(PROJECT_ROOT, "decks")  # uploaded decks go here

# ---------------------------------------------------------------------------
# In-memory stores (keyed by session/game id)
# ---------------------------------------------------------------------------
# simulation results: game_id -> { "log": [...], "status": "running"|"done", "scores": ... }
simulations = {}
# interactive games: game_id -> InteractiveGame instance
interactive_games = {}


# ===========================================================================
# Helper: list available deck files
# ===========================================================================

def list_decks():
    decks = []
    for f in sorted(os.listdir(DECKS_DIR)):
        if f.endswith(".json"):
            decks.append(f)
    return decks


# ===========================================================================
# Simulation engine (runs Game with logging)
# ===========================================================================

class LogCapture:
    """Capture print output as structured log entries."""
    def __init__(self):
        self.entries = []
        self._entry_id = 0

    def log(self, message, entry_type="info"):
        self._entry_id += 1
        self.entries.append({
            "id": self._entry_id,
            "type": entry_type,
            "message": message,
        })


def run_simulation(game_id, game_file_path, num_games):
    """Run a full simulation in a background thread, capturing logs."""
    sim = simulations[game_id]
    logger = LogCapture()
    sim["log_capture"] = logger

    try:
        game = Game(game_file_path)
        game.number_of_games_to_play = num_games

        for game_num in range(game.number_of_games_to_play):
            game.import_game(game.game_file_path_local_copy)
            player_keys = list(range(len(game.dict_of_players)))

            for k in player_keys:
                game.dict_of_players[k].deck.shuffle()

            time_warp_penalties = {k: 0 for k in player_keys}
            ante_pot = []

            logger.log("=== Game %d ===" % (game_num + 1), "game_start")

            round_num = 1
            while round_num <= game._number_of_rounds:
                logger.log("--- Round %d ---" % round_num, "round_start")

                # Deal
                for k in player_keys:
                    hand_size = max(1, 7 - time_warp_penalties[k])
                    time_warp_penalties[k] = 0
                    for _ in range(hand_size):
                        if not game.dict_of_players[k].deck.is_empty():
                            game.dict_of_players[k].action_draw_card()
                    logger.log("  %s dealt %d cards" % (game.dict_of_players[k].name, len(game.dict_of_players[k].hand.deck)), "deal")

                # Roll mulligan
                for k in player_keys:
                    p = game.dict_of_players[k]
                    if p.has_power_in_play_pile(Power.Roll):
                        current_hand_size = len(p.hand.deck)
                        p.action_mulligan(current_hand_size)
                        logger.log("  %s mulligans (Roll)" % p.name, "mulligan")

                last_card_played = None
                is_chain_broken = False
                play_direction_ref = [1]
                players_to_skip = {}
                pending_score = {}
                bij_registry = []
                frozen_ref = [None]

                round_over = False
                current_idx = 0
                max_turns = len(player_keys) * 200
                turn_count = 0

                while not round_over and turn_count < max_turns:
                    turn_count += 1
                    current_key = player_keys[current_idx]
                    player = game.dict_of_players[current_key]

                    if frozen_ref[0] is not None:
                        _, frozen_by = frozen_ref[0]
                        if current_key == frozen_by:
                            frozen_ref[0] = None

                    if players_to_skip.get(current_key, 0) > 0:
                        players_to_skip[current_key] -= 1
                        logger.log("  %s is skipped" % player.name, "skip")
                        bah_cards = [c for c in player.hand.deck if c.power == Power.Bah]
                        if bah_cards:
                            player.action_place_card_under_play_pile(bah_cards[0])
                            logger.log("  %s places Bah under play pile" % player.name, "bah")
                    else:
                        beginning_hand_size = len(player.hand.deck)
                        target_for_poison = game.get_best_player_to_poison([player])
                        expected_poison = (target_for_poison.deck.get_expected_poison_value()
                                           if target_for_poison else 0)

                        best_node = player.get_state_minimum_cards_in_hand(
                            last_card_played, expected_poison, is_chain_broken
                        )
                        new_player = best_node.value[1]
                        played_card = None

                        if beginning_hand_size == len(new_player.hand.deck):
                            if new_player.deck.is_empty():
                                logger.log("  %s is decked out" % new_player.name, "decked")
                                while not new_player.hand.is_empty():
                                    c = new_player.hand.get_top_card_and_remove_card()
                                    new_player.discard_pile.add_card(c)
                            else:
                                new_player.action_draw_card()
                                logger.log("  %s draws a card" % new_player.name, "draw")
                                new_node2 = new_player.get_state_minimum_cards_in_hand(
                                    last_card_played, expected_poison, is_chain_broken
                                )
                                new_player2 = new_node2.value[1]
                                if (beginning_hand_size + 1) == len(new_player2.hand.deck):
                                    is_chain_broken = True
                                    new_player = new_player2
                                    logger.log("  %s can't play, chain broken" % new_player.name, "chain_broken")
                                else:
                                    is_chain_broken = False
                                    played_card = new_player2.play_pile.get_top_card_of_deck()
                                    last_card_played = played_card
                                    new_player = new_player2
                        else:
                            is_chain_broken = False
                            played_card = new_player.play_pile.get_top_card_of_deck()
                            last_card_played = played_card

                        if played_card is not None:
                            logger.log("  %s plays %s %s" % (
                                new_player.name,
                                played_card.denomination,
                                played_card.power.name
                            ), "play")

                            if new_player.additional_action == Power.Poison:
                                target = game.get_best_player_to_poison([player])
                                if target and not target.is_fold_protected():
                                    poison_value = target.action_get_poisoned()
                                    if target.has_power_in_play_pile(Power.Tally):
                                        halved = poison_value // 2
                                        new_player.score["round%s" % round_num] += halved
                                        target.score["round%s" % round_num] += halved
                                    else:
                                        new_player.score["round%s" % round_num] += poison_value
                                    logger.log("    Poison: %s scores %d from %s" % (
                                        new_player.name, poison_value, target.name
                                    ), "poison")

                        new_player.action_end_turn()
                        game.dict_of_players[current_key] = copy.deepcopy(new_player)

                        if played_card is not None and current_key in pending_score:
                            scorer_key = pending_score.pop(current_key)
                            game.dict_of_players[scorer_key].score["round%s" % round_num] += played_card.denomination

                        if played_card is not None:
                            last_card_played, is_chain_broken = game._apply_power_effect(
                                current_key, played_card, last_card_played, is_chain_broken,
                                player_keys, players_to_skip, play_direction_ref,
                                ante_pot, pending_score, bij_registry, round_num, frozen_ref
                            )

                        logger.log("  %s: hand=%d pile=%d" % (
                            game.dict_of_players[current_key].name,
                            len(game.dict_of_players[current_key].hand.deck),
                            len(game.dict_of_players[current_key].play_pile.deck)
                        ), "status")

                        if game.dict_of_players[current_key].hand.is_empty():
                            winner_key = current_key
                            logger.log("  %s goes out!" % game.dict_of_players[winner_key].name, "goes_out")

                            for (bij_card, owner_key, holder_key) in bij_registry:
                                if holder_key == winner_key:
                                    bij_still_in_pile = any(
                                        c.denomination == bij_card.denomination and c.power == Power.Bij
                                        for c in game.dict_of_players[holder_key].play_pile.deck
                                    )
                                    if bij_still_in_pile:
                                        game.dict_of_players[owner_key].score["round%s" % round_num] += 50000
                            bij_registry.clear()

                            for k in player_keys:
                                time_warp_penalties[k] += game.dict_of_players[k].get_time_warp_penalty()

                            game.dict_of_players[winner_key].action_end_round(round_num, is_out=True)
                            logger.log("  Round %d winner: %s (score: %d)" % (
                                round_num,
                                game.dict_of_players[winner_key].name,
                                game.dict_of_players[winner_key].score.get("round%s" % round_num, 0)
                            ), "round_end")
                            for k in player_keys:
                                if k != winner_key:
                                    game.dict_of_players[k].action_end_round(round_num, is_out=False)

                            last_card_played = None
                            is_chain_broken = False
                            play_direction_ref[0] = 1
                            players_to_skip = {}
                            pending_score = {}
                            ante_pot.clear()
                            frozen_ref[0] = None
                            round_num += 1
                            round_over = True

                    if not round_over:
                        current_idx = (current_idx + play_direction_ref[0]) % len(player_keys)

            # Final scores for this game
            scores = {}
            for k in range(len(game.dict_of_players)):
                p = game.dict_of_players[k]
                total = p.get_players_score()
                round_scores = {}
                for r in range(game._number_of_rounds):
                    rk = "round%s" % (r + 1)
                    if rk in p.score:
                        round_scores[rk] = p.score[rk]
                scores[p.name] = {"total": total, "rounds": round_scores}
                logger.log("  %s: total %d" % (p.name, total), "final_score")

            sim["scores"].append(scores)

        sim["status"] = "done"

    except Exception as e:
        logger.log("ERROR: %s" % str(e), "error")
        sim["status"] = "error"
        sim["error"] = str(e)


# ===========================================================================
# Interactive game state machine
# ===========================================================================

class InteractiveGame:
    """Manages state for a human-vs-computer interactive game."""

    def __init__(self, player_configs, num_rounds=5, human_index=0):
        self.num_rounds = num_rounds
        self.human_index = human_index
        self.log = []
        self.game_over = False
        self.waiting_for_input = False
        self.input_prompt = None
        self.input_choices = []

        # Build players
        self.players = {}
        player_keys = []
        for i, cfg in enumerate(player_configs):
            deck_path = os.path.join(DECKS_DIR, cfg["deck_file"])
            p = Player(cfg["name"], deck_path, num_rounds)
            self.players[i] = p
            player_keys.append(i)

        self.player_keys = player_keys
        self.current_game = 0
        self.num_games = 1

        # Round state
        self.round_num = 0
        self.time_warp_penalties = {k: 0 for k in player_keys}
        self.ante_pot = []

        # Turn state
        self.last_card_played = None
        self.is_chain_broken = False
        self.play_direction = 1
        self.players_to_skip = {}
        self.pending_score = {}
        self.bij_registry = []
        self.frozen_ref = [None]
        self.current_idx = 0
        self.turn_count = 0

        # Power-choice state (for powers that need human decisions)
        self.input_mode = "play_card"   # "play_card" | "power_choice"
        self.pending_power_effect = None  # Card whose power is pending resolution
        # Log boundary: entries at/after this index were added since the human's last card play
        self.human_play_log_boundary = 0

        # Shuffle and start
        for k in self.player_keys:
            self.players[k].deck.shuffle()

        self._start_round()

    def _add_log(self, msg, entry_type="info"):
        self.log.append({"message": msg, "type": entry_type})

    def _start_round(self):
        self.round_num += 1
        if self.round_num > self.num_rounds:
            self._end_game()
            return

        self._add_log("--- Round %d ---" % self.round_num, "round_start")

        # Deal
        for k in self.player_keys:
            hand_size = max(1, 7 - self.time_warp_penalties[k])
            self.time_warp_penalties[k] = 0
            for _ in range(hand_size):
                if not self.players[k].deck.is_empty():
                    self.players[k].action_draw_card()

        # Roll mulligan for AI players
        for k in self.player_keys:
            if k != self.human_index:
                p = self.players[k]
                if p.has_power_in_play_pile(Power.Roll):
                    hs = len(p.hand.deck)
                    p.action_mulligan(hs)

        # Reset turn state
        self.last_card_played = None
        self.is_chain_broken = False
        self.play_direction = 1
        self.players_to_skip = {}
        self.pending_score = {}
        self.bij_registry = []
        self.frozen_ref = [None]
        self.current_idx = 0
        self.turn_count = 0
        self.human_play_log_boundary = len(self.log)

        self._next_turn()

    def _next_turn(self):
        if self.game_over:
            return

        max_turns = len(self.player_keys) * 200
        if self.turn_count >= max_turns:
            self._add_log("Round timed out", "error")
            self._end_round(None)
            return

        self.turn_count += 1
        current_key = self.player_keys[self.current_idx]

        # Unfreeze
        if self.frozen_ref[0] is not None:
            _, frozen_by = self.frozen_ref[0]
            if current_key == frozen_by:
                self.frozen_ref[0] = None

        # Skip check
        if self.players_to_skip.get(current_key, 0) > 0:
            self.players_to_skip[current_key] -= 1
            self._add_log("%s is skipped" % self.players[current_key].name, "skip")
            bah_cards = [c for c in self.players[current_key].hand.deck if c.power == Power.Bah]
            if bah_cards and current_key != self.human_index:
                self.players[current_key].action_place_card_under_play_pile(bah_cards[0])
            self._advance_turn()
            return

        if current_key == self.human_index:
            self._human_turn()
        else:
            self._ai_turn(current_key)

    def _human_turn(self):
        player = self.players[self.human_index]
        self._add_log("Your turn!", "your_turn")

        # Find playable cards
        playable = []
        for i, card in enumerate(player.hand.deck):
            if card.is_playable(self.last_card_played, self.is_chain_broken):
                playable.append(i)

        if not playable:
            # Must draw
            if player.deck.is_empty():
                self._add_log("Your deck is empty. Discarding hand.", "decked")
                while not player.hand.is_empty():
                    c = player.hand.get_top_card_and_remove_card()
                    player.discard_pile.add_card(c)
                self.is_chain_broken = True
                self._advance_turn()
            else:
                player.action_draw_card()
                self._add_log("You draw a card.", "draw")
                # Check if drawn card is playable
                new_playable = []
                for i, card in enumerate(player.hand.deck):
                    if card.is_playable(self.last_card_played, self.is_chain_broken):
                        new_playable.append(i)
                if not new_playable:
                    self.is_chain_broken = True
                    self._add_log("Still can't play. Chain broken.", "chain_broken")
                    self._advance_turn()
                else:
                    self._prompt_play(new_playable)
        else:
            self._prompt_play(playable)

    def _prompt_play(self, playable_indices):
        """Ask the human to choose a card to play."""
        player = self.players[self.human_index]
        choices = []
        for i in playable_indices:
            card = player.hand.deck[i]
            choices.append({
                "index": i,
                "denomination": card.denomination,
                "power": card.power.name,
                "label": "%d %s" % (card.denomination, card.power.name),
            })
        self.waiting_for_input = True
        self.input_prompt = "Choose a card to play:"
        self.input_choices = choices

    def handle_human_play(self, card_index):
        """Called when the human selects a card to play or makes a power choice."""
        # Route power choices to their own handler
        if self.input_mode == "power_choice":
            self._handle_power_choice(card_index)
            return

        self.waiting_for_input = False
        player = self.players[self.human_index]
        card = player.hand.deck[card_index]
        card_copy = card.get_copy()
        player.action_play_card(card)
        self._add_log("You play %d %s" % (card_copy.denomination, card_copy.power.name), "play")

        played_card = player.play_pile.get_top_card_of_deck()
        self.last_card_played = played_card
        self.is_chain_broken = False

        # Handle poison (auto-targets opponent with highest expected value)
        if player.additional_action == Power.Poison:
            best_target = None
            best_val = -1
            for k in self.player_keys:
                if k == self.human_index:
                    continue
                val = self.players[k].deck.get_expected_poison_value()
                if val > best_val:
                    best_val = val
                    best_target = k
            if best_target is not None and not self.players[best_target].is_fold_protected():
                pv = self.players[best_target].action_get_poisoned()
                player.score["round%s" % self.round_num] = player.score.get("round%s" % self.round_num, 0) + pv
                self._add_log("Poison: you score %d from %s" % (pv, self.players[best_target].name), "poison")

        player.action_end_turn()

        # Check for actionable power (Go/Rescue) — allow continued play first
        if card_copy.power == Power.Go or card_copy.power == Power.Rescue:
            new_playable = []
            for i, c in enumerate(player.hand.deck):
                if c.is_playable(self.last_card_played, self.is_chain_broken):
                    new_playable.append(i)
            if new_playable:
                self._prompt_play(new_playable)
                return

        # Check if this power requires a human choice; if so, pause and wait
        if self._setup_power_choice_if_needed(card_copy):
            return  # _handle_power_choice will finish the turn

        # No choice needed — apply effects automatically
        self._apply_effects(self.human_index, played_card)

        # Check if went out
        if player.hand.is_empty():
            self._end_round(self.human_index)
            return

        self.human_play_log_boundary = len(self.log)
        self._advance_turn()

    # ------------------------------------------------------------------
    # Interactive power choices for human player
    # ------------------------------------------------------------------

    def _setup_power_choice_if_needed(self, card_copy):
        """
        If the card's power requires a human decision, configure the input prompt
        and return True (turn is paused).  Return False if the power can be applied
        automatically (or has no active effect).
        """
        power = card_copy.power
        player = self.players[self.human_index]

        if power == Power.Replay:
            candidates = [c for c in player.play_pile.deck if c.power != Power.Replay]
            if candidates:
                self.pending_power_effect = card_copy
                self.input_mode = "power_choice"
                self.waiting_for_input = True
                self.input_prompt = "Replay: Choose a card to move to the top of your pile:"
                self.input_choices = [
                    {"index": i, "denomination": c.denomination, "power": c.power.name,
                     "label": "%d %s" % (c.denomination, c.power.name)}
                    for i, c in enumerate(candidates)
                ]
                return True

        elif power == Power.Cache:
            if not player.hand.is_empty():
                self.pending_power_effect = card_copy
                self.input_mode = "power_choice"
                self.waiting_for_input = True
                self.input_prompt = "Cache: Choose a card to put under your deck (then draw 1):"
                self.input_choices = [
                    {"index": i, "denomination": c.denomination, "power": c.power.name,
                     "label": "%d %s" % (c.denomination, c.power.name)}
                    for i, c in enumerate(player.hand.deck)
                ]
                return True

        elif power == Power.Recycle:
            choices = []
            for k in self.player_keys:
                p = self.players[k]
                if not p.discard_pile.is_empty():
                    label = "Your discard" if k == self.human_index else "%s's discard" % p.name
                    choices.append({
                        "index": k, "denomination": len(p.discard_pile.deck), "power": "",
                        "label": "%s (%d cards)" % (label, len(p.discard_pile.deck))
                    })
            if choices:
                self.pending_power_effect = card_copy
                self.input_mode = "power_choice"
                self.waiting_for_input = True
                self.input_prompt = "Recycle: Choose whose discard pile to shuffle into their deck:"
                self.input_choices = choices
                return True

        elif power == Power.Copy:
            choices = []
            for k in self.player_keys:
                if k == self.human_index:
                    continue
                top = self.players[k].play_pile.get_top_card_of_deck()
                if top is not None and top.power not in (Power.Copy, Power.Sabotage):
                    choices.append({
                        "index": k, "denomination": top.denomination, "power": top.power.name,
                        "label": "Copy %s from %s" % (top.power.name, self.players[k].name)
                    })
            if choices:
                self.pending_power_effect = card_copy
                self.input_mode = "power_choice"
                self.waiting_for_input = True
                self.input_prompt = "Copy: Choose whose top pile power to copy:"
                self.input_choices = choices
                return True

        elif power in (Power.Kill, Power.Discard, Power.Score, Power.Bij):
            choices = []
            for k in self.player_keys:
                if k == self.human_index:
                    continue
                p = self.players[k]
                if p.is_fold_protected():
                    continue
                if power == Power.Kill and p.has_fizzbin_protection():
                    continue
                choices.append({"index": k, "denomination": 0, "power": "", "label": p.name})
            if choices:
                self.pending_power_effect = card_copy
                self.input_mode = "power_choice"
                self.waiting_for_input = True
                prompts = {
                    Power.Kill:    "Kill: Choose an opponent's top pile card to destroy:",
                    Power.Discard: "Discard: Choose an opponent to lose a random hand card:",
                    Power.Score:   "Score: Choose an opponent — you score their next card's value:",
                    Power.Bij:     "Bij: Choose an opponent to secretly place a card under their pile:",
                }
                self.input_prompt = prompts[power]
                self.input_choices = choices
                return True

        return False

    def _handle_power_choice(self, choice_index):
        """Apply the effect chosen by the human, then continue the turn."""
        self.waiting_for_input = False
        self.input_mode = "play_card"
        card_copy = self.pending_power_effect
        self.pending_power_effect = None
        power = card_copy.power
        player = self.players[self.human_index]

        if power == Power.Replay:
            candidates = [c for c in player.play_pile.deck if c.power != Power.Replay]
            chosen = candidates[choice_index]
            player.action_replay(chosen)
            replayed = player.play_pile.get_top_card_of_deck()
            self.last_card_played = replayed
            self.is_chain_broken = False
            self._add_log("  Replay: you replay %d %s" % (replayed.denomination, replayed.power.name), "info")

        elif power == Power.Cache:
            chosen = player.hand.deck[choice_index]
            self._add_log("  Cache: you cache %d %s and draw a card" % (chosen.denomination, chosen.power.name), "info")
            player.action_cache(chosen)

        elif power == Power.Recycle:
            target_key = choice_index  # index field holds the player key
            self.players[target_key].action_recycle_discard()
            name = "Your discard" if target_key == self.human_index else "%s's discard" % self.players[target_key].name
            self._add_log("  Recycle: %s shuffled into their deck" % name, "info")

        elif power == Power.Copy:
            target_key = choice_index
            target_top = self.players[target_key].play_pile.get_top_card_of_deck()
            if target_top and target_top.power not in (Power.Copy, Power.Sabotage):
                from deck import Card
                proxy = Card(card_copy.denomination, target_top.power, card_copy.owner)
                self._add_log("  Copy: you copy %s's %s power" % (self.players[target_key].name, target_top.power.name), "info")
                self._apply_effects(self.human_index, proxy)

        elif power == Power.Kill:
            target_key = choice_index
            target = self.players[target_key]
            if not target.is_fold_protected() and not target.has_fizzbin_protection():
                killed = target.action_kill_top_play_pile()
                if killed:
                    self._add_log("  Kill: you destroy %s's %d %s" % (target.name, killed.denomination, killed.power.name), "info")
                    if killed.power == Power.Replicate and not target.hand.is_empty():
                        best = max(target.hand.deck, key=lambda c: c.denomination)
                        target.hand.remove_card(best)
                        target.play_pile.add_card(best)

        elif power == Power.Discard:
            target_key = choice_index
            target = self.players[target_key]
            if not target.is_fold_protected():
                discarded_denom = target.action_discard_random_hand_card()
                if discarded_denom > 0:
                    if target.has_power_in_play_pile(Power.Tally):
                        halved = discarded_denom // 2
                        player.score["round%s" % self.round_num] = player.score.get("round%s" % self.round_num, 0) + halved
                        target.score["round%s" % self.round_num] = target.score.get("round%s" % self.round_num, 0) + halved
                        self._add_log("  Discard: %s loses %d (Tally: both score %d)" % (target.name, discarded_denom, halved), "info")
                    else:
                        player.score["round%s" % self.round_num] = player.score.get("round%s" % self.round_num, 0) + discarded_denom
                        self._add_log("  Discard: you score %d from %s's hand" % (discarded_denom, target.name), "info")

        elif power == Power.Score:
            target_key = choice_index
            self.pending_score[target_key] = self.human_index
            self._add_log("  Score: you will score %s's next card" % self.players[target_key].name, "info")

        elif power == Power.Bij:
            target_key = choice_index
            target = self.players[target_key]
            if not target.is_fold_protected() and not player.hand.is_empty():
                bij_card = max(player.hand.deck, key=lambda c: c.denomination)
                player.hand.remove_card(bij_card)
                target.play_pile.deck.append(bij_card)
                self.bij_registry.append((bij_card, self.human_index, target_key))
                self._add_log("  Bij: you place %d %s under %s's pile" % (bij_card.denomination, bij_card.power.name, target.name), "info")

        # Continue turn
        if player.hand.is_empty():
            self._end_round(self.human_index)
            return
        self.human_play_log_boundary = len(self.log)
        self._advance_turn()

    def _ai_turn(self, key):
        player = self.players[key]
        beginning_hand_size = len(player.hand.deck)
        old_pile_len = len(player.play_pile.deck)

        # Find best target for poison
        others = [self.players[k] for k in self.player_keys if k != key]
        target_for_poison = None
        best_val = -1
        for p in others:
            v = p.deck.get_expected_poison_value()
            if v > best_val:
                best_val = v
                target_for_poison = p
        expected_poison = target_for_poison.deck.get_expected_poison_value() if target_for_poison else 0

        best_node = player.get_state_minimum_cards_in_hand(
            self.last_card_played, expected_poison, self.is_chain_broken
        )
        new_player = best_node.value[1]
        played_card = None

        if beginning_hand_size == len(new_player.hand.deck):
            if new_player.deck.is_empty():
                self._add_log("%s is decked out" % new_player.name, "decked")
                while not new_player.hand.is_empty():
                    c = new_player.hand.get_top_card_and_remove_card()
                    new_player.discard_pile.add_card(c)
            else:
                new_player.action_draw_card()
                self._add_log("%s draws a card" % new_player.name, "draw")
                new_node2 = new_player.get_state_minimum_cards_in_hand(
                    self.last_card_played, expected_poison, self.is_chain_broken
                )
                new_player2 = new_node2.value[1]
                if (beginning_hand_size + 1) == len(new_player2.hand.deck):
                    self.is_chain_broken = True
                    new_player = new_player2
                    self._add_log("%s can't play, chain broken" % new_player.name, "chain_broken")
                else:
                    self.is_chain_broken = False
                    played_card = new_player2.play_pile.get_top_card_of_deck()
                    self.last_card_played = played_card
                    new_player = new_player2
                    n_new = len(new_player.play_pile.deck) - old_pile_len
                    for card in reversed(new_player.play_pile.deck[0:n_new]):
                        self._add_log("%s plays %d %s" % (new_player.name, card.denomination, card.power.name), "ai_play")
        else:
            self.is_chain_broken = False
            played_card = new_player.play_pile.get_top_card_of_deck()
            self.last_card_played = played_card
            n_new = len(new_player.play_pile.deck) - old_pile_len
            for card in reversed(new_player.play_pile.deck[0:n_new]):
                self._add_log("%s plays %d %s" % (new_player.name, card.denomination, card.power.name), "ai_play")

            if new_player.additional_action == Power.Poison:
                # Target human if possible
                target = None
                best_pv = -1
                for k in self.player_keys:
                    if k == key:
                        continue
                    v = self.players[k].deck.get_expected_poison_value()
                    if v > best_pv:
                        best_pv = v
                        target = self.players[k]
                if target and not target.is_fold_protected():
                    pv = target.action_get_poisoned()
                    new_player.score["round%s" % self.round_num] = new_player.score.get("round%s" % self.round_num, 0) + pv
                    self._add_log("  Poison: %s scores %d" % (new_player.name, pv), "poison")

        new_player.action_end_turn()
        self.players[key] = copy.deepcopy(new_player)

        if played_card is not None:
            self._apply_effects(key, played_card)

        self._add_log("  %s: hand=%d pile=%d" % (
            self.players[key].name,
            len(self.players[key].hand.deck),
            len(self.players[key].play_pile.deck)
        ), "status")

        if self.players[key].hand.is_empty():
            self._end_round(key)
            return

        self._advance_turn()

    def _apply_effects(self, acting_key, played_card):
        """Apply power effects using a temporary Game wrapper."""
        # Build a temporary Game to use _apply_power_effect
        temp_game = Game()
        temp_game.dict_of_players = self.players
        play_dir_ref = [self.play_direction]
        self.last_card_played, self.is_chain_broken = temp_game._apply_power_effect(
            acting_key, played_card, self.last_card_played, self.is_chain_broken,
            self.player_keys, self.players_to_skip, play_dir_ref,
            self.ante_pot, self.pending_score, self.bij_registry,
            self.round_num, self.frozen_ref
        )
        self.play_direction = play_dir_ref[0]

    def _advance_turn(self):
        self.current_idx = (self.current_idx + self.play_direction) % len(self.player_keys)
        self._next_turn()

    def _end_round(self, winner_key):
        if winner_key is not None:
            winner_name = self.players[winner_key].name
            self._add_log("%s goes out!" % winner_name, "goes_out")

            for k in self.player_keys:
                self.time_warp_penalties[k] += self.players[k].get_time_warp_penalty()

            self.players[winner_key].action_end_round(self.round_num, is_out=True)
            self._add_log("Round %d winner: %s (score: %d)" % (
                self.round_num, winner_name,
                self.players[winner_key].score.get("round%s" % self.round_num, 0)
            ), "round_end")

            for k in self.player_keys:
                if k != winner_key:
                    self.players[k].action_end_round(self.round_num, is_out=False)
        else:
            for k in self.player_keys:
                self.players[k].action_end_round(self.round_num, is_out=False)

        if self.round_num >= self.num_rounds:
            self._end_game()
        else:
            self._start_round()

    def _end_game(self):
        self.game_over = True
        self._add_log("=== Game Over ===", "game_over")
        for k in self.player_keys:
            p = self.players[k]
            total = p.get_players_score()
            self._add_log("%s: total score %d" % (p.name, total), "final_score")

    def get_state(self):
        """Return the current game state as a JSON-serializable dict."""
        player = self.players[self.human_index]
        hand_cards = [
            {"denomination": c.denomination, "power": c.power.name}
            for c in player.hand.deck
        ]
        pile_cards = [
            {"denomination": c.denomination, "power": c.power.name}
            for c in player.play_pile.deck
        ]

        last_card = None
        if self.last_card_played:
            last_card = {
                "denomination": self.last_card_played.denomination,
                "power": self.last_card_played.power.name,
            }

        all_players = []
        for k in self.player_keys:
            p = self.players[k]
            all_players.append({
                "name": p.name,
                "hand_count": len(p.hand.deck),
                "pile_count": len(p.play_pile.deck),
                "deck_count": len(p.deck.deck),
                "discard_count": len(p.discard_pile.deck),
                "score": p.get_players_score(),
                "is_human": k == self.human_index,
            })

        return {
            "hand": hand_cards,
            "play_pile": pile_cards,
            "last_card": last_card,
            "players": all_players,
            "round": self.round_num,
            "chain_broken": self.is_chain_broken,
            "game_over": self.game_over,
            "waiting_for_input": self.waiting_for_input,
            "input_prompt": self.input_prompt,
            "input_choices": self.input_choices,
            "input_mode": self.input_mode,
            "log": self.log[-50:],  # last 50 log entries
            # Log entries added since the human's last card play (used by frontend for animation)
            "events_since_human_play": self.log[self.human_play_log_boundary:],
        }


# ===========================================================================
# Routes
# ===========================================================================

@app.route("/")
def index():
    return render_template("index.html", decks=list_decks())


@app.route("/upload_deck", methods=["POST"])
def upload_deck():
    if "deck_file" not in request.files:
        return redirect(url_for("index"))
    f = request.files["deck_file"]
    if f.filename and f.filename.endswith(".json"):
        f.save(os.path.join(UPLOAD_DIR, f.filename))
    return redirect(url_for("index"))


# ---------------------------------------------------------------------------
# Simulation mode
# ---------------------------------------------------------------------------

@app.route("/simulate", methods=["POST"])
def simulate():
    num_players = int(request.form.get("num_players", 2))
    num_games = int(request.form.get("num_games", 1))
    num_rounds = int(request.form.get("num_rounds", 5))

    players = []
    for i in range(num_players):
        deck = request.form.get("deck_%d" % i, "testdeck.json")
        name = request.form.get("name_%d" % i, "Player %d" % (i + 1))
        players.append({"deck_file": deck, "player_name": name})

    # Create a temporary game config
    game_id = str(uuid.uuid4())[:8]
    game_config = {
        "players": players,
        "games_to_play": num_games,
        "number_of_rounds": num_rounds,
    }
    config_path = os.path.join(GAMES_DIR, "web_%s.json" % game_id)
    with open(config_path, "w") as fp:
        json.dump(game_config, fp)

    simulations[game_id] = {
        "status": "running",
        "log_capture": None,
        "scores": [],
        "config": game_config,
        "speed": int(request.form.get("speed", 1)),
    }

    t = threading.Thread(target=run_simulation, args=(game_id, config_path, num_games))
    t.daemon = True
    t.start()

    return redirect(url_for("simulation_view", game_id=game_id))


@app.route("/simulation/<game_id>")
def simulation_view(game_id):
    if game_id not in simulations:
        return redirect(url_for("index"))
    return render_template("simulation.html", game_id=game_id,
                           speed=simulations[game_id].get("speed", 1))


@app.route("/api/simulation/<game_id>")
def api_simulation_status(game_id):
    if game_id not in simulations:
        return jsonify({"error": "not found"}), 404
    sim = simulations[game_id]
    after = int(request.args.get("after", 0))
    log_entries = []
    if sim["log_capture"]:
        log_entries = [e for e in sim["log_capture"].entries if e["id"] > after]
    return jsonify({
        "status": sim["status"],
        "log": log_entries,
        "scores": sim["scores"],
        "error": sim.get("error"),
    })


@app.route("/simulation/<game_id>/log")
def simulation_log(game_id):
    if game_id not in simulations:
        return redirect(url_for("index"))
    sim = simulations[game_id]
    entries = sim["log_capture"].entries if sim["log_capture"] else []
    return render_template("log.html", game_id=game_id, entries=entries,
                           scores=sim["scores"], config=sim.get("config"))


# ---------------------------------------------------------------------------
# Interactive mode
# ---------------------------------------------------------------------------

@app.route("/interactive", methods=["POST"])
def interactive_start():
    num_players = int(request.form.get("num_players", 2))
    num_rounds = int(request.form.get("num_rounds", 5))
    human_name = request.form.get("human_name", "You")

    player_configs = [{"name": human_name, "deck_file": request.form.get("deck_0", "testdeck.json")}]
    for i in range(1, num_players):
        deck = request.form.get("deck_%d" % i, "testdeck.json")
        name = request.form.get("name_%d" % i, "CPU %d" % i)
        player_configs.append({"name": name, "deck_file": deck})

    game_id = str(uuid.uuid4())[:8]
    interactive_games[game_id] = InteractiveGame(player_configs, num_rounds, human_index=0)

    return redirect(url_for("interactive_view", game_id=game_id))


@app.route("/interactive/<game_id>")
def interactive_view(game_id):
    if game_id not in interactive_games:
        return redirect(url_for("index"))
    return render_template("interactive.html", game_id=game_id)


@app.route("/api/interactive/<game_id>/state")
def api_interactive_state(game_id):
    if game_id not in interactive_games:
        return jsonify({"error": "not found"}), 404
    return jsonify(interactive_games[game_id].get_state())


@app.route("/api/interactive/<game_id>/play", methods=["POST"])
def api_interactive_play(game_id):
    if game_id not in interactive_games:
        return jsonify({"error": "not found"}), 404
    game = interactive_games[game_id]
    card_index = int(request.json.get("card_index", 0))
    game.handle_human_play(card_index)
    return jsonify(game.get_state())


# ===========================================================================
# Main
# ===========================================================================

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=48888)
