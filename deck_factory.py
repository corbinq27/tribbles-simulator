from enum import Enum
import json
import re

Power = Enum("Power", "Bonus Clone Discard Go Poison Rescue Reverse Skip")

class Card:

    def __init__(self, denomination, power, owner):
        self.denomination = denomination
        self.power = power
        self.owner = owner

class Owner:

    def __init__(self, name):
        name = name

class DeckFactory:

    def __init__(self, name):
        self.deck = []
        self.owner = Owner(name)

    #TODO: Add a card import verifier to ensure only actual existing tribbles cards are added to a deck.
    def deck_import(self, json_formatted_deck):
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

