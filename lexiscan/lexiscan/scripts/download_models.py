"""
LexiScan — Model Download Script
Downloads and caches LegalBERT and spaCy models.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from backend.utils.config import settings


def download_legalbert():
    logger.info(f"Downloading LegalBERT: {settings.LEGALBERT_MODEL}")
    try:
        from transformers import AutoTokenizer, AutoModelForSequenceClassification
        tokenizer = AutoTokenizer.from_pretrained(
            settings.LEGALBERT_MODEL,
            cache_dir=str(settings.model_cache_path),
        )
        model = AutoModelForSequenceClassification.from_pretrained(
            settings.LEGALBERT_MODEL,
            cache_dir=str(settings.model_cache_path),
            num_labels=41,
        )
        logger.success(f"✅ LegalBERT cached to {settings.MODEL_CACHE_DIR}")
    except Exception as e:
        logger.error(f"❌ LegalBERT download failed: {e}")


def download_spacy():
    logger.info("Downloading spaCy model: en_core_web_sm")
    import subprocess
    result = subprocess.run(
        [sys.executable, "-m", "spacy", "download", "en_core_web_sm"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        logger.success("✅ spaCy model downloaded")
    else:
        logger.error(f"❌ spaCy download failed: {result.stderr}")


if __name__ == "__main__":
    download_spacy()
    download_legalbert()
    logger.success("🎉 All models ready!")
