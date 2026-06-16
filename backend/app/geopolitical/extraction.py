"""Entity extraction and sentiment analysis for geopolitical news."""

import logging
import functools
from typing import Optional

import spacy
from textblob import TextBlob

from app.geopolitical.models import NewsArticle, ExtractedEntity

logger = logging.getLogger(__name__)


@functools.lru_cache(maxsize=1)
def get_nlp():
    try:
        nlp = spacy.load("en_core_web_sm")
        logger.info("spaCy model loaded successfully")
        return nlp
    except OSError:
        logger.warning("spaCy model not found. Run: python -m spacy download en_core_web_sm")
        return None


ENTITY_TYPE_MAP = {
    "GPE": "COUNTRY",
    "ORG": "ORGANIZATION",
    "PERSON": "PERSON",
    "PRODUCT": "PRODUCT",
    "EVENT": "EVENT",
    "FAC": "FACILITY",
    "LOC": "LOCATION",
    "NORP": "GROUP",
    "LAW": "LAW",
    "MONEY": "MONEY",
}


def analyze_sentiment(text: str) -> str:
    try:
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity
        if polarity > 0.1:
            return "positive"
        elif polarity < -0.1:
            return "negative"
        return "neutral"
    except Exception:
        return "neutral"


def extract_entities(articles: list[NewsArticle]) -> list[ExtractedEntity]:
    nlp = get_nlp()
    seen: set[tuple[str, str]] = set()
    entities: list[ExtractedEntity] = []

    for article in articles:
        text = f"{article.title}. {article.content}"
        article_sentiment = analyze_sentiment(text)

        if nlp:
            doc = nlp(text[:100000])
            for ent in doc.ents:
                mapped_type = ENTITY_TYPE_MAP.get(ent.label_, "OTHER")
                key = (ent.text.lower(), mapped_type)
                if key not in seen:
                    seen.add(key)
                    entities.append(ExtractedEntity(
                        name=ent.text,
                        entity_type=mapped_type,
                        sentiment=article_sentiment,
                        confidence=0.5,
                    ))
        else:
            import re
            words = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
            for w in set(words[:50]):
                key = (w.lower(), "ORGANIZATION")
                if key not in seen:
                    seen.add(key)
                    entities.append(ExtractedEntity(
                        name=w,
                        entity_type="ORGANIZATION",
                        sentiment=article_sentiment,
                        confidence=0.3,
                    ))

    logger.info(f"extract_entities: {len(entities)} entities from {len(articles)} articles")
    return entities
