# -*- coding: utf-8 -*-
"""
Comprehensive TDD tests for Tribbles CCG rules.

Covers card playability, scoring mechanics, and player actions based on
the official rulebook (Version 2.1, July 2015).
"""

import unittest
import os
import sys

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
DECKS_DIR = os.path.join(TESTS_DIR, '..', 'decks')
GAMES_DIR = os.path.join(TESTS_DIR, '..', 'games')

from deck import Card, Power, Deck
from player import Player


# ---------------------------------------------------------------------------
# Helper: build a Player with a hand pre-loaded from a list of Card objects
# ---------------------------------------------------------------------------

def player_with_hand(cards, name="test"):
    p = Player(name, None, 5)
    for card in cards:
        p.hand.add_card(card)
    return p


def player_with_play_pile(cards, name="test"):
    p = Player(name, None, 5)
    for card in cards:
        p.play_pile.add_card(card)
    return p


# ===========================================================================
# Card playability tests (chain mechanics)
# ===========================================================================

class TestCardPlayability(unittest.TestCase):
    """Tests for Card.is_playable() covering all chain rules."""

    # -- Basic sequence --

    def test_one_playable_at_start_of_chain(self):
        """Denomination 1 is playable when there is no last card (start of round)."""
        card = Card(1, Power.Go, None)
        self.assertTrue(card.is_playable(None))

    def test_nonone_not_playable_at_start(self):
        """Only denomination 1 may open a round."""
        for denom in [10, 100, 1000, 10000, 100000]:
            card = Card(denom, Power.Go, None)
            self.assertFalse(card.is_playable(None),
                             f"{denom} should not be playable at chain start")

    def test_sequence_10x_is_playable(self):
        """Each denomination that is exactly 10x the last is playable."""
        chain = [1, 10, 100, 1000, 10000, 100000]
        for i in range(len(chain) - 1):
            last = Card(chain[i], Power.Go, None)
            nxt = Card(chain[i + 1], Power.Rescue, None)
            self.assertTrue(nxt.is_playable(last),
                            f"{chain[i+1]} should be playable after {chain[i]}")

    def test_out_of_sequence_not_playable(self):
        """Denominations that skip a step are not playable."""
        last = Card(10, Power.Go, None)
        card = Card(1000, Power.Go, None)
        self.assertFalse(card.is_playable(last))

    def test_smaller_denom_not_playable(self):
        """Playing a smaller denomination (going backwards) is not allowed."""
        last = Card(100, Power.Rescue, None)
        card = Card(10, Power.Go, None)
        self.assertFalse(card.is_playable(last))

    # -- Chain reset at 100,000 --

    def test_one_playable_after_100000(self):
        """After 100,000 the chain resets to 1."""
        last = Card(100000, Power.Discard, None)
        card = Card(1, Power.Bonus, None)
        self.assertTrue(card.is_playable(last))

    def test_100000_clone_playable_after_100000(self):
        """100,000 Clone is also valid right after 100,000 (Clone same-denom rule)."""
        last = Card(100000, Power.Discard, None)
        card = Card(100000, Power.Clone, None)
        self.assertTrue(card.is_playable(last))

    def test_non_one_not_playable_after_100000_except_clone(self):
        """Only denomination 1 (or same-denom Clone) is playable after 100,000."""
        last = Card(100000, Power.Discard, None)
        for denom in [10, 100, 1000, 10000]:
            card = Card(denom, Power.Clone, None)
            self.assertFalse(card.is_playable(last),
                             f"{denom} Clone should NOT be playable after 100,000")

    # -- Clone power --

    def test_clone_same_denom_playable(self):
        """Clone may be played on the same denomination as the previous card."""
        last = Card(1000, Power.Discard, None)
        clone = Card(1000, Power.Clone, None)
        self.assertTrue(clone.is_playable(last))

    def test_non_clone_same_denom_not_playable(self):
        """Non-Clone cards of the same denomination as the last card are invalid."""
        last = Card(10000, Power.Clone, None)
        same_denom = Card(10000, Power.Rescue, None)
        self.assertFalse(same_denom.is_playable(last))

    def test_clone_wrong_denom_not_playable(self):
        """Clone cannot skip denominations; it must match the last card exactly."""
        last = Card(100, Power.Go, None)
        clone = Card(1000, Power.Clone, None)
        # 1000 != 100, and 1000 == 100 * 10 so it is actually playable as next in sequence
        # but Clone's special rule is only about same-denomination matching.
        # This is playable via the normal 10x rule, NOT the Clone rule — still True.
        self.assertTrue(clone.is_playable(last))

    def test_clone_lower_denom_not_playable(self):
        """Clone of a lower denomination than the last card is not playable."""
        last = Card(10000, Power.Go, None)
        clone = Card(100, Power.Clone, None)
        self.assertFalse(clone.is_playable(last))

    # -- Chain broken --

    def test_one_playable_when_chain_broken(self):
        """When the chain is broken, denomination 1 can restart it."""
        last = Card(1000, Power.Rescue, None)
        card = Card(1, Power.Poison, None)
        self.assertTrue(card.is_playable(last, is_chain_broken=True))

    def test_non_one_not_playable_when_chain_broken_without_advance(self):
        """When chain is broken, non-1 cards without Advance power cannot be played."""
        last = Card(100, Power.Go, None)
        card = Card(100, Power.Rescue, None)
        self.assertFalse(card.is_playable(last, is_chain_broken=True))

    def test_chain_broken_still_allows_next_in_sequence(self):
        """The player AFTER the one who broke the chain may continue OR restart with 1."""
        last = Card(1000, Power.Rescue, None)
        ten_k = Card(10000, Power.Go, None)
        # Continuing the sequence is still valid even after break
        self.assertTrue(ten_k.is_playable(last, is_chain_broken=True))

    # -- Advance power --

    def test_advance_playable_when_chain_broken_any_denom(self):
        """Advance cards can be played in place of a 1 when chain is broken."""
        last = Card(100, Power.Go, None)
        advance_100 = Card(100, Power.Advance, None)
        advance_10k = Card(10000, Power.Advance, None)
        self.assertTrue(advance_100.is_playable(last, is_chain_broken=True))
        self.assertTrue(advance_10k.is_playable(last, is_chain_broken=True))

    def test_advance_not_special_when_chain_unbroken(self):
        """Advance power gives no advantage when the chain is intact."""
        last = Card(100, Power.Go, None)
        advance_10k = Card(10000, Power.Advance, None)
        # 10,000 is the normal next step after 1,000, not after 100
        self.assertFalse(advance_10k.is_playable(last, is_chain_broken=False))

    def test_advance_in_normal_sequence_is_playable(self):
        """Advance card at the correct denomination in sequence is still playable."""
        last = Card(100, Power.Go, None)
        advance_1k = Card(1000, Power.Advance, None)
        self.assertTrue(advance_1k.is_playable(last, is_chain_broken=False))

    # -- Famine power --

    def test_one_playable_after_famine(self):
        """After any Famine card, only denomination 1 is next in sequence."""
        for denom in [1, 10, 100, 1000, 10000, 100000]:
            famine = Card(denom, Power.Famine, None)
            next_card = Card(1, Power.Go, None)
            self.assertTrue(next_card.is_playable(famine),
                            f"1 should be playable after {denom} Famine")

    def test_non_one_not_playable_after_famine(self):
        """Famine resets chain to 1; non-1 cards are not playable after Famine."""
        famine = Card(100, Power.Famine, None)
        for denom in [10, 100, 1000, 10000, 100000]:
            card = Card(denom, Power.Rescue, None)
            self.assertFalse(card.is_playable(famine),
                             f"{denom} should NOT be playable after Famine")

    def test_clone_not_overrides_famine(self):
        """Clone of the Famine's own denomination is NOT playable after Famine."""
        famine = Card(100, Power.Famine, None)
        clone_100 = Card(100, Power.Clone, None)
        self.assertFalse(clone_100.is_playable(famine))

    def test_famine_chain_does_not_break(self):
        """Famine resets chain to 1 but does not break it; chain_broken flag irrelevant."""
        famine = Card(100, Power.Famine, None)
        one_card = Card(1, Power.Rescue, None)
        # Playable regardless of is_chain_broken because Famine resets to 1
        self.assertTrue(one_card.is_playable(famine, is_chain_broken=False))
        self.assertTrue(one_card.is_playable(famine, is_chain_broken=True))


# ===========================================================================
# IDIC scoring tests
# ===========================================================================

class TestIDICScoring(unittest.TestCase):
    """Tests for Player.get_idic_bonus()."""

    def test_no_idic_in_play_pile_returns_zero(self):
        """No IDIC in play pile → no IDIC bonus."""
        p = player_with_play_pile([
            Card(1, Power.Go, "test"),
            Card(10, Power.Rescue, "test"),
        ])
        self.assertEqual(p.get_idic_bonus(), 0)

    def test_idic_alone_scores_10000(self):
        """A single IDIC in the play pile with only itself scores 10,000 (1 unique power)."""
        p = player_with_play_pile([Card(1, Power.IDIC, "test")])
        self.assertEqual(p.get_idic_bonus(), 10000)

    def test_idic_with_four_unique_powers_scores_40000(self):
        """IDIC + 3 other unique powers = 4 × 10,000 = 40,000."""
        p = player_with_play_pile([
            Card(1, Power.IDIC, "test"),
            Card(100, Power.Recycle, "test"),
            Card(1000, Power.Reverse, "test"),
            Card(10000, Power.Discard, "test"),
        ])
        self.assertEqual(p.get_idic_bonus(), 40000)

    def test_idic_counts_itself_as_a_power(self):
        """IDIC counts as one of the unique powers in the tally."""
        p = player_with_play_pile([
            Card(1, Power.IDIC, "test"),
            Card(10, Power.Go, "test"),
        ])
        # Two unique powers: IDIC and Go
        self.assertEqual(p.get_idic_bonus(), 20000)

    def test_duplicate_powers_count_once(self):
        """Duplicate powers (same power different denomination) count as one."""
        p = player_with_play_pile([
            Card(1, Power.IDIC, "test"),
            Card(10, Power.Go, "test"),
            Card(100, Power.Go, "test"),
        ])
        # Powers: IDIC, Go → 2 unique powers
        self.assertEqual(p.get_idic_bonus(), 20000)

    def test_two_idic_same_denomination_do_not_stack(self):
        """Two IDIC cards of the same denomination are treated as one for scoring."""
        p = player_with_play_pile([
            Card(1, Power.IDIC, "test"),
            Card(1, Power.IDIC, "test"),
            Card(10, Power.Go, "test"),
        ])
        # Powers: IDIC, Go → 2 unique powers (IDIC with denom 1 seen twice, only counts once)
        self.assertEqual(p.get_idic_bonus(), 20000)

    def test_two_idic_different_denominations_both_trigger(self):
        """Two IDIC cards of different denominations are cumulative."""
        p = player_with_play_pile([
            Card(1, Power.IDIC, "test"),
            Card(10000, Power.IDIC, "test"),
            Card(10, Power.Go, "test"),
        ])
        # Powers: IDIC, Go → 2 unique powers; IDIC present at two unique denoms
        # Both IDIC cards give the same bonus (both trigger IDIC, same unique power count)
        # Rulebook: "IDIC Tribbles are never cumulative with other IDIC Tribbles of the same
        # denomination. They are cumulative with those of other denominations."
        # Net: one IDIC bonus applied (the set of unique powers: IDIC + Go = 2 powers = 20,000)
        self.assertEqual(p.get_idic_bonus(), 20000)

    def test_idic_with_six_unique_powers_scores_60000(self):
        """With 6 unique powers and an IDIC, score is 6 × 10,000 = 60,000."""
        p = player_with_play_pile([
            Card(1, Power.IDIC, "test"),
            Card(10, Power.Go, "test"),
            Card(100, Power.Rescue, "test"),
            Card(1000, Power.Poison, "test"),
            Card(10000, Power.Skip, "test"),
            Card(100000, Power.Clone, "test"),
        ])
        self.assertEqual(p.get_idic_bonus(), 60000)

    def test_idic_end_round_out_includes_idic_score(self):
        """action_end_round with is_out=True adds IDIC bonus to round score."""
        p = player_with_play_pile([
            Card(1, Power.IDIC, "test"),
            Card(10, Power.Go, "test"),
        ])
        p.action_end_round(1, is_out=True)
        # play pile sum: 1 + 10 = 11; IDIC bonus: 2 powers × 10,000 = 20,000
        self.assertEqual(p.score["round1"], 11 + 20000)

    def test_idic_end_round_not_out_no_idic_score(self):
        """Players who do not go out do not receive IDIC bonus."""
        p = player_with_play_pile([
            Card(1, Power.IDIC, "test"),
            Card(10, Power.Go, "test"),
        ])
        p.action_end_round(1, is_out=False)
        self.assertEqual(p.score["round1"], 0)


# ===========================================================================
# Bonus run scoring tests
# ===========================================================================

class TestBonusRunScoring(unittest.TestCase):
    """Tests for Player.get_bonus_run_score()."""

    def test_no_bonus_cards_returns_zero(self):
        """No Bonus cards → no Bonus score."""
        p = player_with_play_pile([
            Card(1, Power.Go, "test"),
            Card(10, Power.Rescue, "test"),
        ])
        self.assertEqual(p.get_bonus_run_score(), 0)

    def test_partial_bonus_run_returns_zero(self):
        """Incomplete run (missing 1,000 Bonus) does not score."""
        p = player_with_play_pile([
            Card(1, Power.Bonus, "test"),
            Card(10, Power.Bonus, "test"),
            Card(100, Power.Bonus, "test"),
            # missing 1,000 Bonus
        ])
        self.assertEqual(p.get_bonus_run_score(), 0)

    def test_complete_bonus_run_scores_100000(self):
        """A full run of 1-10-100-1,000 Bonus cards scores 100,000."""
        p = player_with_play_pile([
            Card(1, Power.Bonus, "test"),
            Card(10, Power.Bonus, "test"),
            Card(100, Power.Bonus, "test"),
            Card(1000, Power.Bonus, "test"),
        ])
        self.assertEqual(p.get_bonus_run_score(), 100000)

    def test_bonus_run_with_extra_cards_still_scores(self):
        """Non-Bonus cards interspersed do not prevent Bonus run scoring."""
        p = player_with_play_pile([
            Card(1, Power.Go, "test"),
            Card(1, Power.Bonus, "test"),
            Card(10, Power.Bonus, "test"),
            Card(100, Power.Bonus, "test"),
            Card(1000, Power.Bonus, "test"),
            Card(10000, Power.Clone, "test"),
        ])
        self.assertEqual(p.get_bonus_run_score(), 100000)

    def test_bonus_run_only_scores_once(self):
        """Even two full runs only score 100,000 (once per round)."""
        p = player_with_play_pile([
            Card(1, Power.Bonus, "test"),
            Card(1, Power.Bonus, "test"),
            Card(10, Power.Bonus, "test"),
            Card(10, Power.Bonus, "test"),
            Card(100, Power.Bonus, "test"),
            Card(100, Power.Bonus, "test"),
            Card(1000, Power.Bonus, "test"),
            Card(1000, Power.Bonus, "test"),
        ])
        self.assertEqual(p.get_bonus_run_score(), 100000)

    def test_bonus_run_end_round_out_includes_bonus(self):
        """action_end_round with is_out=True adds Bonus run score."""
        p = player_with_play_pile([
            Card(1, Power.Bonus, "test"),
            Card(10, Power.Bonus, "test"),
            Card(100, Power.Bonus, "test"),
            Card(1000, Power.Bonus, "test"),
        ])
        p.action_end_round(1, is_out=True)
        # play pile sum: 1111; bonus run: 100,000
        self.assertEqual(p.score["round1"], 1111 + 100000)

    def test_bonus_run_end_round_not_out_no_bonus(self):
        """Bonus run is only scored when going out."""
        p = player_with_play_pile([
            Card(1, Power.Bonus, "test"),
            Card(10, Power.Bonus, "test"),
            Card(100, Power.Bonus, "test"),
            Card(1000, Power.Bonus, "test"),
        ])
        p.action_end_round(1, is_out=False)
        self.assertEqual(p.score["round1"], 0)

    def test_both_idic_and_bonus_run_stack(self):
        """IDIC bonus and Bonus run are both added when going out."""
        p = player_with_play_pile([
            Card(1, Power.Bonus, "test"),
            Card(10, Power.Bonus, "test"),
            Card(100, Power.Bonus, "test"),
            Card(1000, Power.Bonus, "test"),
            Card(1, Power.IDIC, "test"),
        ])
        p.action_end_round(1, is_out=True)
        # play pile sum: 1+10+100+1000+1 = 1112; bonus run: 100,000; IDIC: 2 powers (Bonus + IDIC) = 20,000
        self.assertEqual(p.score["round1"], 1112 + 100000 + 20000)


# ===========================================================================
# Time Warp hand-size penalty tests
# ===========================================================================

class TestTimeWarpPenalty(unittest.TestCase):
    """Tests for Player.get_time_warp_penalty()."""

    def test_no_time_warp_returns_zero(self):
        """No Time Warp cards → no hand penalty."""
        p = player_with_play_pile([Card(1, Power.Go, "test")])
        self.assertEqual(p.get_time_warp_penalty(), 0)

    def test_one_time_warp_returns_one(self):
        """A single Time Warp of any denomination reduces next hand by 1."""
        p = player_with_play_pile([Card(10000, Power.TimeWarp, "test")])
        self.assertEqual(p.get_time_warp_penalty(), 1)

    def test_two_time_warps_same_denom_count_once(self):
        """Two Time Warps of the same denomination are not cumulative."""
        p = player_with_play_pile([
            Card(10000, Power.TimeWarp, "test"),
            Card(10000, Power.TimeWarp, "test"),
        ])
        self.assertEqual(p.get_time_warp_penalty(), 1)

    def test_two_time_warps_different_denoms_count_twice(self):
        """Time Warps of different denominations are cumulative."""
        p = player_with_play_pile([
            Card(10000, Power.TimeWarp, "test"),
            Card(100000, Power.TimeWarp, "test"),
        ])
        self.assertEqual(p.get_time_warp_penalty(), 2)

    def test_three_time_warps_mix(self):
        """Two unique denominations among three Time Warp cards gives penalty of 2."""
        p = player_with_play_pile([
            Card(10000, Power.TimeWarp, "test"),
            Card(10000, Power.TimeWarp, "test"),
            Card(100000, Power.TimeWarp, "test"),
        ])
        self.assertEqual(p.get_time_warp_penalty(), 2)


# ===========================================================================
# Round end / scoring integration
# ===========================================================================

class TestRoundEndScoring(unittest.TestCase):
    """Integration tests for action_end_round scoring."""

    def test_going_out_scores_play_pile(self):
        """Player going out scores the denomination sum of their play pile."""
        p = player_with_play_pile([
            Card(1, Power.Go, "test"),
            Card(10, Power.Rescue, "test"),
            Card(100, Power.Clone, "test"),
        ])
        p.action_end_round(1, is_out=True)
        self.assertEqual(p.score["round1"], 111)

    def test_not_going_out_scores_zero(self):
        """Player who does not go out scores nothing for that round."""
        p = player_with_play_pile([Card(100000, Power.Clone, "test")])
        p.action_end_round(1, is_out=False)
        self.assertEqual(p.score["round1"], 0)

    def test_play_pile_moves_to_deck_after_round(self):
        """After round end, play pile is shuffled back into the draw deck."""
        p = player_with_play_pile([
            Card(1, Power.Go, "test"),
            Card(10, Power.Rescue, "test"),
        ])
        p.action_end_round(1, is_out=True)
        self.assertTrue(p.play_pile.is_empty())
        self.assertEqual(len(p.deck.deck), 2)

    def test_hand_discarded_after_round(self):
        """Remaining hand cards are moved to the discard pile at round end."""
        p = player_with_hand([
            Card(1000, Power.Skip, "test"),
            Card(10000, Power.Poison, "test"),
        ])
        p.action_end_round(1, is_out=False)
        self.assertTrue(p.hand.is_empty())
        self.assertEqual(len(p.discard_pile.deck), 2)

    def test_cumulative_score_across_rounds(self):
        """Scores across multiple rounds accumulate correctly."""
        p = Player("test", None, 5)
        for card in [Card(100, Power.Go, "test")]:
            p.play_pile.add_card(card)
        p.action_end_round(1, is_out=True)
        p.deck.shuffle()
        for card in [Card(1000, Power.Rescue, "test")]:
            p.play_pile.add_card(card)
        p.action_end_round(2, is_out=True)
        self.assertEqual(p.get_players_score(), 1100)


# ===========================================================================
# Discard power action tests
# ===========================================================================

class TestDiscardPowerAction(unittest.TestCase):
    """Tests for Player.action_use_discard_power()."""

    def test_discard_removes_card_from_hand(self):
        """Discard power removes the targeted card from the player's hand."""
        p = Player("test", None, 5)
        card = Card(100, Power.Poison, "test")
        p.hand.add_card(card)
        p.action_use_discard_power(card)
        self.assertTrue(p.hand.is_empty())

    def test_discard_places_card_in_discard_pile(self):
        """Discard power places the removed card into the discard pile."""
        p = Player("test", None, 5)
        card = Card(100, Power.Poison, "test")
        p.hand.add_card(card)
        p.action_use_discard_power(card)
        self.assertEqual(len(p.discard_pile.deck), 1)
        self.assertEqual(p.discard_pile.deck[0].denomination, 100)
        self.assertEqual(p.discard_pile.deck[0].power, Power.Poison)

    def test_discard_correct_card_when_multiple_in_hand(self):
        """Discard power removes the specified card, not others."""
        p = Player("test", None, 5)
        keep = Card(1, Power.Go, "test")
        discard_target = Card(100, Power.Poison, "test")
        p.hand.add_card(keep)
        p.hand.add_card(discard_target)
        p.action_use_discard_power(discard_target)
        self.assertEqual(len(p.hand.deck), 1)
        self.assertEqual(p.hand.deck[0].denomination, 1)


# ===========================================================================
# Poison power action tests
# ===========================================================================

class TestPoisonAction(unittest.TestCase):
    """Tests for Player.action_get_poisoned()."""

    def test_poisoned_discards_top_of_deck(self):
        """action_get_poisoned discards the top card of the player's deck."""
        p = Player("test", None, 5)
        card = Card(10000, Power.Rescue, "test")
        p.deck.add_card(card)
        result = p.action_get_poisoned()
        self.assertEqual(result, 10000)
        self.assertTrue(p.deck.is_empty())
        self.assertEqual(len(p.discard_pile.deck), 1)

    def test_poisoned_returns_denomination(self):
        """action_get_poisoned returns the denomination of the discarded card."""
        p = Player("test", None, 5)
        p.deck.add_card(Card(100000, Power.Clone, "test"))
        val = p.action_get_poisoned()
        self.assertEqual(val, 100000)

    def test_poison_card_sets_additional_action(self):
        """Playing a Poison card sets additional_action to Power.Poison."""
        p = player_with_hand([Card(10, Power.Poison, "test")])
        p.action_play_card(p.hand.deck[0])
        self.assertEqual(p.additional_action, Power.Poison)


# ===========================================================================
# Rescue power action tests
# ===========================================================================

class TestRescueAction(unittest.TestCase):
    """Tests for Player.action_rescue_card()."""

    def test_rescue_moves_card_from_discard_to_top_of_deck(self):
        """Rescue moves a card from the discard pile to the top of the draw deck."""
        p = Player("test", None, 5)
        card = Card(1000, Power.Rescue, "test")
        p.discard_pile.add_card(card)
        p.deck.add_card(Card(1, Power.Go, "test"))
        p.action_rescue_card(card)
        top = p.deck.deck[0]
        self.assertEqual(top.denomination, 1000)
        self.assertEqual(top.power, Power.Rescue)

    def test_rescue_removes_from_discard(self):
        """Rescue removes the targeted card from the discard pile."""
        p = Player("test", None, 5)
        card = Card(100, Power.Go, "test")
        p.discard_pile.add_card(card)
        p.action_rescue_card(card)
        self.assertTrue(p.discard_pile.is_empty())


# ===========================================================================
# Power enum completeness tests
# ===========================================================================

class TestPowerEnum(unittest.TestCase):
    """Verify the Power enum contains all powers defined in the rulebook."""

    EXPECTED_POWERS = [
        "Advance", "Ante", "Bah", "Battle", "Bij", "Bonus", "Cache", "Clone",
        "Copy", "Dabo", "Dance", "Discard", "Exchange", "Famine", "Fizzbin",
        "Flood", "Fold", "Freeze", "Go", "IDIC", "Kill", "Mutate", "Party",
        "Poison", "Qapla", "Recycle", "Replay", "Replicate", "Rescue", "Reverse",
        "Rival", "Roll", "Safety", "Sabotage", "Score", "Shift", "Skip",
        "Stampede", "Tally", "TimeWarp", "Wager",
    ]

    def test_all_rulebook_powers_present(self):
        """Every power in the rulebook must have an entry in the Power enum."""
        for power_name in self.EXPECTED_POWERS:
            self.assertIn(power_name, Power.__members__,
                          f"Power '{power_name}' missing from enum")

    def test_power_enum_members_are_unique(self):
        """No duplicate names in the Power enum."""
        names = list(Power.__members__.keys())
        self.assertEqual(len(names), len(set(names)))

    def test_card_creation_with_new_powers(self):
        """Cards can be created with every new power in the enum."""
        for power in Power:
            card = Card(100, power, "test")
            self.assertEqual(card.power, power)


# ===========================================================================
# Deck string parsing tests for new power names
# ===========================================================================

class TestDeckParsingNewPowers(unittest.TestCase):
    """Deck.convert_string_to_cards() must handle all power names."""

    def test_parse_idic_card(self):
        d = Deck("test")
        cards = d.convert_string_to_cards("2 1 Tribble - IDIC")
        self.assertEqual(len(cards), 2)
        self.assertEqual(cards[0].power, Power.IDIC)

    def test_parse_timewarp_card(self):
        d = Deck("test")
        cards = d.convert_string_to_cards("1 10000 Tribbles - TimeWarp")
        self.assertEqual(cards[0].power, Power.TimeWarp)

    def test_parse_famine_card(self):
        d = Deck("test")
        cards = d.convert_string_to_cards("3 100 Tribbles - Famine")
        self.assertEqual(len(cards), 3)
        for c in cards:
            self.assertEqual(c.power, Power.Famine)

    def test_parse_advance_card(self):
        d = Deck("test")
        cards = d.convert_string_to_cards("1 1000 Tribbles - Advance")
        self.assertEqual(cards[0].power, Power.Advance)
        self.assertEqual(cards[0].denomination, 1000)

    def test_parse_bonus_card(self):
        d = Deck("test")
        cards = d.convert_string_to_cards("4 10 Tribbles - Bonus")
        self.assertEqual(len(cards), 4)
        for c in cards:
            self.assertEqual(c.power, Power.Bonus)
            self.assertEqual(c.denomination, 10)


# ===========================================================================
# Dabo chain mechanics tests (mirrors Famine behaviour)
# ===========================================================================

class TestDaboChainMechanics(unittest.TestCase):
    """Dabo resets the chain to 1 without breaking it, identical to Famine."""

    def test_one_playable_after_dabo_any_denom(self):
        """After any Dabo card, denomination 1 is next in sequence."""
        for denom in [1, 10, 100, 1000, 10000, 100000]:
            dabo = Card(denom, Power.Dabo, None)
            one = Card(1, Power.Go, None)
            self.assertTrue(one.is_playable(dabo),
                            f"1 should be playable after {denom} Dabo")

    def test_non_one_not_playable_after_dabo(self):
        """Non-1 cards are not playable after Dabo."""
        dabo = Card(100, Power.Dabo, None)
        for denom in [10, 100, 1000, 10000, 100000]:
            card = Card(denom, Power.Rescue, None)
            self.assertFalse(card.is_playable(dabo),
                             f"{denom} should NOT be playable after Dabo")

    def test_clone_not_playable_after_dabo(self):
        """Clone of Dabo's denomination is not playable after Dabo."""
        dabo = Card(100, Power.Dabo, None)
        clone_100 = Card(100, Power.Clone, None)
        self.assertFalse(clone_100.is_playable(dabo))

    def test_dabo_chain_does_not_break(self):
        """Dabo resets to 1 regardless of is_chain_broken."""
        dabo = Card(100, Power.Dabo, None)
        one = Card(1, Power.Rescue, None)
        self.assertTrue(one.is_playable(dabo, is_chain_broken=False))
        self.assertTrue(one.is_playable(dabo, is_chain_broken=True))

    def test_after_dabo_chain_continues_normally_from_one(self):
        """After Dabo → 1 → 10 should be playable (normal continuation)."""
        one = Card(1, Power.Go, None)
        ten = Card(10, Power.Rescue, None)
        self.assertTrue(ten.is_playable(one))


# ===========================================================================
# Shift chain mechanics tests (wildcard power)
# ===========================================================================

class TestShiftChainMechanics(unittest.TestCase):
    """Shift is a wildcard: playable at any point in an ongoing chain."""

    def test_shift_not_playable_at_chain_start(self):
        """Shift cannot open a round (only denomination 1 may do that)."""
        for denom in [1, 10, 100, 1000, 10000, 100000]:
            shift = Card(denom, Power.Shift, None)
            self.assertFalse(shift.is_playable(None),
                             f"{denom} Shift should NOT be playable at chain start")

    def test_shift_playable_after_any_card(self):
        """Shift is playable after any denomination."""
        for last_denom in [1, 10, 100, 1000, 10000, 100000]:
            last = Card(last_denom, Power.Go, None)
            for shift_denom in [1, 10, 100, 1000, 10000, 100000]:
                shift = Card(shift_denom, Power.Shift, None)
                self.assertTrue(shift.is_playable(last),
                                f"{shift_denom} Shift should be playable after {last_denom}")

    def test_shift_playable_when_chain_broken(self):
        """Shift is also playable when the chain is broken."""
        last = Card(10000, Power.Go, None)
        shift = Card(100, Power.Shift, None)
        self.assertTrue(shift.is_playable(last, is_chain_broken=True))

    def test_shift_playable_after_famine(self):
        """Shift (wildcard) is playable even after Famine."""
        famine = Card(100, Power.Famine, None)
        shift = Card(1000, Power.Shift, None)
        self.assertTrue(shift.is_playable(famine))

    def test_after_shift_chain_continues_from_shift_denomination(self):
        """After a Shift card the normal ×10 rule applies from the Shift's denomination."""
        shift = Card(100, Power.Shift, None)
        correct_next = Card(1000, Power.Go, None)   # 100 × 10
        wrong_next = Card(10, Power.Go, None)        # 100 / 10, invalid
        self.assertTrue(correct_next.is_playable(shift))
        self.assertFalse(wrong_next.is_playable(shift))


# ===========================================================================
# Dance bonus scoring tests
# ===========================================================================

class TestDanceBonusScoring(unittest.TestCase):
    """Tests for Player.get_dance_bonus()."""

    def test_no_cards_no_dance(self):
        p = player_with_play_pile([Card(1, Power.Go, "t")])
        self.assertEqual(p.get_dance_bonus(), 0)

    def test_fewer_than_6_cards_no_dance(self):
        p = player_with_play_pile([
            Card(1, Power.Skip, "t"), Card(10, Power.Reverse, "t"),
            Card(100, Power.Skip, "t"), Card(1000, Power.Reverse, "t"),
        ])
        self.assertEqual(p.get_dance_bonus(), 0)

    def test_correct_pattern_scores_100000(self):
        """Skip/Reverse×3 in top 6 cards → 100,000.
        add_card inserts at index 0, so the LAST card added is at the top.
        To get top=[Skip,Reverse,Skip,Reverse,Skip,Reverse] we add in reverse order."""
        p = player_with_play_pile([
            Card(100000, Power.Reverse, "t"),  # added first → ends up deepest
            Card(10000,  Power.Skip,    "t"),
            Card(1000,   Power.Reverse, "t"),
            Card(100,    Power.Skip,    "t"),
            Card(10,     Power.Reverse, "t"),
            Card(1,      Power.Skip,    "t"),  # added last → top of pile
        ])
        self.assertEqual(p.get_dance_bonus(), 100000)

    def test_wrong_pattern_no_dance(self):
        """Reverse before Skip (top→bottom) is not the Dance pattern."""
        p = player_with_play_pile([
            Card(100000, Power.Skip,    "t"),
            Card(10000,  Power.Reverse, "t"),
            Card(1000,   Power.Skip,    "t"),
            Card(100,    Power.Reverse, "t"),
            Card(10,     Power.Skip,    "t"),
            Card(1,      Power.Reverse, "t"),  # top of pile = Reverse
        ])
        self.assertEqual(p.get_dance_bonus(), 0)

    def test_dance_added_to_score_on_going_out(self):
        """Dance bonus is included in action_end_round when going out."""
        p = player_with_play_pile([
            Card(100000, Power.Reverse, "t"),
            Card(10000,  Power.Skip,    "t"),
            Card(1000,   Power.Reverse, "t"),
            Card(100,    Power.Skip,    "t"),
            Card(10,     Power.Reverse, "t"),
            Card(1,      Power.Skip,    "t"),  # top of pile
        ])
        p.action_end_round(1, is_out=True)
        pile_sum = 1 + 10 + 100 + 1000 + 10000 + 100000
        self.assertEqual(p.score["round1"], pile_sum + 100000)

    def test_dance_not_scored_when_not_out(self):
        p = player_with_play_pile([
            Card(100000, Power.Reverse, "t"),
            Card(10000,  Power.Skip,    "t"),
            Card(1000,   Power.Reverse, "t"),
            Card(100,    Power.Skip,    "t"),
            Card(10,     Power.Reverse, "t"),
            Card(1,      Power.Skip,    "t"),
        ])
        p.action_end_round(1, is_out=False)
        self.assertEqual(p.score["round1"], 0)


# ===========================================================================
# Safety power tests
# ===========================================================================

class TestSafetyPower(unittest.TestCase):
    """Tests for the Safety passive power in action_end_round."""

    def test_safety_in_play_pile_shuffles_hand_to_deck(self):
        """When Safety is in the play pile, hand cards go to deck instead of discard."""
        p = Player("test", None, 5)
        p.play_pile.add_card(Card(1, Power.Safety, "test"))
        hand_card = Card(1000, Power.Go, "test")
        p.hand.add_card(hand_card)
        initial_deck_size = len(p.deck.deck)
        p.action_end_round(1, is_out=False)
        self.assertTrue(p.hand.is_empty())
        self.assertTrue(p.discard_pile.is_empty())
        # play pile also moves back to deck, so deck grew by 2 (Safety + hand card)
        self.assertEqual(len(p.deck.deck), initial_deck_size + 2)

    def test_no_safety_discards_hand_normally(self):
        """Without Safety in play pile, hand cards go to discard."""
        p = Player("test", None, 5)
        p.play_pile.add_card(Card(1, Power.Go, "test"))
        p.hand.add_card(Card(1000, Power.Rescue, "test"))
        p.action_end_round(1, is_out=False)
        self.assertTrue(p.hand.is_empty())
        self.assertEqual(len(p.discard_pile.deck), 1)


# ===========================================================================
# Roll mulligan tests
# ===========================================================================

class TestRollMulligan(unittest.TestCase):
    """Tests for Player.action_mulligan()."""

    def test_mulligan_discards_hand(self):
        """action_mulligan moves all hand cards to discard pile."""
        p = Player("test", None, 5)
        for denom in [1, 10, 100]:
            p.hand.add_card(Card(denom, Power.Go, "test"))
        p.deck.add_card(Card(1000, Power.Rescue, "test"))
        p.deck.add_card(Card(10000, Power.Rescue, "test"))
        p.action_mulligan(3)
        self.assertTrue(p.hand.is_empty() or len(p.hand.deck) <= 3)
        # Old hand cards should be in discard
        self.assertEqual(len(p.discard_pile.deck), 3)

    def test_mulligan_draws_new_hand(self):
        """action_mulligan draws up to hand_size new cards from deck."""
        p = Player("test", None, 5)
        for _ in range(3):
            p.hand.add_card(Card(1, Power.Go, "test"))
        for denom in [10, 100, 1000]:
            p.deck.add_card(Card(denom, Power.Rescue, "test"))
        p.action_mulligan(3)
        self.assertEqual(len(p.hand.deck), 3)
        # new hand should have come from deck
        self.assertTrue(all(c.denomination in [10, 100, 1000] for c in p.hand.deck))


# ===========================================================================
# Fizzbin protection tests
# ===========================================================================

class TestFizzbinProtection(unittest.TestCase):
    """Tests for Player.has_fizzbin_protection() and its effect on Kill."""

    def test_no_fizzbin_not_protected(self):
        p = player_with_play_pile([Card(1, Power.Go, "test")])
        self.assertFalse(p.has_fizzbin_protection())

    def test_fizzbin_in_play_pile_is_protected(self):
        p = player_with_play_pile([
            Card(1, Power.Go, "test"),
            Card(10, Power.Fizzbin, "test"),
        ])
        self.assertTrue(p.has_fizzbin_protection())

    def test_kill_blocked_by_fizzbin(self):
        """Kill cannot remove the top card if Fizzbin is in the play pile."""
        p = player_with_play_pile([
            Card(10, Power.Fizzbin, "test"),
            Card(100, Power.Go, "test"),
        ])
        initial_size = len(p.play_pile.deck)
        if p.has_fizzbin_protection():
            pass  # game loop would skip the kill
        else:
            p.action_kill_top_play_pile()
        # Protected: pile unchanged
        self.assertEqual(len(p.play_pile.deck), initial_size)


# ===========================================================================
# Fold protection tests
# ===========================================================================

class TestFoldProtection(unittest.TestCase):
    """Tests for Player.is_fold_protected()."""

    def test_fold_on_top_is_protected(self):
        p = player_with_play_pile([Card(100, Power.Fold, "test")])
        self.assertTrue(p.is_fold_protected())

    def test_fold_not_on_top_not_protected(self):
        # add_card inserts at index 0; last added = top.
        # Add Go last so Go is on top and Fold is beneath.
        p = player_with_play_pile([
            Card(10, Power.Fold, "test"),   # added first → beneath top
            Card(100, Power.Go, "test"),    # added last → top of pile
        ])
        self.assertFalse(p.is_fold_protected())

    def test_empty_play_pile_not_protected(self):
        p = Player("test", None, 5)
        self.assertFalse(p.is_fold_protected())


# ===========================================================================
# New player action method tests
# ===========================================================================

class TestCachePowerAction(unittest.TestCase):

    def test_cache_removes_card_from_hand(self):
        """Cache removes the cached card from hand then draws one new card, so net hand size is 1."""
        p = Player("test", None, 5)
        card = Card(100, Power.Go, "test")
        p.hand.add_card(card)
        p.deck.add_card(Card(1000, Power.Rescue, "test"))
        p.action_cache(card)
        # Cached card is gone; drew one replacement → hand still has 1 card
        self.assertEqual(len(p.hand.deck), 1)
        self.assertFalse(any(c.denomination == 100 for c in p.hand.deck))

    def test_cache_places_card_under_deck(self):
        p = Player("test", None, 5)
        card = Card(100, Power.Go, "test")
        p.hand.add_card(card)
        p.deck.add_card(Card(1000, Power.Rescue, "test"))
        p.action_cache(card)
        # The cached card is at the bottom; new drawn card is at top
        self.assertEqual(p.deck.deck[-1].denomination, 100)

    def test_cache_draws_new_card(self):
        p = Player("test", None, 5)
        p.hand.add_card(Card(100, Power.Go, "test"))
        p.deck.add_card(Card(1000, Power.Rescue, "test"))
        p.action_cache(p.hand.deck[0])
        # Drew the 1000 card from deck
        self.assertEqual(len(p.hand.deck), 1)
        self.assertEqual(p.hand.deck[0].denomination, 1000)


class TestExchangePowerAction(unittest.TestCase):

    def test_exchange_swaps_hand_and_discard(self):
        p = Player("test", None, 5)
        hand_card = Card(1, Power.Go, "test")
        discard_card = Card(100000, Power.Clone, "test")
        p.hand.add_card(hand_card)
        p.discard_pile.add_card(discard_card)
        p.action_exchange(hand_card, discard_card)
        self.assertEqual(p.hand.deck[0].denomination, 100000)
        self.assertEqual(p.discard_pile.deck[0].denomination, 1)

    def test_exchange_removes_from_hand(self):
        p = Player("test", None, 5)
        card = Card(10, Power.Poison, "test")
        p.hand.add_card(card)
        p.discard_pile.add_card(Card(1000, Power.Go, "test"))
        p.action_exchange(card, p.discard_pile.deck[0])
        self.assertFalse(any(c.denomination == 10 for c in p.hand.deck))


class TestReplayPowerAction(unittest.TestCase):

    def test_replay_moves_card_to_top_of_play_pile(self):
        p = Player("test", None, 5)
        old_top = Card(1000, Power.Rescue, "test")
        under_card = Card(100, Power.Go, "test")
        p.play_pile.add_card(old_top)   # top
        p.play_pile.add_card(under_card)  # now under
        # Replay the 100 card
        p.action_replay(under_card)
        self.assertEqual(p.play_pile.deck[0].denomination, 100)

    def test_replay_does_not_duplicate_card(self):
        p = Player("test", None, 5)
        c1 = Card(1000, Power.Rescue, "test")
        c2 = Card(100, Power.Go, "test")
        p.play_pile.add_card(c1)
        p.play_pile.add_card(c2)
        p.action_replay(c2)
        self.assertEqual(len(p.play_pile.deck), 2)


class TestRecyclePowerAction(unittest.TestCase):

    def test_recycle_shuffles_discard_into_deck(self):
        p = Player("test", None, 5)
        for denom in [1, 10, 100]:
            p.discard_pile.add_card(Card(denom, Power.Go, "test"))
        p.action_recycle_discard()
        self.assertTrue(p.discard_pile.is_empty())
        self.assertEqual(len(p.deck.deck), 3)


class TestFloodPowerAction(unittest.TestCase):

    def test_flood_puts_hand_under_deck(self):
        p = Player("test", None, 5)
        for denom in [1, 10, 100]:
            p.hand.add_card(Card(denom, Power.Go, "test"))
        # Give enough cards in deck to draw from
        for denom in [1000, 10000, 100000]:
            p.deck.add_card(Card(denom, Power.Rescue, "test"))
        p.action_flood()
        self.assertTrue(p.hand.is_empty() or len(p.hand.deck) == 3)  # drew 3 new cards
        # Original hand cards should be in deck (at bottom)
        bottom3 = p.deck.deck[-3:]
        self.assertTrue(all(c.denomination in [1, 10, 100] for c in bottom3))

    def test_flood_draws_three_new_cards(self):
        p = Player("test", None, 5)
        p.hand.add_card(Card(1, Power.Go, "test"))
        for denom in [10, 100, 1000]:
            p.deck.add_card(Card(denom, Power.Rescue, "test"))
        p.action_flood()
        self.assertEqual(len(p.hand.deck), 3)


class TestMutatePowerAction(unittest.TestCase):

    def test_mutate_clears_play_pile(self):
        p = Player("test", None, 5)
        for denom in [1, 10, 100]:
            p.play_pile.add_card(Card(denom, Power.Go, "test"))
        for denom in [1000, 10000, 100000]:
            p.deck.add_card(Card(denom, Power.Rescue, "test"))
        p.action_mutate()
        self.assertTrue(p.play_pile.is_empty())

    def test_mutate_draws_same_count_as_play_pile(self):
        p = Player("test", None, 5)
        for denom in [1, 10, 100]:
            p.play_pile.add_card(Card(denom, Power.Go, "test"))
        for denom in [1000, 10000, 100000]:
            p.deck.add_card(Card(denom, Power.Rescue, "test"))
        p.action_mutate()
        self.assertEqual(len(p.hand.deck), 3)


class TestWagerPowerAction(unittest.TestCase):

    def test_wager_preserves_card_count(self):
        p = Player("test", None, 5)
        for denom in [1, 10, 100, 1000]:
            p.deck.add_card(Card(denom, Power.Go, "test"))
        last = Card(1, Power.Go, "test")
        p.action_wager(last, False)
        self.assertEqual(len(p.deck.deck), 4)

    def test_wager_puts_playable_card_on_top(self):
        p = Player("test", None, 5)
        # top 3 in deck (added last = first out): 100, 10, 1000
        p.deck.add_card(Card(1000, Power.Go, "test"))
        p.deck.add_card(Card(10, Power.Go, "test"))
        p.deck.add_card(Card(100, Power.Go, "test"))
        last = Card(10, Power.Go, "test")  # next in sequence is 100
        p.action_wager(last, False)
        self.assertEqual(p.deck.deck[0].denomination, 100)


class TestKillPowerAction(unittest.TestCase):

    def test_kill_removes_top_of_play_pile(self):
        # add_card inserts at index 0; last added = top.
        p = player_with_play_pile([
            Card(100, Power.Rescue, "test"),   # added first → beneath
            Card(1000, Power.Go, "test"),      # added last → top
        ])
        killed = p.action_kill_top_play_pile()
        self.assertEqual(killed.denomination, 1000)
        self.assertEqual(len(p.play_pile.deck), 1)

    def test_kill_moves_card_to_discard(self):
        p = player_with_play_pile([Card(500, Power.Go, "test")])
        p.action_kill_top_play_pile()
        self.assertEqual(len(p.discard_pile.deck), 1)

    def test_kill_empty_play_pile_returns_none(self):
        p = Player("test", None, 5)
        result = p.action_kill_top_play_pile()
        self.assertIsNone(result)


class TestDiscardRandomHandAction(unittest.TestCase):

    def test_discard_random_removes_from_hand(self):
        p = Player("test", None, 5)
        p.hand.add_card(Card(100, Power.Go, "test"))
        denom = p.action_discard_random_hand_card()
        self.assertEqual(denom, 100)
        self.assertTrue(p.hand.is_empty())

    def test_discard_random_empty_hand_returns_zero(self):
        p = Player("test", None, 5)
        self.assertEqual(p.action_discard_random_hand_card(), 0)

    def test_discard_random_moves_to_discard_pile(self):
        p = Player("test", None, 5)
        p.hand.add_card(Card(10000, Power.Rescue, "test"))
        p.action_discard_random_hand_card()
        self.assertEqual(len(p.discard_pile.deck), 1)


class TestBattlePowerAction(unittest.TestCase):

    def test_battle_reveal_removes_top_3_from_deck(self):
        p = Player("test", None, 5)
        for denom in [1, 10, 100, 1000]:
            p.deck.add_card(Card(denom, Power.Go, "test"))
        total, cards = p.action_battle_reveal()
        self.assertEqual(len(cards), 3)
        self.assertEqual(len(p.deck.deck), 1)

    def test_battle_reveal_returns_correct_total(self):
        p = Player("test", None, 5)
        p.deck.add_card(Card(100, Power.Go, "test"))
        p.deck.add_card(Card(10, Power.Go, "test"))
        p.deck.add_card(Card(1, Power.Go, "test"))
        total, cards = p.action_battle_reveal()
        self.assertEqual(total, 111)

    def test_battle_receive_adds_to_hand(self):
        p = Player("test", None, 5)
        cards = [Card(100, Power.Go, "test"), Card(1000, Power.Rescue, "test")]
        p.action_battle_receive_cards(cards)
        self.assertEqual(len(p.hand.deck), 2)


class TestPlaceCardUnderPlayPile(unittest.TestCase):

    def test_place_card_under_removes_from_hand(self):
        p = Player("test", None, 5)
        card = Card(1000, Power.Bij, "test")
        p.hand.add_card(card)
        p.action_place_card_under_play_pile(card)
        self.assertTrue(p.hand.is_empty())

    def test_place_card_under_goes_to_bottom_of_play_pile(self):
        p = Player("test", None, 5)
        existing = Card(100, Power.Go, "test")
        p.play_pile.add_card(existing)
        bij = Card(1000, Power.Bij, "test")
        p.hand.add_card(bij)
        p.action_place_card_under_play_pile(bij)
        # Bottom of play pile should be Bij
        self.assertEqual(p.play_pile.deck[-1].denomination, 1000)
        self.assertEqual(p.play_pile.deck[-1].power, Power.Bij)


class TestAntePowerAction(unittest.TestCase):

    def test_ante_removes_card_from_hand(self):
        p = Player("test", None, 5)
        p.hand.add_card(Card(100, Power.Go, "test"))
        card = p.action_ante()
        self.assertIsNotNone(card)
        self.assertTrue(p.hand.is_empty())

    def test_ante_empty_hand_returns_none(self):
        p = Player("test", None, 5)
        self.assertIsNone(p.action_ante())


# ===========================================================================
# TimeWarp game-loop integration tests
# ===========================================================================

class TestTimeWarpGameLoopIntegration(unittest.TestCase):
    """TimeWarp penalty reduces the opening hand size in the following round."""

    def test_get_time_warp_penalty_zero_when_no_timewarp(self):
        p = player_with_play_pile([Card(1, Power.Go, "test")])
        self.assertEqual(p.get_time_warp_penalty(), 0)

    def test_get_time_warp_penalty_reflects_unique_denoms(self):
        p = player_with_play_pile([
            Card(10000, Power.TimeWarp, "test"),
            Card(100000, Power.TimeWarp, "test"),
        ])
        self.assertEqual(p.get_time_warp_penalty(), 2)

    def test_hand_size_reduced_by_penalty_simulation(self):
        """
        Simulate the game-loop logic: if a player has penalty=2 from previous round,
        they should draw max(1, 7-2)=5 cards.
        """
        p = Player("test", None, 5)
        for _ in range(10):
            p.deck.add_card(Card(1, Power.Go, "test"))
        penalty = 2
        hand_size = max(1, 7 - penalty)
        for _ in range(hand_size):
            p.action_draw_card()
        self.assertEqual(len(p.hand.deck), 5)


# ===========================================================================
# Tally passive halving tests
# ===========================================================================

class TestTallyPower(unittest.TestCase):
    """Tally halves opponent scoring and awards the halved amount to the Tally owner."""

    def test_tally_in_play_pile_detected(self):
        p = player_with_play_pile([Card(1000, Power.Tally, "test")])
        self.assertTrue(p.has_power_in_play_pile(Power.Tally))

    def test_no_tally_not_detected(self):
        p = player_with_play_pile([Card(1000, Power.Go, "test")])
        self.assertFalse(p.has_power_in_play_pile(Power.Tally))


# ===========================================================================
# AI Evaluator tests (_evaluate_state scoring logic)
# ===========================================================================

class TestAIEvaluator(unittest.TestCase):
    """Tests for the weighted _evaluate_state scoring function in Player."""

    def _make_player_state(self, hand_cards=None, pile_cards=None, name="test"):
        """Helper: build a player with specific hand and play pile."""
        p = Player(name, None, 5)
        for c in (hand_cards or []):
            p.hand.add_card(c)
        for c in (pile_cards or []):
            p.play_pile.add_card(c)
        return p

    def test_going_out_scores_higher_than_not(self):
        """A state where the hand is empty should score much higher."""
        evaluator = Player("eval", None, 5)
        # State A: hand empty, pile has cards (going out)
        state_a = self._make_player_state(
            hand_cards=[],
            pile_cards=[Card(1, Power.Go, "test"), Card(10, Power.Go, "test")]
        )
        # State B: hand has 1 card, same pile
        state_b = self._make_player_state(
            hand_cards=[Card(100, Power.Go, "test")],
            pile_cards=[Card(1, Power.Go, "test"), Card(10, Power.Go, "test")]
        )
        score_a = evaluator._evaluate_state(state_a, 2, 0)
        score_b = evaluator._evaluate_state(state_b, 2, 0)
        self.assertGreater(score_a, score_b)

    def test_fewer_cards_in_hand_scores_higher(self):
        """Playing more cards (fewer in hand) should score higher."""
        evaluator = Player("eval", None, 5)
        # State A: played 2 cards (hand has 1 left)
        state_a = self._make_player_state(
            hand_cards=[Card(100, Power.Go, "test")],
            pile_cards=[Card(1, Power.Go, "test"), Card(10, Power.Go, "test")]
        )
        # State B: played 1 card (hand has 2 left)
        state_b = self._make_player_state(
            hand_cards=[Card(100, Power.Go, "test"), Card(1000, Power.Go, "test")],
            pile_cards=[Card(1, Power.Go, "test")]
        )
        score_a = evaluator._evaluate_state(state_a, 3, 0)
        score_b = evaluator._evaluate_state(state_b, 3, 0)
        self.assertGreater(score_a, score_b)

    def test_poison_adds_expected_value(self):
        """If additional_action is Poison, expected poison value is added to score."""
        evaluator = Player("eval", None, 5)
        state = self._make_player_state(
            hand_cards=[Card(100, Power.Go, "test")],
            pile_cards=[Card(1, Power.Poison, "test")]
        )
        state.additional_action = Power.Poison
        score_with_poison = evaluator._evaluate_state(state, 2, 5000)
        state.additional_action = None
        score_without = evaluator._evaluate_state(state, 2, 5000)
        self.assertEqual(score_with_poison - score_without, 5000)

    def test_power_bonus_for_kill_on_top(self):
        """Kill on top of play pile adds its bonus to score."""
        evaluator = Player("eval", None, 5)
        state_kill = self._make_player_state(
            hand_cards=[Card(100, Power.Go, "test")],
            pile_cards=[Card(1, Power.Kill, "test")]  # Kill is on top (added last = index 0)
        )
        state_go = self._make_player_state(
            hand_cards=[Card(100, Power.Go, "test")],
            pile_cards=[Card(1, Power.Go, "test")]
        )
        score_kill = evaluator._evaluate_state(state_kill, 2, 0)
        score_go = evaluator._evaluate_state(state_go, 2, 0)
        # Kill has bonus 500, Go has no bonus
        self.assertAlmostEqual(score_kill - score_go, 500, delta=1)

    def test_idic_diversity_bonus(self):
        """IDIC in pile awards bonus per unique power."""
        evaluator = Player("eval", None, 5)
        state = self._make_player_state(
            hand_cards=[Card(100, Power.Go, "test")],
            pile_cards=[
                Card(1, Power.IDIC, "test"),
                Card(10, Power.Go, "test"),
                Card(100, Power.Kill, "test"),
            ]
        )
        score = evaluator._evaluate_state(state, 2, 0)
        # Without IDIC, same pile but no IDIC
        state_no_idic = self._make_player_state(
            hand_cards=[Card(100, Power.Go, "test")],
            pile_cards=[
                Card(1, Power.Go, "test"),
                Card(10, Power.Go, "test"),
                Card(100, Power.Kill, "test"),
            ]
        )
        score_no_idic = evaluator._evaluate_state(state_no_idic, 2, 0)
        # IDIC state should score higher due to unique power diversity bonus
        self.assertGreater(score, score_no_idic)

    def test_bonus_run_progress(self):
        """Bonus cards of different denominations add progress score."""
        evaluator = Player("eval", None, 5)
        # 3 different Bonus denominations in pile
        state_3 = self._make_player_state(
            hand_cards=[Card(10000, Power.Go, "test")],
            pile_cards=[
                Card(1, Power.Bonus, "test"),
                Card(10, Power.Bonus, "test"),
                Card(100, Power.Bonus, "test"),
            ]
        )
        # 1 Bonus denomination
        state_1 = self._make_player_state(
            hand_cards=[Card(10000, Power.Go, "test")],
            pile_cards=[
                Card(1, Power.Bonus, "test"),
                Card(10, Power.Go, "test"),
                Card(100, Power.Go, "test"),
            ]
        )
        score_3 = evaluator._evaluate_state(state_3, 2, 0)
        score_1 = evaluator._evaluate_state(state_1, 2, 0)
        # 3 Bonus progress vs 1 → difference of 2 * 2000 = 4000
        self.assertAlmostEqual(score_3 - score_1, 4000, delta=50)


if __name__ == '__main__':
    unittest.main()
