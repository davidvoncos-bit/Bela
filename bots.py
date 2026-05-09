import random
from rules import SUITS

class RandomBot:
    name = "Random Bot"

    def choose_trump(self, state, player_idx):
        return random.choice(SUITS + ["pass"])

    def choose_card(self, state, player_idx, legal_cards):
        return random.choice(list(legal_cards))

    def call_bela(self, state, player_idx):
        return True