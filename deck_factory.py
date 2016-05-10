from enum import Enum

Power = Enum("Power", "Bonus Clone Discard Go Poison Rescue Reverse Skip")

class Card:

    def __init__(self, denomination, power, owner):
        denomination = denomination
        power = power
        owner = owner

