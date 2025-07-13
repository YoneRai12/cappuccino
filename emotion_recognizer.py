from textblob import TextBlob


def detect_emotion(text: str) -> str:
    """Return rough sentiment category for the given text."""
    if not text:
        return "neutral"
    polarity = TextBlob(text).sentiment.polarity
    if polarity > 0.1:
        return "positive"
    if polarity < -0.1:
        return "negative"
    return "neutral"
