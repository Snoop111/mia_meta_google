"""
Creative Analysis Routes

Refactored API endpoints for creative analysis with improved modularity.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from .models import CreativeAnalysisRequest, CreativeAnalysisResponse, PRESET_QUESTIONS
from .account_context import get_account_context
from .analysis import analyze_creative_question

router = APIRouter()

@router.post("/api/creative-analysis-v2", response_model=CreativeAnalysisResponse)
async def analyze_creative_assets(
    request: CreativeAnalysisRequest,
    db: Session = Depends(get_db)
):
    """
    Refactored creative analysis endpoint with improved modularity

    This is a cleaner version of the original /api/creative-analysis endpoint,
    broken down into smaller, maintainable modules.
    """
    try:
        # Validate question is in preset list
        category_questions = PRESET_QUESTIONS.get(request.category, [])
        if request.question not in category_questions:
            raise HTTPException(
                status_code=400,
                detail=f"Question '{request.question}' not found in category '{request.category}'"
            )

        # Get account context
        account_context = get_account_context(request.session_id, db)

        print(f"[CREATIVE-V2] Analyzing question: '{request.question}' for account: {account_context['account_name']}")

        # Perform analysis
        result = await analyze_creative_question(
            question=request.question,
            category=request.category,
            account_context=account_context,
            start_date=request.start_date,
            end_date=request.end_date
        )

        if not result.get("success", False):
            return CreativeAnalysisResponse(
                success=False,
                analysis=result.get("analysis", "Analysis failed"),
                error=result.get("error")
            )

        return CreativeAnalysisResponse(
            success=True,
            analysis=result["analysis"],
            source="creative-analysis-v2"
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"[CREATIVE-V2] Unexpected error: {e}")
        return CreativeAnalysisResponse(
            success=False,
            analysis="An unexpected error occurred during analysis.",
            error=str(e)
        )

@router.get("/api/creative-questions")
async def get_creative_questions():
    """Get all available creative analysis questions by category"""
    return {
        "success": True,
        "questions": PRESET_QUESTIONS,
        "total_questions": sum(len(questions) for questions in PRESET_QUESTIONS.values())
    }

@router.get("/api/creative-questions/{category}")
async def get_creative_questions_by_category(category: str):
    """Get creative analysis questions for a specific category"""
    if category not in PRESET_QUESTIONS:
        raise HTTPException(status_code=404, detail=f"Category '{category}' not found")

    return {
        "success": True,
        "category": category,
        "questions": PRESET_QUESTIONS[category],
        "count": len(PRESET_QUESTIONS[category])
    }