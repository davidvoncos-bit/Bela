# -*- coding: utf-8 -*-
import random
import os
from functools import partial

# Optional imports for image mode
try:
    import tkinter as tk
    from PIL import Image, ImageTk
    print("Uspjeh")
except ImportError:
    tk = None  # Stay in text mode if Tkinter/Pillow missing
    print("Minus")


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

# Example trump suit (could be chosen at game start)
TRUMP_SUIT = "h"

CARD_FOLDER = "karte"  # Cropped cards will be stored here


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


def show_hands_text(hands):
    for i, hand in enumerate(hands, start=1):
        print(f"Player {i}: {' '.join(hand)}")


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


# =====================
# IMAGE DISPLAY
# =====================
def load_card_image(card, size=(80, 120), rotate=0):
    """
    Loads a single card PNG, optionally rotates it (degrees), and returns a PhotoImage.
    """
    filename = os.path.join(CARD_FOLDER, f"{card}.png")
    if not os.path.exists(filename):
        raise FileNotFoundError(f"Missing image: {filename}")
    img = Image.open(filename).convert("RGBA").resize(size, Image.Resampling.LANCZOS)
    if rotate:
        img = img.rotate(rotate, expand=True)
    return ImageTk.PhotoImage(img)


def show_hands_images(hands):
    if tk is None:
        print("Image mode unavailable: Tkinter/Pillow not installed.")
        return

    root = tk.Tk()
    root.title("Belote - German Suited Cards")
    root.geometry("1100x800")

    def safe_close():
        try:
            root.destroy()
            root.quit()
        except Exception:
            pass

    root.protocol("WM_DELETE_WINDOW", safe_close)

    # Message box
    message_box = tk.Text(root, height=8, width=50)
    message_box.grid(row=2, column=0, columnspan=3, sticky="ew", pady=5)

    def log(msg):
        message_box.insert("end", msg + "\n")
        message_box.see("end")

    # --- Frames for hands ---
    top_f = tk.Frame(root, width=360, height=260)
    top_f.grid(row=0, column=1, pady=8)
    top_f.grid_propagate(False)

    bottom_f = tk.Frame(root, width=360, height=260)
    bottom_f.grid(row=2, column=1, pady=8)
    bottom_f.grid_propagate(False)

    left_f = tk.Frame(root, width=260, height=500)
    left_f.grid(row=1, column=0, padx=8, sticky="ns")
    left_f.grid_propagate(False)

    right_f = tk.Frame(root, width=260, height=500)
    right_f.grid(row=1, column=2, padx=8, sticky="ns")
    right_f.grid_propagate(False)

    # --- Center "table" ---
    center_f = tk.Frame(root, relief="groove", borderwidth=3, bg="green")
    center_f.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")

    # --- Root grid sizing ---
    root.grid_rowconfigure(0, weight=1, minsize=260)
    root.grid_rowconfigure(1, weight=1, minsize=280)
    root.grid_rowconfigure(2, weight=1, minsize=260)

    root.grid_columnconfigure(0, weight=1, minsize=280)
    root.grid_columnconfigure(1, weight=1, minsize=360)
    root.grid_columnconfigure(2, weight=1, minsize=280)

    controls_f = tk.Frame(root)
    controls_f.grid(row=3, column=1, pady=10)

    # Player played cards shown in center
    played_labels = [None, None, None, None]

    # Keep strong references to images
    root.images = []
    card_widgets = [[], [], [], []]

    # Current player (0 = bottom, 1 = right, 2 = top, 3 = left)
    current_player = [0]

    # Track trick progress
    trick_cards = []
    trick_in_progress = [False]

    # Team scores
    team_scores = {"A": 0, "B": 0}
    
    # Pending declaration points (shown separately, not yet merged into score)
    declaration_bonus = {"A": 0, "B": 0}
    winning_declarations_text = ["Winning declarations: none"]
    def update_score_label():
        def fmt(team):
            base = team_scores[team]
            bonus = declaration_bonus[team]
            return f"{base} (+{bonus})" if bonus > 0 else f"{base}"
    
        score_label.config(
            text=(
                f"Scores - Team A: {fmt('A')} | "
                f"Team B: {fmt('B')}"
            )
        )
    
    winning_declarations_text = ["Declarations: none"]
    def update_declaration_label():
        declaration_label.config(text=winning_declarations_text[0])
    
    # Turn indicator
    turn_label = tk.Label(root, text="Turn: Player 0", font=("Arial", 16))
    turn_label.grid(row=4, column=1, pady=6)

    # Score indicator
    score_label = tk.Label(root, text="Scores - Team A: 0 | Team B: 0", font=("Arial", 14))
    score_label.grid(row=5, column=1, pady=6)
    
    # Declaration indicator
    declaration_label = tk.Label(
    root,
    text="Declarations: none",
    font=("Arial", 12),
    wraplength=900,
    justify="center"
)
    declaration_label.grid(row=6, column=1, pady=4)


    def apply_declarations():
        """
        Only the stronger team's declarations count,
        but they are stored in declaration_bonus instead of being added
        directly into team_scores.

        Also logs:
        - each player's declarations
        - each team's best declaration
        - overall strongest declaration
        - players who had that strongest declaration
        """
        declaration_bonus["A"] = 0
        declaration_bonus["B"] = 0
        winning_declarations_text[0] = "Declarations: none"

        player_declarations = {}
        player_best = {}

        for player_idx in range(4):
            decls = find_declarations(hands[player_idx])
            player_declarations[player_idx] = decls
            player_best[player_idx] = best_declaration_for_player(decls)

            if decls:
                log(f"Player {player_idx} declarations:")
                for d in decls:
                    log(f"  - {declaration_to_text(d)}")
            else:
                log(f"Player {player_idx} declarations: none")

        team_best = {"A": None, "B": None}
        team_best_player = {"A": None, "B": None}
        team_totals = {"A": 0, "B": 0}

        for player_idx in range(4):
            team = team_of_player(player_idx)
            decls = player_declarations[player_idx]
            best = player_best[player_idx]

            team_totals[team] += total_declaration_points(decls)

            if best is None:
                continue

            if team_best[team] is None:
                team_best[team] = best
                team_best_player[team] = player_idx
            else:
                cmp_res = compare_declarations(best, team_best[team])
                if cmp_res == 1:
                    team_best[team] = best
                    team_best_player[team] = player_idx
                elif cmp_res == 0:
                    if player_idx < team_best_player[team]:
                        team_best_player[team] = player_idx

        # Log team best declarations
        if team_best["A"] is not None:
            log(
                f"Team A best declaration: {declaration_to_text(team_best['A'])} "
                f"(Player {team_best_player['A']})"
            )
        else:
            log("Team A best declaration: none")

        if team_best["B"] is not None:
            log(
                f"Team B best declaration: {declaration_to_text(team_best['B'])} "
                f"(Player {team_best_player['B']})"
            )
        else:
            log("Team B best declaration: none")
        
        # No declarations at all
        if team_best["A"] is None and team_best["B"] is None:
            log("No declarations on either team.")
            update_score_label()
            return
        
        # Determine winning team
        if team_best["A"] is not None and team_best["B"] is None:
            winner_team = "A"
            strongest_decl = team_best["A"]
        elif team_best["B"] is not None and team_best["A"] is None:
            winner_team = "B"
            strongest_decl = team_best["B"]
        else:
            cmp_res = compare_declarations(team_best["A"], team_best["B"])
            if cmp_res == 1:
                winner_team = "A"
                strongest_decl = team_best["A"]
            elif cmp_res == -1:
                winner_team = "B"
                strongest_decl = team_best["B"]
            else:
                if team_best_player["A"] < team_best_player["B"]:
                    winner_team = "A"
                    strongest_decl = team_best["A"]
                else:
                    winner_team = "B"
                    strongest_decl = team_best["B"]

        # Store only as pending bonus
        declaration_bonus[winner_team] = team_totals[winner_team]
        winning_players = [0, 2] if winner_team == "A" else [1, 3]
        winning_parts = []
        
        for player_idx in winning_players:
            decls = player_declarations[player_idx]
            if decls:
                decl_text = " ; ".join(" ".join(d["cards"]) for d in decls)
                winning_parts.append(f"P{player_idx}: {decl_text}")
        
        if winning_parts:
            winning_declarations_text[0] = (
                f"Declarations: Team {winner_team} -> " + " | ".join(winning_parts)
            )
        else:
            winning_declarations_text[0] = "Declarations: none"

        # Find all players who had an equally strongest declaration
        strongest_players = []
        for player_idx in range(4):
            for d in player_declarations[player_idx]:
                if compare_declarations(d, strongest_decl) == 0 and compare_declarations(strongest_decl, d) == 0:
                    strongest_players.append(player_idx)
                    break

        log(f"Overall strongest declaration: {declaration_to_text(strongest_decl)}")
        log(f"Players with strongest declaration: {strongest_players}")
        log(
            f"Team {winner_team} wins declarations and keeps +{declaration_bonus[winner_team]} pending."
        )

        update_score_label()
        update_declaration_label()
        

    def new_game():
        log("=== Starting new game ===")

        team_scores["A"] = 0
        team_scores["B"] = 0
        declaration_bonus["A"] = 0
        declaration_bonus["B"] = 0
        winning_declarations_text[0] = "Declarations: none"
        update_declaration_label()
        update_score_label()

        for lbl in played_labels:
            if lbl:
                lbl.destroy()
        for i in range(4):
            played_labels[i] = None

        trick_cards.clear()
        trick_in_progress[0] = False
        current_player[0] = 0
        message_box.delete("1.0", "end")

        global deck
        deck = create_deck()
        shuffle_deck(deck)
        new_hands = deal(deck)
        for i in range(4):
            hands[i] = new_hands[i]

        draw_hands()
        apply_declarations()
        turn_label.config(text=f"Turn: Player {current_player[0]}")

    def restart_round():
        log("=== Restarting current round ===")

        team_scores["A"] = 0
        team_scores["B"] = 0
        declaration_bonus["A"] = 0
        declaration_bonus["B"] = 0
        winning_declarations_text[0] = "Declarations: none"
        update_declaration_label()
        update_score_label()

        for lbl in played_labels:
            if lbl:
                lbl.destroy()
        for i in range(4):
            played_labels[i] = None

        trick_cards.clear()
        trick_in_progress[0] = False
        current_player[0] = 0

        new_hands = deal(deck)
        for i in range(4):
            hands[i] = new_hands[i]

        draw_hands()
        apply_declarations()
        turn_label.config(text=f"Turn: Player {current_player[0]}")

    new_game_btn = tk.Button(controls_f, text="New Game", command=new_game)
    new_game_btn.grid(row=0, column=0, padx=10)

    restart_round_btn = tk.Button(controls_f, text="Restart Round", command=restart_round)
    restart_round_btn.grid(row=0, column=1, padx=10)

    def draw_hands():
        """Draw all four players' hands in a 2x4 layout"""
        for i in range(4):
            for w in card_widgets[i]:
                w.destroy()
            card_widgets[i] = []

        try:
            left_f.config(width=280, height=520)
            right_f.config(width=280, height=520)
            left_f.grid_propagate(False)
            right_f.grid_propagate(False)
        except Exception:
            try:
                left_f.pack_propagate(False)
                right_f.pack_propagate(False)
            except Exception:
                pass

        def place_horizontal_2x4(lbl, index):
            row = index // 4
            col = index % 4
            lbl.grid(row=row, column=col, padx=3, pady=3)

        def place_vertical_2x4(lbl, index):
            row = index % 4
            col = index // 4
            lbl.grid(row=row, column=col, padx=0, pady=1)

        # Bottom player (0)
        for i, card in enumerate(hands[0]):
            try:
                im = load_card_image(card, size=(80, 120))
                lbl = tk.Label(bottom_f, image=im, bd=0)
                lbl.image = im
                lbl.card_image = im
                root.images.append(im)
                lbl.card_name = card
                lbl.card_rotate = 0
                lbl.bind("<Button-1>", partial(on_card_click, 0, card, lbl))
            except FileNotFoundError:
                lbl = tk.Label(bottom_f, text=card, font=("Arial", 10))

            place_horizontal_2x4(lbl, i)
            card_widgets[0].append(lbl)

        # Right player (1)
        for i, card in enumerate(hands[1]):
            try:
                im = load_card_image(card, size=(80, 120), rotate=-90)
                lbl = tk.Label(right_f, image=im, bd=0)
                lbl.image = im
                lbl.card_image = im
                root.images.append(im)
                lbl.card_name = card
                lbl.card_rotate = -90
                lbl.bind("<Button-1>", partial(on_card_click, 1, card, lbl))
            except FileNotFoundError:
                lbl = tk.Label(right_f, text=card, font=("Arial", 9))

            place_vertical_2x4(lbl, i)
            card_widgets[1].append(lbl)

        # Top player (2)
        for i, card in enumerate(hands[2]):
            try:
                im = load_card_image(card, size=(80, 120))
                lbl = tk.Label(top_f, image=im, bd=0)
                lbl.image = im
                lbl.card_image = im
                root.images.append(im)
                lbl.card_name = card
                lbl.card_rotate = 0
                lbl.bind("<Button-1>", partial(on_card_click, 2, card, lbl))
            except FileNotFoundError:
                lbl = tk.Label(top_f, text=card, font=("Arial", 10))

            place_horizontal_2x4(lbl, i)
            card_widgets[2].append(lbl)

        # Left player (3)
        for i, card in enumerate(hands[3]):
            try:
                im = load_card_image(card, size=(80, 120), rotate=90)
                lbl = tk.Label(left_f, image=im, bd=0)
                lbl.image = im
                lbl.card_image = im
                root.images.append(im)
                lbl.card_name = card
                lbl.card_rotate = 90
                lbl.bind("<Button-1>", partial(on_card_click, 3, card, lbl))
            except FileNotFoundError:
                lbl = tk.Label(left_f, text=card, font=("Arial", 9))

            place_vertical_2x4(lbl, i)
            card_widgets[3].append(lbl)

    def get_image_for_card(card, rotate=0):
        for widgets in card_widgets:
            for w in widgets:
                if getattr(w, "card_name", None) == card and getattr(w, "card_rotate", 0) == rotate:
                    return getattr(w, "card_image", None)
        return None

    def place_played_card(player_idx, card):
        """Show card in center area in correct seat position."""
        positions = [
            {"relx": 0.5, "rely": 0.85, "anchor": "center"},  # bottom
            {"relx": 0.85, "rely": 0.5, "anchor": "center"},  # right
            {"relx": 0.5, "rely": 0.15, "anchor": "center"},  # top
            {"relx": 0.15, "rely": 0.5, "anchor": "center"},  # left
        ]

        try:
            rotate = 0
            if player_idx == 1:
                rotate = -90
            elif player_idx == 3:
                rotate = 90

            im = get_image_for_card(card, rotate=rotate)
            if im is None:
                im = load_card_image(card, size=(90, 135), rotate=rotate)

            lbl = tk.Label(center_f, image=im, bg="green")
            lbl.image = im
            root.images.append(im)
            lbl.place(**positions[player_idx])

            if played_labels[player_idx]:
                played_labels[player_idx].destroy()
            played_labels[player_idx] = lbl
        except FileNotFoundError:
            lbl = tk.Label(center_f, text=card, font=("Arial", 12), bg="green")
            lbl.place(**positions[player_idx])
            played_labels[player_idx] = lbl

    def on_card_click(player_idx, card, widget, event=None):
        log(f"Player {player_idx} played {card}")

        if trick_in_progress[0]:
            return

        if player_idx != current_player[0]:
            log(f"Not Player {player_idx}'s turn.")
            return

        allowed = legal_moves(hands[player_idx], trick_cards, TRUMP_SUIT)
        if card not in allowed:
            log(f"Illegal move: {card}. Allowed: {allowed}")
            return

        try:
            idx = hands[player_idx].index(card)
        except ValueError:
            log(f"Card {card} not found in Player {player_idx}'s hand (maybe already played).")
            return

        hands[player_idx].pop(idx)

        if widget in card_widgets[player_idx]:
            card_widgets[player_idx].remove(widget)
        try:
            widget.destroy()
        except Exception:
            pass

        trick_cards.append((player_idx, card))
        place_played_card(player_idx, card)

        if len(trick_cards) == 4:
            trick_in_progress[0] = True
            root.after(1500, clear_trick)

        current_player[0] = (current_player[0] + 1) % 4
        turn_label.config(text=f"Turn: Player {current_player[0]}")

    def card_points(card, trump_suit):
        rank, suit = card[:-1], card[-1]
        if suit == trump_suit:
            points_map = {"J": 20, "9": 14, "A": 11, "X": 10, "K": 4, "D": 3, "8": 0, "7": 0}
        else:
            points_map = {"A": 11, "X": 10, "K": 4, "D": 3, "J": 2, "9": 0, "8": 0, "7": 0}
        return points_map.get(rank, 0)

    def clear_trick():
        """Remove all played cards and determine trick winner."""
        if len(trick_cards) == 4:
            lead_suit = trick_cards[0][1][-1]
            best = trick_cards[0]
            best_val = card_value(best[1], lead_suit, TRUMP_SUIT)

            for play in trick_cards[1:]:
                val = card_value(play[1], lead_suit, TRUMP_SUIT)
                if val > best_val:
                    best = play
                    best_val = val

            winner_idx = best[0]
            log(f"Trick winner: Player {winner_idx}")

            trick_points = sum(card_points(card, TRUMP_SUIT) for _, card in trick_cards)

            if len(hands[0]) == 0:
                trick_points += 10

            if winner_idx in (0, 2):
                team_scores["A"] += trick_points
            else:
                team_scores["B"] += trick_points

            update_score_label()

            current_player[0] = winner_idx
            turn_label.config(text=f"Turn: Player {winner_idx}")

        for lbl in played_labels:
            if lbl is not None:
                lbl.destroy()
        for i in range(4):
            played_labels[i] = None

        trick_cards.clear()
        trick_in_progress[0] = False

    draw_hands()
    apply_declarations()
    root.mainloop()


# =====================
# MAIN
# =====================
def main():
    try:
        global root
        root.destroy()
    except NameError:
        pass
    except Exception:
        pass

    global deck
    deck = create_deck()
    shuffle_deck(deck)
    hands = deal(deck)

    show_hands_text(hands)

    if os.path.exists(CARD_FOLDER):
        show_hands_images(hands)
    else:
        print("NOPE")


if __name__ == "__main__":
    main()