import random

# =====================
# CONFIGURATION
# =====================
RANKS = ["7", "8", "9", "X", "J", "D", "K", "A"]   # Unter=J, Ober=Q
SUITS = ["t", "k", "h", "p"]  # Eichel, Grün, Herz, Schellen

# Rank order for non-trump and trump
NON_TRUMP_ORDER = ["7", "8", "9", "J", "D", "K", "X", "A"]
TRUMP_ORDER = ["7", "8", "D", "K", "X", "A", "9", "J"]

# For declarations: runs are checked in this order
DECLARATION_ORDER = ["7", "8", "9", "X", "J", "D", "K", "A"]

# For comparing top card of sequences:
# higher(AKDJX987) top card wins
SEQUENCE_TOP_COMPARE_ORDER = ["7", "8", "9", "X", "J", "D", "K", "A"]



# =====================
# CORE GAME FUNCTIONS
# =====================
def create_deck():
    return [f"{rank}{suit}" for suit in SUITS for rank in RANKS]


def shuffle_deck(deck):
    random.shuffle(deck)


def sort_key(a):
    vrati = 8 * SUITS.index(a[1])
    vrati += RANKS.index(a[0])
    return vrati


def sort_cards(hands):
    for i in range(4):
        hands[i].sort(key=sort_key)
    return hands


def deal(deck):
    return sort_cards([deck[i*8:(i+1)*8] for i in range(4)])


def card_value(card, lead_suit, trump_suit):
    """Return a tuple for comparing trick cards."""
    rank, suit = card[:-1], card[-1]

    if suit == trump_suit:
        return (2, TRUMP_ORDER.index(rank))  # trump beats everything
    elif suit == lead_suit:
        return (1, NON_TRUMP_ORDER.index(rank))  # same suit as lead
    else:
        return (0, NON_TRUMP_ORDER.index(rank))  # irrelevant suit


def legal_moves(hand, trick_cards, trump_suit):
    """Return the set of legal cards the player can play under Belote rules."""
    if not trick_cards:  # Player is leading
        return set(hand)

    lead_suit = trick_cards[0][1][-1]

    follow = [c for c in hand if c[-1] == lead_suit]
    if not follow:
        follow = [c for c in hand if c[-1] == trump_suit]
    if not follow:
        return set(hand)

    highest_val = (-1, -1)
    for _, card in trick_cards:
        val = card_value(card, lead_suit, trump_suit)
        if val > highest_val:
            highest_val = val

    better_follow = [c for c in follow if card_value(c, lead_suit, trump_suit) > highest_val]
    return set(better_follow) if better_follow else set(follow)


def card_points(card, trump_suit):
    rank, suit = card[:-1], card[-1]
    if suit == trump_suit:
        points_map = {"J": 20, "9": 14, "A": 11, "X": 10, "K": 4, "D": 3, "8": 0, "7": 0}
    else:
        points_map = {"A": 11, "X": 10, "K": 4, "D": 3, "J": 2, "9": 0, "8": 0, "7": 0}
    return points_map.get(rank, 0)



# =====================
# DECLARATIONS
# =====================
def four_kind_points(rank):
    """Returns points for four of a kind, or None if not a valid declaration."""
    if rank in ("7", "8"):
        return None
    if rank == "J":
        return 200
    if rank == "9":
        return 150
    return 100  # X, D, K, A


def sequence_points(length):
    """Returns points for a sequence, or None if too short."""
    if length < 3:
        return None
    if length == 3:
        return 20
    if length == 4:
        return 50
    return 100  # 5+


def find_four_of_a_kind(hand):
    """
    Valid four-of-a-kind declarations only.
    4x7 and 4x8 are ignored.
    """
    by_rank = {}
    for card in hand:
        rank = card[:-1]
        by_rank.setdefault(rank, []).append(card)

    declarations = []
    for rank, cards in by_rank.items():
        if len(cards) == 4:
            pts = four_kind_points(rank)
            if pts is not None:
                declarations.append({
                    "type": "four_kind",
                    "rank": rank,
                    "cards": sorted(cards, key=sort_key),
                    "points": pts,
                    "top_rank": rank
                })
    return declarations


def find_sequences(hand):
    """
    Returns maximal same-suit runs of length >= 3.
    Example: 7h 8h 9h Xh -> one sequence of 4
    """
    declarations = []
    order_index = {rank: i for i, rank in enumerate(DECLARATION_ORDER)}

    by_suit = {}
    for card in hand:
        rank, suit = card[:-1], card[-1]
        by_suit.setdefault(suit, []).append(card)

    for suit, cards in by_suit.items():
        sorted_cards = sorted(cards, key=lambda c: order_index[c[:-1]])
        indices = [order_index[c[:-1]] for c in sorted_cards]

        start = 0
        for i in range(1, len(indices) + 1):
            if i < len(indices) and indices[i] == indices[i - 1] + 1:
                continue

            run_cards = sorted_cards[start:i]
            run_len = len(run_cards)
            pts = sequence_points(run_len)
            if pts is not None:
                declarations.append({
                    "type": "sequence",
                    "suit": suit,
                    "length": run_len,
                    "cards": run_cards,
                    "points": pts,
                    "top_rank": run_cards[-1][:-1]
                })
            start = i

    return declarations


def find_declarations(hand):
    declarations = []
    declarations.extend(find_four_of_a_kind(hand))
    declarations.extend(find_sequences(hand))
    return declarations


def declaration_to_text(declaration):
    if declaration["type"] == "four_kind":
        return f"four of a kind {declaration['rank']} ({' '.join(declaration['cards'])}) -> {declaration['points']}"

    if declaration["type"] == "sequence":
        return (
            f"sequence {declaration['length']} in suit {declaration['suit']} "
            f"({' '.join(declaration['cards'])}) -> {declaration['points']}"
        )

    return str(declaration)


def compare_sequence_tops(rank1, rank2):
    """
    Compare sequence top cards using order AKDJX987 where higher wins.
    Internally we map that to increasing strength: 7 < 8 < 9 < X < J < D < K < A.
    """
    idx = {rank: i for i, rank in enumerate(SEQUENCE_TOP_COMPARE_ORDER)}
    if idx[rank1] > idx[rank2]:
        return 1
    if idx[rank1] < idx[rank2]:
        return -1
    return 0


def compare_four_kind(rank1, rank2):
    """
    Compare sequence top cards using order AXKDJ987 where higher wins.
    Internally we map that to increasing strength: 7 < 8 < 9 < J < D < K < X < A.
    """
    idx = {rank: i for i, rank in enumerate(NON_TRUMP_ORDER)}
    if idx[rank1] > idx[rank2]:
        return 1
    if idx[rank1] < idx[rank2]:
        return -1
    return 0


def compare_declarations(d1, d2):
    """
    Returns:
      1  if d1 stronger
     -1  if d2 stronger
      0  if equal

    Rules:
    - Higher points wins
    - Exception:
        5+ sequence beats only 100-point four of a kind
    - If both are sequences with same points, higher top card wins
    - If still same, equal
    """

    d1_is_long_seq = (d1["type"] == "sequence" and d1["length"] >= 5)
    d2_is_long_seq = (d2["type"] == "sequence" and d2["length"] >= 5)

    d1_is_100_four = (d1["type"] == "four_kind" and d1["points"] == 100)
    d2_is_100_four = (d2["type"] == "four_kind" and d2["points"] == 100)

    # Special rule: 5+ sequence beats only 100-point four of a kind
    if d1_is_long_seq and d2_is_100_four:
        return 1
    if d2_is_long_seq and d1_is_100_four:
        return -1

    # General rule: points first
    if d1["points"] > d2["points"]:
        return 1
    if d1["points"] < d2["points"]:
        return -1

    # If both are sequences with same points, higher top card wins
    if d1["type"] == "sequence" and d2["type"] == "sequence":
        return compare_sequence_tops(d1["top_rank"], d2["top_rank"])
    
    # If both are 4 of a kind, higher card wins
    if d1["type"] == "four_kind" and d2["type"] == "four_kind":
        return compare_four_kind(d1["rank"], d2["rank"])
    
    # Otherwise equal
    return 0


def best_declaration_for_player(declarations):
    """Returns strongest declaration in a player's list, or None."""
    if not declarations:
        return None

    best = declarations[0]
    for d in declarations[1:]:
        if compare_declarations(d, best) == 1:
            best = d
    return best


def team_of_player(player_idx):
    return "A" if player_idx in (0, 2) else "B"


def total_declaration_points(declarations):
    return sum(d["points"] for d in declarations)