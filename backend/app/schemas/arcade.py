from pydantic import BaseModel


class MoneyWordGuessOut(BaseModel):
    word: str
    feedback: list[str]


class MoneyWordStateOut(BaseModel):
    length: int
    max_guesses: int
    guesses: list[MoneyWordGuessOut]
    completed: bool
    solved: bool
    definition: str | None
    already_played: bool


class MoneyWordGuessIn(BaseModel):
    guess: str


class QuizItem(BaseModel):
    lesson_id: str
    question: str
    choices: list[str]
    answer_index: int


class QuizSessionOut(BaseModel):
    items: list[QuizItem]


class QuizAnswer(BaseModel):
    lesson_id: str
    choice_index: int
    time_ms: int = 0


class QuizScoreIn(BaseModel):
    session_items: list[QuizItem]
    answers: list[QuizAnswer]


class QuizScoreOut(BaseModel):
    points: int
    coins_awarded: int
    personal_best: int
    leaderboard_rank: int | None


class LeaderboardEntryOut(BaseModel):
    username: str
    country_code: str
    points: int


class LeaderboardOut(BaseModel):
    entries: list[LeaderboardEntryOut]
