# -*- coding: utf-8 -*-
import random
import os
from functools import partial

# Optional imports for image mode
try:
    import tkinter as tk
    from tkinter import messagebox
    from PIL import Image, ImageTk
    print("Uspjeh")
except ImportError:
    tk = None  # Stay in text mode if Tkinter/Pillow missing
    print("Minus")

from rules import (
    RANKS, SUITS,
    create_deck, shuffle_deck, deal,
    card_value, legal_moves, card_points,
    find_declarations, declaration_to_text,
    compare_declarations, best_declaration_for_player,
    team_of_player, total_declaration_points,
)

# Trump is chosen during bidding
TRUMP_SUIT = None

CARD_FOLDER = "karte"  # Cropped cards will be stored here


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
        img = img.rotate(rotate, expand=True)
    return ImageTk.PhotoImage(img)


def load_misc_image(filename, size=(80, 120), rotate=0):
    """
    Loads non-card PNGs, for example card_back.png or suit_h.png.
    """
    path = os.path.join(CARD_FOLDER, filename)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Missing image: {path}")

    img = Image.open(path).convert("RGBA").resize(size, Image.Resampling.LANCZOS)

    if rotate:
        img = img.rotate(rotate, expand=True)

    return ImageTk.PhotoImage(img)


def show_hands_images(hands):
    if tk is None:
        print("Image mode unavailable: Tkinter/Pillow not installed.")
        return

    root = tk.Tk()
    root.title("Belote - German Suited Cards")
    root.geometry("1200x920")
    root.minsize(1100, 850)

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

    left_f = tk.Frame(root, width=280, height=560)
    left_f.grid(row=1, column=0, padx=8, sticky="ns")
    left_f.grid_propagate(False)

    right_f = tk.Frame(root, width=280, height=560)
    right_f.grid(row=1, column=2, padx=8, sticky="ns")
    right_f.grid_propagate(False)

    # --- Center "table" ---
    center_f = tk.Frame(root, relief="groove", borderwidth=3, bg="green")
    center_f.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")
    
    # --- Trump bidding panel shown in the center table ---
    bidding_f = tk.Frame(center_f, bg="darkgreen", relief="ridge", borderwidth=3)
    bidding_f.place(relx=0.5, rely=0.5, anchor="center")

    bidding_title = tk.Label(
        bidding_f,
        text="Choose trump suit",
        font=("Arial", 14, "bold"),
        fg="white",
        bg="darkgreen"
    )
    bidding_title.grid(row=0, column=0, columnspan=5, pady=(8, 4), padx=10)

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
    
    # Dealer / round order
    # Starting at 3 means the first round behaves like your old code:
    # Player 0 starts, Player 3 is last.
    dealer_player = [3]
    round_first_player = [0]

    def player_after(player_idx):
        return (player_idx + 1) % 4

    def advance_dealer():
        dealer_player[0] = player_after(dealer_player[0])
        round_first_player[0] = player_after(dealer_player[0])

    def bidding_order():
        start = round_first_player[0]
        return [(start + i) % 4 for i in range(4)]

    def order_rank(player_idx):
        """
        Lower number means this player goes earlier in the current round.
        Used for declaration tie-breaking.
        """
        return bidding_order().index(player_idx)
    
    
    
    # =====================
    # TRUMP BIDDING STATE
    # =====================
    bidding_active = [True]
    bidding_player = [0]

    # During bidding, everyone starts by seeing only 6 cards.
    # When a player passes, they are allowed to see all 8.
    revealed_players = set()

    trump_label = tk.Label(root, text="Trump: not chosen", font=("Arial", 16))
    trump_label.grid(row=3, column=0, columnspan=3, pady=(4, 0), sticky="ew")
    
    bidding_label = tk.Label(root, text="Bidding: Player 0 chooses trump or passes", font=("Arial", 13))
    bidding_label.grid(row=4, column=0, columnspan=3, pady=(2, 0), sticky="ew")
    
    dealer_label = tk.Label(root, text="Dealer: Player 3", font=("Arial", 12))
    dealer_label.grid(row=5, column=0, columnspan=3, pady=(2, 4), sticky="ew")
    
    def update_dealer_label():
        dealer_label.config(
            text=(
                f"Dealer: Player {dealer_player[0]} | "
                f"First: Player {round_first_player[0]} | "
                f"Order: {bidding_order()}"
            )
        )

    bsuit_buttons = {}
    pass_button = None

    suit_buttons = {}
    pass_button = None
    
    # Track trick progress
    trick_cards = []
    trick_in_progress = [False]

    # Team scores
    team_scores = {"A": 0, "B": 0}
    
    # Pending declaration points (shown separately, not yet merged into score)
    declaration_bonus = {"A": 0, "B": 0}
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
    turn_label.grid(row=6, column=0, columnspan=3, pady=(2, 0), sticky="ew")

    # Score indicator
    score_label = tk.Label(root, text="Scores - Team A: 0 | Team B: 0", font=("Arial", 14))
    score_label.grid(row=7, column=0, columnspan=3, pady=(2, 0), sticky="ew")
    
    # Declaration indicator
    declaration_label = tk.Label(
    root,
    text="Declarations: none",
    font=("Arial", 12),
    wraplength=900,
    justify="center"
)
    declaration_label.grid(row=8, column=0, columnspan=3, pady=(2, 4), sticky="ew")


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
                    if order_rank(player_idx) < order_rank(team_best_player[team]):
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
                # Completely equal declarations:
                # the player who goes earlier in this round wins.
                if order_rank(team_best_player["A"]) < order_rank(team_best_player["B"]):
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
        

    def visible_count_for_player(player_idx):
        """
        During bidding:
        - players normally see only 6 cards
        - players who passed see all 8
        After bidding:
        - everyone sees all cards
        """
        if is_bot(player_idx):
            return 0
    
        if not bidding_active[0]:
            return 8

        if player_idx in revealed_players:
            return 8

        return 6


    def update_bidding_controls():
        """
        Enables/disables suit and pass buttons depending on bidding state.
        Last player must choose trump, so Pass is disabled for Player 3.
        """
        if not bidding_active[0]:
            bidding_label.config(text="Bidding finished.")

            bidding_f.place_forget()

            for btn in suit_buttons.values():
                btn.config(state="disabled")

            if pass_button is not None:
                pass_button.config(state="disabled")

            return

        bidding_f.place(relx=0.5, rely=0.5, anchor="center")
        bidding_f.lift()

        p = bidding_player[0]
        bidding_label.config(text=f"Bidding: Player {p} chooses trump or passes")
        bidding_title.config(text=f"Player {p}: choose trump suit")

        for btn in suit_buttons.values():
            btn.config(state="normal")

        if pass_button is not None:
            if p == dealer_player[0]:
                pass_button.config(state="disabled", text="Must choose")
            else:
                pass_button.config(state="normal", text="Pass")


    def choose_trump(suit):
        """
        Called when current bidding player chooses trump.
        """
        global TRUMP_SUIT

        TRUMP_SUIT = suit
        bidding_active[0] = False

        # After trump is chosen, everyone sees all cards.
        revealed_players.clear()
        revealed_players.update([0, 1, 2, 3])

        trump_label.config(text=f"Trump: {TRUMP_SUIT}")
        log(f"Player {bidding_player[0]} chose trump: {TRUMP_SUIT}")

        draw_hands()
        update_bidding_controls()

        # Declarations should be checked after trump is chosen.
        apply_declarations()

        current_player[0] = round_first_player[0]
        turn_label.config(text=f"Turn: Player {current_player[0]}")
        
        root.after(500, maybe_bot_play)


    def pass_trump():
        """
        Current bidding player passes.
        They now get to see all 8 cards.
        Next player in bidding order gets the chance to choose.
        The dealer is last and cannot pass.
        """
        order = bidding_order()
        p = bidding_player[0]

        if p == dealer_player[0]:
            log(f"Player {p} is dealer and cannot pass. Dealer must choose trump.")
            return

        log(f"Player {p} passed.")
        revealed_players.add(p)

        current_pos = order.index(p)
        bidding_player[0] = order[current_pos + 1]
        current_player[0] = bidding_player[0]

        draw_hands()
        update_bidding_controls()

        turn_label.config(text=f"Turn: Player {current_player[0]}")
        root.after(500, maybe_bot_bid)


    def start_bidding():
        """
        Starts trump selection.
        Everyone sees only 6 cards at first.
        Bidding starts with the player after the dealer.
        The dealer is last and must choose if everyone else passes.
        """
        global TRUMP_SUIT

        TRUMP_SUIT = None
        bidding_active[0] = True

        bidding_player[0] = round_first_player[0]

        revealed_players.clear()

        trump_label.config(text="Trump: not chosen")
        current_player[0] = bidding_player[0]

        draw_hands()
        update_bidding_controls()
        update_dealer_label()

        turn_label.config(text=f"Turn: Player {current_player[0]}")
        log(
            f"Trump bidding started. Dealer: Player {dealer_player[0]}. "
            f"Bidding order: {bidding_order()}"
        )
        root.after(500, maybe_bot_bid)


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
        advance_dealer()
        new_hands = deal(deck)
        for i in range(4):
            hands[i] = new_hands[i]

        start_bidding()

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

        start_bidding()

    new_game_btn = tk.Button(controls_f, text="New Game", command=new_game)
    new_game_btn.grid(row=0, column=0, padx=10)

    restart_round_btn = tk.Button(controls_f, text="Restart Round", command=restart_round)
    restart_round_btn.grid(row=0, column=1, padx=10)
    
    # Trump suit buttons, displayed in center_f
    for col, suit in enumerate(SUITS):
        try:
            im = load_misc_image(f"boja_{suit}.png", size=(60, 60))
            btn = tk.Button(
                bidding_f,
                image=im,
                command=partial(choose_trump, suit),
                width=70,
                height=70
            )
            btn.image = im
            root.images.append(im)
        except FileNotFoundError:
            btn = tk.Button(
                bidding_f,
                text=suit,
                font=("Arial", 16, "bold"),
                width=5,
                height=2,
                command=partial(choose_trump, suit)
            )

        btn.grid(row=1, column=col, padx=5, pady=6)
        suit_buttons[suit] = btn

    pass_button = tk.Button(
        bidding_f,
        text="Pass",
        font=("Arial", 13),
        width=10,
        command=pass_trump
    )
    pass_button.grid(row=2, column=0, columnspan=4, pady=(4, 10))

    def draw_hands():
        """Draw all four players' hands in a 2x4 layout"""
        for i in range(4):
            for w in card_widgets[i]:
                w.destroy()
            card_widgets[i] = []

        try:
            left_f.config(width=280, height=560)
            right_f.config(width=280, height=560)
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
            lbl.grid(row=row, column=col, padx=1, pady=0)
        
        def draw_bot_placeholder(frame, player_idx):
            lbl = tk.Label(
                frame,
                text=f"Bot Player {player_idx}\n{len(hands[player_idx])} cards",
                font=("Arial", 14, "bold"),
                justify="center"
            )
        
            lbl.place(relx=0.5, rely=0.5, anchor="center")
            card_widgets[player_idx].append(lbl)
        
        # Bottom player (0)
        if is_bot(0):
            draw_bot_placeholder(bottom_f, 0)
        else:
            visible_count = visible_count_for_player(0)
            
            for i, card in enumerate(hands[0]):
                shown_card = card if i < visible_count else None
            
                try:
                    if shown_card is None:
                        im = load_misc_image("prazna_karta.png", size=(80, 120))
                        lbl = tk.Label(bottom_f, image=im, bd=0)
                        lbl.image = im
                        root.images.append(im)
                    else:
                        im = load_card_image(card, size=(80, 120))
                        lbl = tk.Label(bottom_f, image=im, bd=0)
                        lbl.image = im
                        lbl.card_image = im
                        root.images.append(im)
                        lbl.card_name = card
                        lbl.card_rotate = 0
                        lbl.bind("<Button-1>", partial(on_card_click, 0, card, lbl))
            
                except FileNotFoundError:
                    text = card if shown_card is not None else "BACK"
                    lbl = tk.Label(bottom_f, text=text, font=("Arial", 10))
            
                place_horizontal_2x4(lbl, i)
                card_widgets[0].append(lbl)
        
        # Right player (1)
        if is_bot(1):
            draw_bot_placeholder(right_f, 1)
        else:
            visible_count = visible_count_for_player(1)
            
            for i, card in enumerate(hands[1]):
                shown_card = card if i < visible_count else None
            
                try:
                    if shown_card is None:
                        im = load_misc_image("prazna_karta.png", size=(72, 108), rotate=-90)
                        lbl = tk.Label(right_f, image=im, bd=0)
                        lbl.image = im
                        root.images.append(im)
                    else:
                        im = load_card_image(card, size=(72, 108), rotate=-90)
                        lbl = tk.Label(right_f, image=im, bd=0)
                        lbl.image = im
                        lbl.card_image = im
                        root.images.append(im)
                        lbl.card_name = card
                        lbl.card_rotate = -90
                        lbl.bind("<Button-1>", partial(on_card_click, 1, card, lbl))
            
                except FileNotFoundError:
                    text = card if shown_card is not None else "BACK"
                    lbl = tk.Label(right_f, text=text, font=("Arial", 9))
            
                place_vertical_2x4(lbl, i)
                card_widgets[1].append(lbl)
        
        # Top player (2)
        if is_bot(2):
            draw_bot_placeholder(top_f, 2)
        else:
            visible_count = visible_count_for_player(2)
    
            for i, card in enumerate(hands[2]):
                shown_card = card if i < visible_count else None
    
                try:
                    if shown_card is None:
                        im = load_misc_image("prazna_karta.png", size=(80, 120))
                        lbl = tk.Label(top_f, image=im, bd=0)
                        lbl.image = im
                        root.images.append(im)
                    else:
                        im = load_card_image(card, size=(80, 120))
                        lbl = tk.Label(top_f, image=im, bd=0)
                        lbl.image = im
                        lbl.card_image = im
                        root.images.append(im)
                        lbl.card_name = card
                        lbl.card_rotate = 0
                        lbl.bind("<Button-1>", partial(on_card_click, 2, card, lbl))
    
                except FileNotFoundError:
                    text = card if shown_card is not None else "BACK"
                    lbl = tk.Label(top_f, text=text, font=("Arial", 10))
    
                place_horizontal_2x4(lbl, i)
                card_widgets[2].append(lbl)

        # Left player (3)
        if is_bot(3):
            draw_bot_placeholder(left_f, 3)
        else:
            visible_count = visible_count_for_player(3)
    
            for i, card in enumerate(hands[3]):
                shown_card = card if i < visible_count else None
    
                try:
                    if shown_card is None:
                        im = load_misc_image("prazna_karta.png", size=(72, 108), rotate=90)
                        lbl = tk.Label(left_f, image=im, bd=0)
                        lbl.image = im
                        root.images.append(im)
                    else:
                        im = load_card_image(card, size=(72, 108), rotate=90)
                        lbl = tk.Label(left_f, image=im, bd=0)
                        lbl.image = im
                        lbl.card_image = im
                        root.images.append(im)
                        lbl.card_name = card
                        lbl.card_rotate = 90
                        lbl.bind("<Button-1>", partial(on_card_click, 3, card, lbl))
    
                except FileNotFoundError:
                    text = card if shown_card is not None else "BACK"
                    lbl = tk.Label(left_f, text=text, font=("Arial", 9))
    
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
    
    def maybe_ask_bela(player_idx, card):
        if TRUMP_SUIT is None:
            return

        rank, suit = card[:-1], card[-1]

        # Bela je samo K + D u adutu
        if suit != TRUMP_SUIT or rank not in ("K", "D"):
            return

        # Važno: ova funkcija se poziva PRIJE micanja karte iz ruke.
        # Zato pri prvoj od dvije karte igrač još ima obje.
        if f"K{TRUMP_SUIT}" not in hands[player_idx]:
            return
        if f"D{TRUMP_SUIT}" not in hands[player_idx]:
            return

        wants_bela = messagebox.askyesno(
            "Bela",
            f"Player {player_idx} ima kralja i damu u adutu.\nŽeli li zvati belu?"
        )

        if wants_bela:
            team = team_of_player(player_idx)
            declaration_bonus[team] += 20
            log(f"Player {player_idx} called bela. Team {team} gets +20 pending.")
            update_score_label()
        else:
            log(f"Player {player_idx} did not call bela.")
    
    def play_card(player_idx, card, widget=None):
        if bidding_active[0]:
            log("You cannot play cards until trump is chosen.")
            return
    
        if TRUMP_SUIT is None:
            log("Trump suit has not been chosen yet.")
            return
    
        if trick_in_progress[0]:
            return
    
        if player_idx != current_player[0]:
            log(f"Not Player {player_idx}'s turn.")
            return
    
        allowed = legal_moves(hands[player_idx], trick_cards, TRUMP_SUIT)
        if card not in allowed:
            log(f"Illegal move: {card}. Allowed: {allowed}")
            return
    
        # Ako si već dodao belu, ovo ide ovdje, PRIJE micanja karte iz ruke
        # maybe_ask_bela(player_idx, card)
    
        try:
            idx = hands[player_idx].index(card)
        except ValueError:
            log(f"Card {card} not found in Player {player_idx}'s hand (maybe already played).")
            return
    
        hands[player_idx].pop(idx)
    
        if widget is not None:
            if widget in card_widgets[player_idx]:
                card_widgets[player_idx].remove(widget)
            try:
                widget.destroy()
            except Exception:
                pass
    
        trick_cards.append((player_idx, card))
        place_played_card(player_idx, card)
    
        log(f"Player {player_idx} played {card}")
    
        if len(trick_cards) == 4:
            trick_in_progress[0] = True
            root.after(1500, clear_trick)
        else:
            current_player[0] = (current_player[0] + 1) % 4
            turn_label.config(text=f"Turn: Player {current_player[0]}")
            root.after(500, maybe_bot_play)
    
        draw_hands()
    
    def on_card_click(player_idx, card, widget, event=None):
        play_card(player_idx, card, widget)
    
    def start_next_round():
        """
        Starts a fresh round after all cards have been played.
        Dealer shifts, new cards are dealt, bidding starts again.
        Scores stay.
        """
        log("=== Starting next round ===")

        for lbl in played_labels:
            if lbl:
                lbl.destroy()

        for i in range(4):
            played_labels[i] = None

        trick_cards.clear()
        trick_in_progress[0] = False

        declaration_bonus["A"] = 0
        declaration_bonus["B"] = 0
        winning_declarations_text[0] = "Declarations: none"
        update_declaration_label()
        update_score_label()

        global deck
        deck = create_deck()
        shuffle_deck(deck)

        advance_dealer()

        new_hands = deal(deck)
        for i in range(4):
            hands[i] = new_hands[i]

        start_bidding()
    
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

            round_is_over = all(len(hand) == 0 for hand in hands)

            if round_is_over:
                trick_points += 10

            if winner_idx in (0, 2):
                team_scores["A"] += trick_points
            else:
                team_scores["B"] += trick_points

            update_score_label()

            if round_is_over:
                log("Round finished.")

                # Start next round automatically after a short delay.
                root.after(2000, start_next_round)
                return

            current_player[0] = winner_idx
            turn_label.config(text=f"Turn: Player {winner_idx}")
            root.after(500, maybe_bot_play)

        for lbl in played_labels:
            if lbl is not None:
                lbl.destroy()
        for i in range(4):
            played_labels[i] = None

        trick_cards.clear()
        trick_in_progress[0] = False
    
    
    
    # =====================
    # BOT HELPERS
    # =====================
    from bots import RandomBot
    
    players = [
    "human",
    RandomBot(),
    RandomBot(),
    RandomBot(),
]

    def is_bot(player_idx):
        return players[player_idx] != "human"
    
    def is_human(player_idx):
        return players[player_idx] == "human"
    
    def get_state_for_bot(player_idx):
        return {
            "my_hand": hands[player_idx].copy(),
            "trump_suit": TRUMP_SUIT,
            "current_player": current_player[0],
            "trick_cards": trick_cards.copy(),
            "team_scores": team_scores.copy(),
            "declaration_bonus": declaration_bonus.copy(),
            "dealer_player": dealer_player[0],
            "round_first_player": round_first_player[0],
            "bidding_active": bidding_active[0],
            "bidding_player": bidding_player[0],
        }
    
    
    def maybe_bot_play():
        if bidding_active[0]:
            return
    
        p = current_player[0]
    
        if not is_bot(p):
            return
    
        allowed = legal_moves(hands[p], trick_cards, TRUMP_SUIT)
        bot = players[p]
        state = get_state_for_bot(p)
        card = bot.choose_card(state, p, allowed)
    
        if card not in allowed:
            log(f"Bot Player {p} chose illegal card: {card}. Allowed: {allowed}")
            return
    
        root.after(500, lambda p=p, card=card: play_card(p, card))
    
    
    def maybe_bot_bid():
        if not bidding_active[0]:
            return
    
        p = bidding_player[0]
    
        if not is_bot(p):
            return
    
        bot = players[p]
        state = get_state_for_bot(p)
        choice = bot.choose_trump(state, p)
    
        if p == dealer_player[0] and choice == "pass":
            choice = random.choice(SUITS)
    
        if choice == "pass":
            root.after(500, pass_trump)
        elif choice in SUITS:
            root.after(500, lambda: choose_trump(choice))
        else:
            log(f"Bot Player {p} made invalid trump choice: {choice}")
    
    
    start_bidding()
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