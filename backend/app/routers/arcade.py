from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.rate_limit import limiter
from app.models.user import User, UserProgress
from app.routers.users import get_current_user
from app.schemas.arcade import (
    LeaderboardEntryOut,
    LeaderboardOut,
    QuizScoreIn,
    QuizScoreOut,
    QuizSessionOut,
)
from app.services import arcade_service, quiz_rush_service

router = APIRouter(prefix="/arcade", tags=["arcade"])


@router.get("/quiz-rush/session", response_model=QuizSessionOut)
@limiter.limit("20/hour")
async def quiz_rush_session(
    request: Request,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> QuizSessionOut:
    items = await quiz_rush_service.build_session(session, user)
    return QuizSessionOut(items=items)


@router.post("/quiz-rush/score", response_model=QuizScoreOut)
@limiter.limit("30/hour")
async def quiz_rush_score(
    request: Request,
    payload: QuizScoreIn,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> QuizScoreOut:
    items = [it.model_dump() for it in payload.session_items]
    answers = [a.model_dump() for a in payload.answers]
    result = quiz_rush_service.score_submission(items, answers)
    market = user.active_market_code or "GB"
    progress = await session.get(UserProgress, user.id)
    coins = await arcade_service.award_arcade_coins(
        session, progress, result["correct"], market_code=market
    )
    await arcade_service.record_score(
        session, user_id=user.id, game="quiz_rush", points=result["points"], market_code=market
    )
    best = await arcade_service.personal_best(session, user_id=user.id, game="quiz_rush")
    board = await arcade_service.weekly_leaderboard(session, game="quiz_rush", market_code=market)
    rank = next((i + 1 for i, row in enumerate(board) if row[0] == user.username), None)
    await session.commit()
    return QuizScoreOut(
        points=result["points"],
        coins_awarded=coins,
        personal_best=best,
        leaderboard_rank=rank,
    )


@router.get("/leaderboard", response_model=LeaderboardOut)
@limiter.limit("60/hour")
async def leaderboard(
    request: Request,
    game: str = "quiz_rush",
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> LeaderboardOut:
    market = user.active_market_code or "GB"
    rows = await arcade_service.weekly_leaderboard(session, game=game, market_code=market)
    return LeaderboardOut(
        entries=[LeaderboardEntryOut(username=u, country_code=c, points=p) for u, c, p in rows]
    )
