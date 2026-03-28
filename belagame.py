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
    hands.sort
    for i in range(4): hands[i].sort(key = sort_key)
    return hands


def deal(deck):
    return sort_cards([deck[i*8:(i+1)*8] for i in range(4)])

def card_value(card, lead_suit, trump_suit):
    """Return a tuple (is_trump, same_suit, rank_index) for comparing cards."""
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
        # expand=True so the rotated image canvas enlarges instead of cropping
        img = img.rotate(rotate, expand=True)
    return ImageTk.PhotoImage(img)



def show_hands_images(hands):
    if tk is None:
        print("Image mode unavailable: Tkinter/Pillow not installed.")
        return

    
    def new_game():
        log("=== Starting new game ===")
        
        team_scores["A"] = 0
        team_scores["B"] = 0
        score_label.config(text="Scores - Team A: 0 | Team B: 0")

        # Clear played cards in center
        for lbl in played_labels:
            if lbl:
                lbl.destroy()
        for i in range(4):
            played_labels[i] = None
    
        trick_cards.clear()
        trick_in_progress[0] = False
        current_player[0] = 0
        message_box.delete("1.0", "end")
    
        # Create and deal new hands
        global deck
        deck = create_deck()
        shuffle_deck(deck)
        new_hands = deal(deck)
        for i in range(4):
            hands[i] = new_hands[i]
    
        # Draw the hands
        draw_hands()
        turn_label.config(text=f"Turn: Player {current_player[0]}")


    def restart_round():
        log("=== Restarting current round ===")
        
        team_scores["A"] = 0
        team_scores["B"] = 0
        score_label.config(text="Scores - Team A: 0 | Team B: 0")
        
        # Clear played cards in center
        for lbl in played_labels:
            if lbl:
                lbl.destroy()
        for i in range(4):
            played_labels[i] = None
    
        trick_cards.clear()
        trick_in_progress[0] = False
        current_player[0] = 0    
        # Create and deal new hands
        new_hands = deal(deck)
        for i in range(4):
            hands[i] = new_hands[i]
    
        # Draw the hands
        draw_hands()
        turn_label.config(text=f"Turn: Player {current_player[0]}")


    root = tk.Tk()
    root.title("Belote - German Suited Cards")
    root.geometry("1100x800")
    
    def safe_close():
        try:
            root.destroy()  # destroy all widgets
            root.quit()
        except Exception:
            pass  # ignore if already destroyed
    root.protocol("WM_DELETE_WINDOW", safe_close)
    
    # Message box
    message_box = tk.Text(root, height=8, width=50)
    message_box.grid(row=2, column=0, columnspan=3, sticky="ew", pady=5)
    
    def log(msg):
        message_box.insert("end", msg + "\n")
        message_box.see("end")
    
    # --- Frames for hands ---
    top_f    = tk.Frame(root)
    top_f.grid(row=0, column=1, pady=8)
    
    bottom_f = tk.Frame(root)
    bottom_f.grid(row=2, column=1, pady=8)
    
    left_f   = tk.Frame(root)
    left_f.grid(row=1, column=0, padx=8, sticky="ns")
    left_f.grid_propagate(False)
    
    right_f  = tk.Frame(root)
    right_f.grid(row=1, column=2, padx=8, sticky="ns")
    right_f.grid_propagate(False)
    
    # --- Center "table" ---
    center_f = tk.Frame(root, width=500, height=400, relief="groove", borderwidth=3, bg="green")
    center_f.grid(row=1, column=1, sticky="nsew")
    center_f.grid_propagate(False)
    
    # Make the grid expandable
    root.grid_rowconfigure(1, weight=1)
    root.grid_columnconfigure(1, weight=1)
    
    controls_f = tk.Frame(root)
    controls_f.grid(row=3, column=1, pady=10)
    
    new_game_btn = tk.Button(controls_f, text="New Game", command=new_game)
    new_game_btn.grid(row=0, column=0, padx=10)
    
    restart_round_btn = tk.Button(controls_f, text="Restart Round", command=restart_round)
    restart_round_btn.grid(row=0, column=1, padx=10)

    
    # Turn indicator
    turn_label = tk.Label(root, text="Turn: Player 0", font=("Arial", 16))
    turn_label.grid(row=4, column=1, pady=6)
    
    # Score indicator
    score_label = tk.Label(root, text="Scores - Team A: 0 | Team B: 0", font=("Arial", 14))
    score_label.grid(row=5, column=1, pady=6)
    
    # Player played cards shown in center
    played_labels = [None, None, None, None]
    
    # Keep strong references to images
    root.images = []
    card_widgets = [[], [], [], []]
    
    # Current player (0 = bottom, 1 = right, 2 = top, 3 = left)
    current_player = [0]  # use list for mutability inside nested funcs
    
    # Track trick progress
    trick_cards = []
    trick_in_progress = [False]  # mutable flag
    
    # Team scores
    team_scores = {"A": 0, "B": 0}



    def draw_hands():
        """Draw all four players’ hands in their frames"""
        # Clear old hand widgets first
        for i in range(4):
            for w in card_widgets[i]:
                w.destroy()
            card_widgets[i] = []
    
        # ---- Bottom player (0) ----
        for card in hands[0]:
            try:
                im = load_card_image(card, size=(90, 135))
                lbl = tk.Label(bottom_f, image=im); lbl.image = im; root.images.append(im)
                lbl.card_name = card
                lbl.card_rotate = 0
                lbl.pack(side="left", padx=4)
                lbl.bind("<Button-1>", partial(on_card_click, 0, card, lbl))
            except FileNotFoundError:
                lbl = tk.Label(bottom_f, text=card, font=("Arial", 12))
                lbl.pack(side="left", padx=4)
            card_widgets[0].append(lbl)
    
        # ---- Right player (1) ----
        for card in hands[1]:
            try:
                im = load_card_image(card, size=(75, 110), rotate=-90)
                lbl = tk.Label(right_f, image=im); lbl.image = im; root.images.append(im)
                lbl.card_name = card
                lbl.card_rotate = -90
                lbl.pack(side="top", pady=2)
                lbl.bind("<Button-1>", partial(on_card_click, 1, card, lbl))
            except FileNotFoundError:
                lbl = tk.Label(right_f, text=card, font=("Arial", 12))
                lbl.pack(side="top", pady=2)
            card_widgets[1].append(lbl)
    
        # ---- Top player (2) ----
        for card in hands[2]:
            try:
                im = load_card_image(card, size=(90, 135))
                lbl = tk.Label(top_f, image=im); lbl.image = im; root.images.append(im)
                lbl.card_name = card
                lbl.card_rotate = 0
                lbl.pack(side="left", padx=4)
                lbl.bind("<Button-1>", partial(on_card_click, 2, card, lbl))
            except FileNotFoundError:
                lbl = tk.Label(top_f, text=card, font=("Arial", 12))
                lbl.pack(side="left", padx=4)
            card_widgets[2].append(lbl)
    
        # ---- Left player (3) ----
        for card in hands[3]:
            try:
                im = load_card_image(card, size=(75, 110), rotate=90)
                lbl = tk.Label(left_f, image=im); lbl.image = im; root.images.append(im)
                lbl.card_name = card
                lbl.card_rotate = 90
                lbl.pack(side="top", pady=2)
                lbl.bind("<Button-1>", partial(on_card_click, 3, card, lbl))
            except FileNotFoundError:
                lbl = tk.Label(left_f, text=card, font=("Arial", 12))
                lbl.pack(side="top", pady=2)
            card_widgets[3].append(lbl)
    
    
    def get_image_for_card(card, rotate=0):
        # Search all card widgets
        for widgets in card_widgets:
            for w in widgets:
                if getattr(w, "card_name", None) == card and getattr(w, "card_rotate", 0) == rotate:
                    return w.card_image
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
            if player_idx == 1:   # right
                rotate = -90
            elif player_idx == 3: # left
                rotate = 90
            im = get_image_for_card(card, rotate = rotate)
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

    def on_card_click(player_idx, card, widget, event = None):
        
        log(f"Player {player_idx} played {card}")
        
        # Block input while clearing a finished trick
        if trick_in_progress[0]:
            return
    
        # Not this player's turn?
        if player_idx != current_player[0]:
            log(f"Not Player {player_idx}'s turn.")
            return
    
        # Is the move legal?
        allowed = legal_moves(hands[player_idx], trick_cards, TRUMP_SUIT)
        if card not in allowed:
            log(f"Illegal move: {card}. Allowed: {allowed}")
            return
    
        # Find card index in the current hand (fails if card not present)
        try:
            idx = hands[player_idx].index(card)
        except ValueError:
            # Card already played / not found in hand
            log(f"Card {card} not found in Player {player_idx}'s hand (maybe already played).")
            return
    
        # Remove card from the hand data structure
        hands[player_idx].pop(idx)
    
        # Remove the widget from the UI and from card_widgets list
        # Prefer removing by object identity (widget) to be robust
        if widget in card_widgets[player_idx]:
            card_widgets[player_idx].remove(widget)
        try:
            widget.destroy()
        except Exception:
            pass
    
        # Record the play and show it in player's center position
        trick_cards.append((player_idx, card))
        place_played_card(player_idx, card)
    
        # If trick complete, lock and schedule clearing + evaluation
        if len(trick_cards) == 4:
            trick_in_progress[0] = True
            root.after(1500, clear_trick)
    
        # Advance to next player (counterclockwise)
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
        # Determine winner
        if len(trick_cards) == 4:
            lead_suit = trick_cards[0][1][-1]  # suit of first card
            best = trick_cards[0]
            best_val = card_value(best[1], lead_suit, TRUMP_SUIT)
            for play in trick_cards[1:]:
                val = card_value(play[1], lead_suit, TRUMP_SUIT)
                if val > best_val:
                    best = play
                    best_val = val
            winner_idx = best[0]
            log(f"Trick winner: Player {winner_idx}")

            # Calculate trick points
            trick_points = sum(card_points(card, TRUMP_SUIT) for _, card in trick_cards)

            # Last trick += 10 points
            if len(hands[0]) == 0:
                trick_points += 10
            
            # Add points to correct team
            if winner_idx in (0, 2):
                team_scores["A"] += trick_points
            else:
                team_scores["B"] += trick_points
            
            # Update label
            score_label.config(text=f"Scores - Team A: {team_scores['A']} | Team B: {team_scores['B']}")

            # Next trick leader is winner
            current_player[0] = winner_idx
            turn_label.config(text=f"Turn: Player {winner_idx}")

        # Clear visuals
        for lbl in played_labels:
            if lbl is not None:
                lbl.destroy()
        for i in range(4):
            played_labels[i] = None

        trick_cards.clear()
        trick_in_progress[0] = False  # unlock table

    
    draw_hands()
    root.mainloop()






# =====================
# MAIN
# =====================
def main():
    
    # If a Tk root already exists from a previous run, destroy it
    try:
        global root
        root.destroy()
    except NameError:
        pass
    except tk.TclError:
        pass  # root was already destroyed
    global deck
    deck = create_deck()
    shuffle_deck(deck)
    hands = deal(deck)

    # Always show text version
    show_hands_text(hands)

    if os.path.exists(CARD_FOLDER):
        show_hands_images(hands)
    else: print("NOPE")



if __name__ == "__main__":
    main()
