"""Domain data classes, named after the terms in GLOSSARY.md."""

from dataclasses import dataclass, field

MASTERY_LEVELS = ("basic", "intermediate", "advanced")
MASTERED_LEVELS = ("intermediate", "advanced")


@dataclass(frozen=True)
class Skill:
    """A concrete technical capability in the Catalog."""

    name: str
    category: str
    description: str
    difficulty: int  # Difficulty, 1 to 5
    prerequisites: tuple[str, ...] = ()  # names of Prerequisite Skills


@dataclass
class LearnerProfile:
    """Target Role, known Skills with their Mastery level, and interests."""

    role: str
    known_skills: dict[str, str] = field(default_factory=dict)  # Skill name -> Mastery level
    interests: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class LearningPathItem:
    """One recommended Skill within a Learning path."""

    skill: str
    frequency: float  # percentage of the Role's Offers mentioning the Skill
    effort: int
    explanation: str  # short, in Spanish


@dataclass(frozen=True)
class LearningPath:
    """Ordered list of Skills to learn; respects Prerequisites."""

    role: str
    items: list[LearningPathItem]
