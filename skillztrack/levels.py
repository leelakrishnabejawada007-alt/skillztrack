"""Skill-level scale shared by models, forms and the engine (pure Python)."""

MIN_LEVEL = 0
MAX_LEVEL = 5

LEVEL_LABELS = {
    0: "No experience",
    1: "Beginner",
    2: "Basic",
    3: "Intermediate",
    4: "Advanced",
    5: "Expert",
}
LEVEL_CHOICES = list(LEVEL_LABELS.items())


def level_label(level):
    return LEVEL_LABELS.get(level, str(level))
