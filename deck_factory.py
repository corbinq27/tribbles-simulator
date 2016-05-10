from enum import Enum
import json

Power = Enum("Power", "Bonus Clone Discard Go Poison Rescue Reverse Skip")

class Card:

    def __init__(self, denomination, power, owner):
        denomination = denomination
        power = power
        owner = owner

class DeckFactory:

    def __init__(self):
        deck = []

    def deck_import(self, json_formatted_deck):
        """An example deck might look like this:

        """

