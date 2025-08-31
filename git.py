#!/usr/bin/env python3
"""
Ultimate Console Arcade Hub
Includes:
 - Guess the Number (leaderboard by attempts, tiebreak by time)
 - Reaction Game (modes of rounds; leaderboard by total reaction time)
 - Gibberish Typing (modes by word count; only 100% accuracy saved; leaderboard by time)
 - Number Memory (modes, leaderboard by longest length then time)
 - Sequence Tap (modes by steps; leaderboard by total time)
 - Word Memory Chain (modes by number of words; leaderboard by correct count then time)
 - Math Speed Run (modes by number of problems; leaderboard by total time)
 - Achievements stored per player
 - All leaderboards top 100, persistent in highscores.json
"""
import random, time, json, os, sys

# Optional color output
try:
    from colorama import init, Fore, Style
    init(autoreset=True)
except Exception:
    class _C:
        def __getattr__(self, _): return ""
    Fore = Style = _C()

HIGHSCORE_FILE = "highscores.json"
TOP_N = 100

# ---------- JSON structure ----------
# {
#   "leaderboards": {
#       "guess_the_number": { mode_key: [entries...] },
#       "reaction_game": { rounds_str: [entries...] },
#       "gibberish_typing": { words_str: [entries...] },
#       "number_memory": { mode_key: [...] },
#       "sequence_tap": { mode_key: [...] },
#       "word_memory": { mode_key: [...] },
#       "math_speed": { mode_key: [...] }
#   },
#   "players": {
#       "Alice": { "achievements": [...], "games_played": n }
#   }
# }
BASE_SAVE = {
    "leaderboards": {
        "guess_the_number": {},
        "reaction_game": {},
        "gibberish_typing": {},
        "number_memory": {},
        "sequence_tap": {},
        "word_memory": {},
        "math_speed": {}
    },
    "players": {}
}

def read_save():
    if not os.path.exists(HIGHSCORE_FILE):
        write_save(BASE_SAVE)
        return json.loads(json.dumps(BASE_SAVE))
    try:
        with open(HIGHSCORE_FILE, "r") as f:
            data = json.load(f)
    except Exception:
        data = json.loads(json.dumps(BASE_SAVE))
    # ensure keys
    data.setdefault("leaderboards", {})
    for key in BASE_SAVE["leaderboards"]:
        data["leaderboards"].setdefault(key, {})
    data.setdefault("players", {})
    return data

def write_save(data):
    with open(HIGHSCORE_FILE, "w") as f:
        json.dump(data, f, indent=2)

# ---------- Utilities ----------
def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def pause():
    input(Fore.CYAN + "\nPress Enter to continue...")

def now_ts():
    return int(time.time())

def ensure_player(data, name):
    data.setdefault("players", {})
    if name not in data["players"]:
        data["players"][name] = {"achievements": [], "games_played": 0}

def award_achievement(data, player, ach_key, ach_name):
    ensure_player(data, player)
    player_data = data["players"][player]
    if ach_key not in player_data["achievements"]:
        player_data["achievements"].append(ach_key)
        print(Fore.YELLOW + f"🏆 Achievement unlocked: {ach_name}!")
        write_save(data)

def add_leaderboard_entry(data, game_key, mode_key, entry, sort_fn, top_n=TOP_N):
    lbs = data["leaderboards"].setdefault(game_key, {})
    lb = lbs.setdefault(str(mode_key), [])
    lb.append(entry)
    lb.sort(key=sort_fn)
    lbs[str(mode_key)] = lb[:top_n]
    data["leaderboards"][game_key] = lbs
    write_save(data)

def show_leaderboard_generic(data, game_key, mode_key, fmt_fn, title):
    lbs = data["leaderboards"].get(game_key, {})
    lb = lbs.get(str(mode_key), [])
    print(Fore.YELLOW + f"\n🏆 {title} — mode {mode_key} (Top {TOP_N})")
    if not lb:
        print("No scores yet!")
        return
    for i, e in enumerate(lb, 1):
        print(fmt_fn(i, e))

# ---------- Achievements catalog ----------
ACH_LIST = {
    # Guess the Number
    "gtn_first_try": "Lucky First Guess (1 attempt)",
    "gtn_speed_demon": "Speed Demon (<5s)",
    "gtn_sniper": "Sniper (<3 attempts)",
    "gtn_persistent": "Persistent (20+ attempts)",
    "gtn_iron_streak_5": "Iron Streak — 5 wins in a row",
    "gtn_nightmare": "Impossible Odds — Beat Nightmare range",
    # Reaction
    "rx_lightning": "Lightning Reflexes (<0.200s single)",
    "rx_consistent": "Consistent Pro (all <0.500s)",
    "rx_marathon": "Marathon Reflexes (complete 25 rounds)",
    # Gibberish
    "gt_perfect_accuracy": "Perfect Accuracy (100%)",
    "gt_typing_machine": "Typing Machine (<1s/word avg)",
    "gt_flawless_streak3": "Flawless Streak — 3 perfects in a row",
    # Number Memory
    "nm_brain_of_steel": "Brain of Steel (10-digit recall)",
    "nm_flash_recall": "Flash Recall (5 in a row)",
    # Sequence Tap
    "st_pattern_pro": "Pattern Pro (complete 20-step)",
    # Word Memory
    "wm_word_wizard": "Word Wizard (15 words)",
    # Math Speed
    "ms_lightning_calc": "Lightning Calculator (20 in <30s)",
    "ms_math_genius": "Math Genius (perfect on 50)",
    # Cross-game
    "cg_triple_threat": "Triple Threat (play all 3 different games in session)",
    "cg_grinder_50": "Grinder (50 total games)",
    "cg_century_100": "Century Club (100 total games)",
    "cg_top10": "Top 10 Glory",
    "cg_champion": "Champion (#1 on any leaderboard)",
    "cg_collector_10": "Collector (10 achievements)",
    "cg_collector_20": "Master Collector (20 achievements)"
}

# ---------- Player session (for tracking session achievements) ----------
class SessionTracker:
    def __init__(self, player):
        self.player = player
        self.games_this_session = set()
        self.consecutive_gtn_wins = 0
        self.perfect_gibberish_streak = 0
        self.total_games_played = 0

# ---------- Guess the Number (unchanged logic but different ranking) ----------
def get_guess_difficulty():
    print(Fore.CYAN + """
Choose Difficulty:
1. Very Easy (1–20)
2. Easy      (1–50)
3. Normal    (1–100)
4. Hard      (1–250)
5. Very Hard (1–500)
6. Extreme   (1–1000)
7. Nightmare (1–5000)
8. Custom Range
""")
    while True:
        ch = input("Enter difficulty level (1–8): ").strip()
        if ch in [str(i) for i in range(1,8)]:
            ranges = {'1':(1,20),'2':(1,50),'3':(1,100),'4':(1,250),'5':(1,500),'6':(1,1000),'7':(1,5000)}
            return ch, ranges[ch]
        elif ch == '8':
            try:
                low = int(input("Min (>=1): "))
                high = int(input("Max (>min): "))
                if low >= 1 and high > low:
                    return f"custom_{low}_{high}", (low, high)
            except:
                print(Fore.RED + "Invalid numbers.")
        else:
            print(Fore.RED + "Invalid choice.")

def play_guess_the_number(data, session):
    clear_screen()
    print(Fore.GREEN + "🎯 Guess the Number")
    player = input("Enter your name: ").strip() or "Player"
    ensure_player(data, player)
    session.player = player

    mode_key, (min_n, max_n) = get_guess_difficulty()
    target = random.randint(min_n, max_n)
    attempts = 0
    start = time.time()
    while True:
        try:
            g = int(input("Your guess: "))
            attempts += 1
            if g < min_n or g > max_n:
                print(Fore.RED + f"Guess inside {min_n}-{max_n}.")
            elif g < target:
                print(Fore.BLUE + "Too low.")
            elif g > target:
                print(Fore.BLUE + "Too high.")
            else:
                break
        except ValueError:
            print(Fore.RED + "Enter integer.")
    elapsed = time.time() - start
    print(Fore.MAGENTA + f"Solved in {attempts} attempts, {elapsed:.2f}s")
    # Achievements
    if attempts == 1:
        award_achievement(data, player, "gtn_first_try", ACH_LIST["gtn_first_try"])
    if elapsed < 5:
        award_achievement(data, player, "gtn_speed_demon", ACH_LIST["gtn_speed_demon"])
    if attempts < 3:
        award_achievement(data, player, "gtn_sniper", ACH_LIST["gtn_sniper"])
    if attempts >= 20:
        award_achievement(data, player, "gtn_persistent", ACH_LIST["gtn_persistent"])
    if mode_key == '7':  # nightmare
        award_achievement(data, player, "gtn_nightmare", ACH_LIST["gtn_nightmare"])

    # Track streaks
    session.games_this_session.add("guess")
    session.total_games_played += 1
    session.consecutive_gtn_wins += 1
    if session.consecutive_gtn_wins >= 5:
        award_achievement(data, player, "gtn_iron_streak_5", ACH_LIST["gtn_iron_streak_5"])

    # Save leaderboard entry (ranking by attempts ASC then time ASC)
    entry = {"name": player, "attempts": attempts, "time": float(elapsed), "ts": now_ts()}
    add_leaderboard_entry(data, "guess_the_number", mode_key, entry,
                          sort_fn=lambda r: (r["attempts"], r["time"]))
    show_guess_leaderboard(data, mode_key)
    pause()

def show_guess_leaderboard(data, mode_key):
    def fmt(i, e):
        return f"{i}. {e['name']} — {e['attempts']} attempts, {e['time']:.2f}s"
    show_leaderboard_generic(data, "guess_the_number", mode_key, fmt, "Guess the Number")

# ---------- Reaction Game ----------
REACTION_MODES = [2,3,5,7,10,15,25]

def play_reaction(data, session):
    clear_screen()
    print(Fore.GREEN + "⚡ Reaction Game")
    player = input("Enter your name: ").strip() or "Player"
    ensure_player(data, player)
    session.player = player

    print("Choose rounds:")
    for i,m in enumerate(REACTION_MODES, 1):
        print(f"{i}. {m}")
    rounds = None
    while rounds is None:
        ch = input("Choice: ").strip()
        if ch.isdigit() and 1 <= int(ch) <= len(REACTION_MODES):
            rounds = REACTION_MODES[int(ch)-1]
        else:
            print(Fore.RED + "Invalid.")

    print(Fore.CYAN + "Instructions: press Enter to arm, wait for NOW!, then press Enter again as fast as you can.")
    total = 0.0
    per_round = []
    any_below_200 = False
    all_below_500 = True

    for r in range(1, rounds+1):
        input(f"[Round {r}/{rounds}] Press Enter to arm...")
        wait = random.uniform(1.0, 3.0)
        print("(waiting...)")
        time.sleep(wait)
        print(Fore.GREEN + "NOW!")
        t0 = time.time()
        input()
        dt = time.time() - t0
        per_round.append(dt)
        total += dt
        print(Fore.MAGENTA + f"Reaction: {dt:.3f}s")
        if dt < 0.2: any_below_200 = True
        if dt >= 0.5: all_below_500 = False

    print(Fore.CYAN + f"\nTotal: {total:.3f}s")
    if any_below_200:
        award_achievement(data, player, "rx_lightning", ACH_LIST["rx_lightning"])
    if all_below_500:
        award_achievement(data, player, "rx_consistent", ACH_LIST["rx_consistent"])
    if rounds == 25:
        award_achievement(data, player, "rx_marathon", ACH_LIST["rx_marathon"])

    session.games_this_session.add("reaction")
    session.total_games_played += 1

    # Save leaderboard entry (total_time ASC)
    entry = {"name": player, "total_time": float(total), "per_round": per_round, "ts": now_ts()}
    add_leaderboard_entry(data, "reaction_game", str(rounds), entry, sort_fn=lambda r: r["total_time"])
    show_reaction_leaderboard(data, rounds)
    pause()

def show_reaction_leaderboard(data, rounds):
    def fmt(i, e):
        return f"{i}. {e['name']} — {e['total_time']:.3f}s"
    show_leaderboard_generic(data, "reaction_game", rounds, fmt, "Reaction Game")

# ---------- Gibberish Typing ----------
GIB_MODES = [5,10,15,20,25,30,35,40]
_GIB_SYLS = ["za","qi","xo","vu","ka","ty","ble","gro","spl","cru","dra","zle","mip","nop","quix","zog","flek","vrax","snoo","yib","glum","pry","thra","kly","wex","zor","plim","snar","vex","krax","flib","mox"]

def make_gib_word():
    chunks = random.randint(2,4)
    word = "".join(random.choice(_GIB_SYLS) for _ in range(chunks))
    if random.random() < 0.1:
        word += random.choice(["'", "-", ""])
    return word

def play_gibberish(data, session):
    clear_screen()
    print(Fore.GREEN + "⌨️  Gibberish Typing")
    player = input("Enter your name: ").strip() or "Player"
    ensure_player(data, player)
    session.player = player

    print("Choose word count:")
    for i,m in enumerate(GIB_MODES,1):
        print(f"{i}. {m}")
    words = None
    while words is None:
        ch = input("Choice: ").strip()
        if ch.isdigit() and 1 <= int(ch) <= len(GIB_MODES):
            words = GIB_MODES[int(ch)-1]
        else:
            print(Fore.RED + "Invalid.")
    targets = [make_gib_word() for _ in range(words)]
    print(Fore.CYAN + "\nType the following EXACTLY (100% accuracy required):\n")
    print(" ".join(targets))
    start = time.time()
    typed = input("\nYour input:\n> ").strip()
    elapsed = time.time() - start
    typed_tokens = typed.split()
    perfect = (typed_tokens == targets)
    session.games_this_session.add("gibberish")
    session.total_games_played += 1
    if perfect:
        print(Fore.GREEN + f"100% accuracy! Time: {elapsed:.3f}s")
        award_achievement(data, player, "gt_perfect_accuracy", ACH_LIST["gt_perfect_accuracy"])
        avg = elapsed / max(1, words)
        if avg < 1.0:
            award_achievement(data, player, "gt_typing_machine", ACH_LIST["gt_typing_machine"])
        # track flawless streak
        p = data["players"][player]
        # We'll manage streak in session for consecutive perfects:
        session.perfect_gibberish_streak = getattr(session, "perfect_gibberish_streak", 0) + 1
        if session.perfect_gibberish_streak >= 3:
            award_achievement(data, player, "gt_flawless_streak3", ACH_LIST["gt_flawless_streak3"])
        # Save leaderboard
        entry = {"name": player, "total_time": float(elapsed), "words": words, "ts": now_ts()}
        add_leaderboard_entry(data, "gibberish_typing", str(words), entry, sort_fn=lambda r: r["total_time"])
        show_gibberish_leaderboard(data, words)
    else:
        print(Fore.RED + f"Not 100% accurate. Time: {elapsed:.3f}s (not saved)")
        # reset streak
        session.perfect_gibberish_streak = 0
        # optional hint:
        min_len = min(len(typed_tokens), len(targets))
        mismatch = None
        for i in range(min_len):
            if typed_tokens[i] != targets[i]:
                mismatch = i+1
                break
        if mismatch is None and len(typed_tokens) != len(targets):
            mismatch = min_len+1
        if mismatch:
            print(Fore.YELLOW + f"Hint: mismatch around word #{mismatch}")
    pause()

def show_gibberish_leaderboard(data, words):
    def fmt(i,e):
        return f"{i}. {e['name']} — {e['total_time']:.3f}s"
    show_leaderboard_generic(data, "gibberish_typing", str(words), fmt, "Gibberish Typing")

# ---------- Number Memory ----------
# Modes: Easy (start 2 digits), Normal (start 4), Hard (start 6)
NM_MODES = {"1":"easy_2","2":"normal_4","3":"hard_6"}

def play_number_memory(data, session):
    clear_screen()
    print(Fore.GREEN + "🔢 Number Memory")
    player = input("Enter your name: ").strip() or "Player"
    ensure_player(data, player)
    session.player = player

    print("Select mode:")
    print("1) Easy (start 2 digits)")
    print("2) Normal (start 4 digits)")
    print("3) Hard (start 6 digits)")
    mode_choice = None
    while mode_choice is None:
        ch = input("Choice: ").strip()
        if ch in NM_MODES:
            mode_choice = NM_MODES[ch]
        else:
            print(Fore.RED + "Invalid.")
    # starting length
    start_len = 2 if mode_choice=="easy_2" else 4 if mode_choice=="normal_4" else 6
    max_len = start_len
    total_time = 0.0
    round_no = 0
    print(Fore.CYAN + "You will see a number briefly, then retype it. Round continues until you fail.")
    while True:
        round_no += 1
        n = "".join(str(random.randint(0,9)) for _ in range(max_len))
        print(Fore.WHITE + f"\nMemorize: {n}")
        time.sleep(1.5 + 0.4 * max_len)  # display depends on length
        clear_screen()
        t0 = time.time()
        ans = input(f"Enter the {max_len}-digit number: ").strip()
        dt = time.time() - t0
        total_time += dt
        if ans == n:
            print(Fore.GREEN + f"Correct! (+{dt:.3f}s)")
            # increase for next round
            max_len += 1
            # achievements checks
            if max_len-1 >= 10:
                award_achievement(data, player, "nm_brain_of_steel", ACH_LIST["nm_brain_of_steel"])
            if round_no >= 5:
                award_achievement(data, player, "nm_flash_recall", ACH_LIST["nm_flash_recall"])
            session.total_games_played += 1
            continue
        else:
            print(Fore.RED + f"Wrong. The number was {n}. You reached length {max_len}.")
            # scoreboard: longest length achieved = max_len - 1 (because failed at current attempt)
            achieved = max_len - 1
            entry = {"name": player, "max_length": achieved, "total_time": float(total_time), "ts": now_ts()}
            add_leaderboard_entry(data, "number_memory", mode_choice, entry,
                                  sort_fn=lambda r: (-r["max_length"], r["total_time"]))
            show_number_memory_leaderboard(data, mode_choice)
            pause()
            break

def show_number_memory_leaderboard(data, mode_key):
    def fmt(i, e):
        return f"{i}. {e['name']} — length {e['max_length']}, time {e['total_time']:.3f}s"
    show_leaderboard_generic(data, "number_memory", mode_key, fmt, "Number Memory")

# ---------- Sequence Tap ----------
SEQ_MODES = [5,10,15,20]

def play_sequence_tap(data, session):
    clear_screen()
    print(Fore.GREEN + "🔁 Sequence Tap")
    player = input("Enter your name: ").strip() or "Player"
    ensure_player(data, player)
    session.player = player

    print("Choose steps:")
    for i,m in enumerate(SEQ_MODES,1):
        print(f"{i}. {m}")
    steps = None
    while steps is None:
        ch = input("Choice: ").strip()
        if ch.isdigit() and 1 <= int(ch) <= len(SEQ_MODES):
            steps = SEQ_MODES[int(ch)-1]
        else:
            print(Fore.RED + "Invalid.")

    # sequence chars: uppercase letters and digits
    pool = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    seq = [random.choice(pool) for _ in range(steps)]

    print(Fore.CYAN + "\nWatch the sequence (pauses between items):")
    for s in seq:
        print(Fore.WHITE + s)
        time.sleep(0.8)
        clear_screen()
        time.sleep(0.2)
    print("Now type the sequence with no spaces, e.g., ABC12")
    t0 = time.time()
    typed = input("Your input: ").strip().upper()
    elapsed = time.time() - t0
    expected = "".join(seq)
    correct = typed == expected
    if correct:
        print(Fore.GREEN + f"Correct! Time: {elapsed:.3f}s")
        award_achievement(data, player, "st_pattern_pro", ACH_LIST["st_pattern_pro"]) if steps == 20 else None
        entry = {"name": player, "total_time": float(elapsed), "ts": now_ts()}
        add_leaderboard_entry(data, "sequence_tap", str(steps), entry, sort_fn=lambda r: r["total_time"])
        show_sequence_leaderboard(data, steps)
    else:
        print(Fore.RED + f"Wrong. Expected: {expected}")
    session.total_games_played += 1
    pause()

def show_sequence_leaderboard(data, steps):
    def fmt(i,e):
        return f"{i}. {e['name']} — {e['total_time']:.3f}s"
    show_leaderboard_generic(data, "sequence_tap", str(steps), fmt, "Sequence Tap")

# ---------- Word Memory Chain ----------
# use a modest wordlist for random selection
_WORD_LIST = [
    "apple","river","mount","stone","bridge","silver","pillow","planet","rocket","banana",
    "computer","train","window","garden","shadow","market","mirror","coffee","library","ocean",
    "forest","bottle","candle","button","island","castle","paper","guitar","circle","planet"
]

WM_MODES = [5,10,15]

def play_word_memory(data, session):
    clear_screen()
    print(Fore.GREEN + "📚 Word Memory Chain")
    player = input("Enter your name: ").strip() or "Player"
    ensure_player(data, player)
    session.player = player

    print("Choose mode:")
    for i,m in enumerate(WM_MODES,1):
        print(f"{i}. {m}")
    words_count = None
    while words_count is None:
        ch = input("Choice: ").strip()
        if ch.isdigit() and 1 <= int(ch) <= len(WM_MODES):
            words_count = WM_MODES[int(ch)-1]
        else:
            print(Fore.RED + "Invalid.")

    words = random.sample(_WORD_LIST, words_count)
    print(Fore.CYAN + "Memorize the words in order:")
    print(" ".join(words))
    time.sleep(2 + words_count*0.6)
    clear_screen()
    print("Now type them in order separated by spaces.")
    t0 = time.time()
    typed = input("> ").strip().lower().split()
    elapsed = time.time() - t0
    correct_count = sum(1 for a,b in zip(words, typed) if a==b)
    print(Fore.MAGENTA + f"You recalled {correct_count}/{words_count} words in {elapsed:.3f}s")
    session.total_games_played += 1
    # achievements
    if correct_count == words_count and words_count >= 15:
        award_achievement(data, player, "wm_word_wizard", ACH_LIST["wm_word_wizard"])
    # leaderboard: rank by correct_count DESC, time ASC
    entry = {"name": player, "correct": correct_count, "total_time": float(elapsed), "ts": now_ts()}
    add_leaderboard_entry(data, "word_memory", str(words_count), entry,
                          sort_fn=lambda r: (-r["correct"], r["total_time"]))
    show_word_memory_leaderboard(data, words_count)
    pause()

def show_word_memory_leaderboard(data, words_count):
    def fmt(i,e):
        return f"{i}. {e['name']} — {e['correct']}/{words_count} correct, {e['total_time']:.3f}s"
    show_leaderboard_generic(data, "word_memory", str(words_count), fmt, "Word Memory Chain")

# ---------- Math Speed Run ----------
MATH_MODES = [10,20,30,50]

def play_math_speed(data, session):
    clear_screen()
    print(Fore.GREEN + "🧮 Math Speed Run")
    player = input("Enter your name: ").strip() or "Player"
    ensure_player(data, player)
    session.player = player

    print("Choose problems:")
    for i,m in enumerate(MATH_MODES,1):
        print(f"{i}. {m}")
    problems = None
    while problems is None:
        ch = input("Choice: ").strip()
        if ch.isdigit() and 1 <= int(ch) <= len(MATH_MODES):
            problems = MATH_MODES[int(ch)-1]
        else:
            print(Fore.RED + "Invalid.")

    print(Fore.CYAN + f"Solve {problems} problems. You must answer correctly; retry allowed (time continues).")
    start = time.time()
    for i in range(1, problems+1):
        a = random.randint(1, 12)
        b = random.randint(1, 12)
        op = random.choice(['+','-','*'])
        ans = a + b if op=='+' else a - b if op=='-' else a * b
        while True:
            try:
                resp = int(input(f"Q{i}: {a}{op}{b} = "))
                if resp == ans:
                    break
                else:
                    print(Fore.RED + "Wrong, try again.")
            except ValueError:
                print(Fore.RED + "Enter integer.")
    elapsed = time.time() - start
    print(Fore.MAGENTA + f"Completed {problems} problems in {elapsed:.3f}s")
    # achievements
    if problems >= 20 and elapsed < 30:
        award_achievement(data, player, "ms_lightning_calc", ACH_LIST["ms_lightning_calc"])
    if problems == 50:
        # perfect score achieved by finishing all with correct answers (we forced correctness)
        award_achievement(data, player, "ms_math_genius", ACH_LIST["ms_math_genius"])
    session.total_games_played += 1
    # leaderboard by elapsed time ASC
    entry = {"name": player, "total_time": float(elapsed), "problems": problems, "ts": now_ts()}
    add_leaderboard_entry(data, "math_speed", str(problems), entry, sort_fn=lambda r: r["total_time"])
    show_math_speed_leaderboard(data, problems)
    pause()

def show_math_speed_leaderboard(data, problems):
    def fmt(i,e):
        return f"{i}. {e['name']} — {e['total_time']:.3f}s"
    show_leaderboard_generic(data, "math_speed", str(problems), fmt, "Math Speed Run")

# ---------- Leaderboard browser ----------
def browse_leaderboards(data):
    while True:
        clear_screen()
        print(Fore.MAGENTA + """
=== Leaderboards ===
1) Guess the Number (by mode)
2) Reaction Game (by rounds)
3) Gibberish Typing (by words)
4) Number Memory (by mode)
5) Sequence Tap (by steps)
6) Word Memory (by words)
7) Math Speed (by problems)
8) Back
""")
        ch = input("Choose: ").strip()
        if ch == "1":
            mk = input("Enter GTN mode key (1..7 or custom_low_high): ").strip()
            if mk:
                show_guess_leaderboard(read_save(), mk)
            pause()
        elif ch == "2":
            r = input("Enter rounds (2,3,5,7,10,15,25): ").strip()
            if r.isdigit():
                show_reaction_leaderboard(read_save(), int(r))
            pause()
        elif ch == "3":
            w = input("Enter words (5,10,15,20,25,30,35,40): ").strip()
            if w.isdigit():
                show_gibberish_leaderboard(read_save(), int(w))
            pause()
        elif ch == "4":
            mk = input("Enter Number Memory mode (easy_2, normal_4, hard_6): ").strip()
            if mk:
                show_number_memory_leaderboard(read_save(), mk)
            pause()
        elif ch == "5":
            s = input("Enter steps (5,10,15,20): ").strip()
            if s.isdigit():
                show_sequence_leaderboard(read_save(), int(s))
            pause()
        elif ch == "6":
            w = input("Enter words (5,10,15): ").strip()
            if w.isdigit():
                show_word_memory_leaderboard(read_save(), int(w))
            pause()
        elif ch == "7":
            p = input("Enter problems (10,20,30,50): ").strip()
            if p.isdigit():
                show_math_speed_leaderboard(read_save(), int(p))
            pause()
        elif ch == "8":
            return
        else:
            print(Fore.RED + "Invalid.")
            pause()

# ---------- Session and main menu ----------
def main_menu():
    data = read_save()
    session = SessionTracker(player=None)
    while True:
        clear_screen()
        print(Fore.MAGENTA + """
==== Ultimate Console Arcade ====
1) Guess the Number
2) Reaction Game
3) Gibberish Typing
4) Number Memory
5) Sequence Tap
6) Word Memory Chain
7) Math Speed Run
8) View Leaderboards
9) View My Achievements
0) Exit
""")
        ch = input("Select: ").strip()
        if ch == "1":
            play_guess_the_number(data, session)
        elif ch == "2":
            play_reaction(data, session)
        elif ch == "3":
            play_gibberish(data, session)
        elif ch == "4":
            play_number_memory(data, session)
        elif ch == "5":
            play_sequence_tap(data, session)
        elif ch == "6":
            play_word_memory(data, session)
        elif ch == "7":
            play_math_speed(data, session)
        elif ch == "8":
            browse_leaderboards(data)
        elif ch == "9":
            player = input("Enter your player name to view achievements: ").strip()
            dd = read_save()
            p = dd["players"].get(player)
            if not p:
                print("No such player or no achievements yet.")
            else:
                print(Fore.YELLOW + f"\nAchievements for {player}:")
                for a in p.get("achievements", []):
                    print("-", ACH_LIST.get(a, a))
                print(f"\nTotal games played: {p.get('games_played', 0)}")
            pause()
        elif ch == "0":
            print(Fore.GREEN + "Goodbye!")
            write_save(data)
            sys.exit(0)
        else:
            print(Fore.RED + "Invalid.")
            pause()

# ---------- Start ----------
if __name__ == "__main__":
    # ensure save exists
    if not os.path.exists(HIGHSCORE_FILE):
        write_save(BASE_SAVE)
    main_menu()
