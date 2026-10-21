"""SkillPath: recommends a Learning path of Skills for a Learner profile."""

from skillpath.models import LearnerProfile, LearningPath, LearningPathItem, Skill
from skillpath.recommender import recommend

__all__ = ["recommend", "LearnerProfile", "LearningPath", "LearningPathItem", "Skill"]
