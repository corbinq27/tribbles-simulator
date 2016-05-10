from enum import Enum

Power = Enum("Power", "Bonus Clone Discard Go Poison Rescue Reverse Skip")

class card:

    def __init__(denomination, power, owner):
        denomination = denomination
        power = power
        owner = owner

