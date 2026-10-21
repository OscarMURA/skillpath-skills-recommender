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
    reviewed: bool = False  # True once a human reviewed the row


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
    similarity: float = 0.0  # cosine with the Learner's known Skills and interests, in [0, 1]


@dataclass(frozen=True)
class LearningPath:
    """Ordered list of Skills to learn; respects Prerequisites."""

    role: str
    items: list[LearningPathItem]
    unrecognized_interests: list[str] = field(default_factory=list)
    cold_start: bool = False  # True when the Learner profile has no known Skill or recognized interest

    def most_frequent(self, n: int = 10) -> list[LearningPathItem]:
        """The n candidate Skills with highest Frequency in the Role's Offers.

        Pure Frequency, ties by name ascending; Skills with Frequency 0 are left out.
        Independent of the Learning path order (which also weighs Effort).
        """
        ranked = sorted(
            (i for i in self.items if i.frequency > 0), key=lambda i: (-i.frequency, i.skill)
        )
        return ranked[:n]
