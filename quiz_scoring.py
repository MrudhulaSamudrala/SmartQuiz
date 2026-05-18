from config import OPTION_LABELS, TYPE_LABELS, TYPE_MCQ, TYPE_ONE_WORD, TYPE_TRUE_FALSE


def normalize_word(text: str) -> str:
    return " ".join(text.strip().lower().split())


def is_correct(question: dict, user_answer) -> bool:
    if user_answer is None:
        return False

    qtype = question["type"]

    if qtype == TYPE_MCQ:
        return user_answer == question["correct_index"]

    if qtype == TYPE_TRUE_FALSE:
        return bool(user_answer) == bool(question["correct_answer"])

    if qtype == TYPE_ONE_WORD:
        return normalize_word(str(user_answer)) == normalize_word(question["correct_answer"])

    return False


def calculate_score(quiz: list[dict], answers: dict) -> tuple[int, int, int]:
    total = len(quiz)
    score = sum(1 for i, q in enumerate(quiz) if is_correct(q, answers.get(i)))
    skipped = sum(1 for i in range(total) if i not in answers)
    return score, total, skipped


def format_user_answer(question: dict, user_answer) -> str:
    if user_answer is None:
        return "No answer"

    qtype = question["type"]
    if qtype == TYPE_MCQ:
        return OPTION_LABELS[user_answer] + ". " + question["options"][user_answer]
    if qtype == TYPE_TRUE_FALSE:
        return "True" if user_answer else "False"
    return str(user_answer)


def format_correct_answer(question: dict) -> str:
    qtype = question["type"]
    if qtype == TYPE_MCQ:
        idx = question["correct_index"]
        return OPTION_LABELS[idx] + ". " + question["options"][idx]
    if qtype == TYPE_TRUE_FALSE:
        return "True" if question["correct_answer"] else "False"
    return question["correct_answer"]
