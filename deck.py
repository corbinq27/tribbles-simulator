from enum import Enum
import json
import re
import random

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


class Owner:
    """private Class to represent the Owner object."""
    def __init__(self, name):
        self.name = name


class Deck:
    """Deck"""
    def __init__(self, name, json_formatted_deck_path=None):
        self.deck = []
        self.owner = Owner(name)

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
        self.deck.remove(card)
        return card

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

    def get_denomination_sum(self):
        """
        get the sum total of all of the denominations of the cards in this deck
        """
        to_return = 0
        for each_card in self.deck:
            to_return += each_card.denomination

        return to_return

    def shuffle(self, seed=None):
        if seed:
            random.seed(seed)
            random.shuffle(self.deck)
            random.seed()
        else:
            random.shuffle(self.deck)

