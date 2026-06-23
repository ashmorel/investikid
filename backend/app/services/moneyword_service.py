from collections import Counter

MAX_GUESSES = 6


def evaluate_guess(answer: str, guess: str) -> list[str]:
    answer, guess = answer.upper(), guess.upper()
    result = ["absent"] * len(guess)
    remaining = Counter(answer)
    # Pass 1: exact matches consume answer letters.
    for i, ch in enumerate(guess):
        if i < len(answer) and ch == answer[i]:
            result[i] = "correct"
            remaining[ch] -= 1
    # Pass 2: present only while an unconsumed copy remains.
    for i, ch in enumerate(guess):
        if result[i] == "correct":
            continue
        if remaining.get(ch, 0) > 0:
            result[i] = "present"
            remaining[ch] -= 1
    return result
