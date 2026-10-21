"""Domain data classes, named after the terms in GLOSSARY.md."""

from dataclasses import dataclass, field

MASTERY_LEVELS = ("basic", "intermediate", "advanced")
MASTERED_LEVELS = ("intermediate", "advanced")
EXPERIENCE_LEVELS = ("experienced", "entry")


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
    # "experienced" (default) uses the base Frequency only; "entry" (student or
    # recent graduate) blends in the entry-level Frequency. See docs/entry-level-complement.md.
    experience_level: str = "experienced"


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
    experience_level: str = "experienced"
    # Entry-level Offers behind the blend (None when not entry level or no data for the Role).
    entry_sample_size: int | None = None
    # Weight of the entry-level Frequency in the blend (0.0 when not blended).
    entry_weight: float = 0.0

    def most_frequent(self, n: int = 10) -> list[LearningPathItem]:
        """The n candidate Skills with highest Frequency in the Role's Offers.

        Pure Frequency, ties by name ascending; Skills with Frequency 0 are left out.
        Independent of the Learning path order (which also weighs Effort).
        """
        ranked = sorted(
            (i for i in self.items if i.frequency > 0), key=lambda i: (-i.frequency, i.skill)
        )
        return ranked[:n]
