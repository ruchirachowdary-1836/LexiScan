"""LexiScan — Health Check Routes"""

from fastapi import APIRouter
from backend.utils.config import settings

router = APIRouter()


@router.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


@router.get("/health/models")
def model_health():
    """Check if models are loaded."""
    status = {}
    try:
        import spacy
        spacy.load("en_core_web_sm")
        status["spacy"] = "ok"
    except Exception as e:
        status["spacy"] = f"error: {e}"

    try:
        from transformers import AutoTokenizer
        AutoTokenizer.from_pretrained("nlpaueb/legal-bert-base-uncased", local_files_only=True)
        status["legalbert"] = "cached"
    except Exception:
        status["legalbert"] = "not cached (will download on first use)"

    return {"models": status}
