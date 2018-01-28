from enum import Enum
import json
import re
import random
import math
import copy

Power = Enum("Power", "Bonus Clone Discard Go Poison Rescue Reverse Skip")


class Card:
    """private Class to represent the Card object."""
    def __init__(self, denomination, power, owner):
        self.denomination = denomination
        self.power = power
        self.owner = owner

    def __repr__(self):
        return "Card Instance. Power: %s Denom: %s Owner: %s" % (self.power, self.denomination, self.owner)

    def __str__(self):
         return "Card Instance. Power: %s Denom: %s Owner: %s" % (self.power, self.denomination, self.owner)


    def get_card_categorization(self):
        """
        returns a string concatenating the denomination and power.  For example, if the card's denomination
        is 100 and the card's power is Poison, then the string returned will be "100 Power.Poison"
        """
        return "%s %s" % (self.denomination, self.power)

    def is_actionable_power(self):
        """
        Returns true if the power for this card is actionable (that is, the player could cause the player to play an
         additonal card on his turn because of the card's power.  Currently, the list of actionable powers are Rescue
         and Go.
        """
        return self.power == Power.Go or self.power == Power.Rescue

    def is_playable(self, last_played_card, is_chain_broken=False):
        """
        Given the last played card within the game, returns True if this card can be played or False if not.
        a 1 can also be played if the chain was broken.
        * This card can be played if the last card played has a denomination 10 times smaller than this card.
        * This card can be played if the last card played and this card have the same denomination and this card
        has a power of clone.
        * This card can be played if the last card played was denomination 100,000 and this card is denomination 1.
        * This card can be played if the last card played is a None object and this card is denomincation 1.
        """
        last_denom = None
        if last_played_card is None:
            if self.denomination == 1:
                return True
            else:
                return False
        else:
            last_denom = last_played_card.denomination

        if self.denomination == (last_denom * 10):
            return True
        elif (self.denomination == last_denom) and self.power == Power.Clone:
            return True
        elif self.denomination == 1 and last_denom == 100000:
            return True
        elif is_chain_broken and self.denomination == 1:
            return True
        else:
            return False

    def get_copy(self):
        """return a new instance of this card in the same state as this card"""
        d = {"denomination": self.denomination, "power": self.power, "owner": self.owner}
        card_to_return = Card(d["denomination"], d["power"], d["owner"])
        return card_to_return

class Deck:
    """Deck"""
    def __init__(self, name, json_formatted_deck_path=None):
        self.deck = []
        self.owner = name

        if json_formatted_deck_path != None:
            self.deck_import(json_formatted_deck_path)

    #TODO: Add a card import verifier to ensure only actual existing tribbles cards are added to a deck.
    def deck_import(self, json_formatted_deck_path):
        """An example deck might look like this:
            {
                "cards":
                    [
                        "2 100 Tribbles - Rescue",
                        "1 10 Tribbles - Copy",
                        "4 100 Tribbles - Copy"
                    ]
            }
        """
        with open(json_formatted_deck_path, "r") as fp:
            deck_dict = json.load(fp)
            for each_item in deck_dict["cards"]:
                self.deck = self.deck + self.convert_string_to_cards(each_item)

    def convert_string_to_cards(self, string):
        """
        parses cards in the format '<quantity> <denomination> Tribbles - <power>' to one or more Card objects.
        Returns all cards as a list.
        """
        quantity = int(re.findall("(\d+)\s\d+", string)[0])
        denomination = int(re.findall("\d+\s(\d+)\s", string)[0])
        power = re.findall("- (.+)$", string)[0]

        to_return = []
        for i in range(0, quantity):
            to_return.append(Card(denomination, Power[power], self.owner))

        return to_return

    def remove_card(self, card):
        for each_card in self.deck:
            if (each_card.denomination == card.denomination) and (each_card.power == card.power):
                self.deck.remove(each_card)
                return each_card

    def add_card(self, card):
        self.deck.insert(0, card)

    def is_empty(self):
        "return True if deck empty. False otherwise."
        if len(self.deck) > 0:
            return False
        if len(self.deck) == 0:
            return True
        else:
            raise ValueError

    def get_top_card_and_remove_card(self):
        """
        Remove the top card of this deck and return it.
        """
        return self.deck.pop(0)

    def get_top_card_of_deck(self):
        """
        Peek at the top card of the deck.  Return None if the deck is empty.
        """
        if self.is_empty():
            return None
        else:
            return self.deck[0]

    def get_denomination_sum(self):
        """
        get the sum total of all of the denominations of the cards in this deck
        """
        to_return = 0
        for each_card in self.deck:
            to_return += each_card.denomination

        return to_return

    def get_expected_poison_value(self):
        """
        get the sum of all of the denominations of the cards in the deck over the number
        of cards in the deck as an integer rounded up.
        """
        try:
            value_to_return = int(math.ceil(self.get_denomination_sum() / len(self.deck)))
        except ZeroDivisionError:
            value_to_return = 0
        return value_to_return

    def shuffle(self, seed=None):
        if seed:
            random.seed(seed)
            random.shuffle(self.deck)
            random.seed()
        else:
            random.shuffle(self.deck)

    def get_all_unique_cards(self):
        """
        convenience function.  It is useful to get a list of the different type of cards in a deck.  Returns a list
        of what cards are in this deck without returning a second copy of that card.
        """
        to_return = []

        for each_card in self.deck:
            card_in_to_return = False
            for every_card in to_return:
                if each_card.get_card_categorization() == every_card.get_card_categorization():
                    card_in_to_return = True
            if card_in_to_return == False:
                to_return.append(each_card)

        return to_return

    def pretty_print(self, number_to_print=None):
        """
        returns a string represeentation of the deck.  If only a certain number are desired to
        be printed, it can be specified.
        """
        to_return = ""
        if number_to_print:
            for each_card in self.deck[:number_to_print]:
                if each_card.denomination == 1:
                    to_return += "%s Tribble %s, \r\n" % (each_card.denomination, each_card.power)
                else:
                    to_return += "%s Tribbles %s, \r\n" % (each_card.denomination, each_card.power)

        else:

            for each_card in self.deck:
                if each_card.denomination == 1:
                    to_return += "%s Tribble %s, \r\n" % (each_card.denomination, each_card.power)
                else:
                    to_return += "%s Tribbles %s, \r\n" % (each_card.denomination, each_card.power)

        return to_return

    def get_copy(self):
        """Return a new instance of this deck class in the same state as itself"""
        deck_to_return = []
        for each_card in self.deck:
            deck_to_return.append(each_card.get_copy())
        dic = {"owner": self.owner}
        d = Deck(dic["owner"])
        d.deck = deck_to_return

        return d
