"""Score, level and stamp code of every element."""
from collections import Counter

from .model import NOT_CERTIFIED


class Scorer:
    """Assigns scores, levels and stamps according to certification.yaml."""

    def __init__(self, certification, rules_digest, signer):
        self.certification = certification
        self.rules_digest = rules_digest
        self.signer = signer

    @property
    def levels(self):
        """Level definitions, best first."""
        return self.certification.get("levels", [])

    def order(self, level_id):
        """Rank of the level: lower is better."""
        ids = [level["id"] for level in self.levels]
        return ids.index(level_id) if level_id in ids else len(ids)

    def worst(self, levels):
        """The worst level of a list."""
        return max(levels, key=self.order)

    def score_tree(self, entity):
        """Stamp the element after stamping its children."""
        for child in entity.children:
            self.score_tree(child)
        active = [v for v in entity.violations if not v.suppressed]
        entity.score = self._score(active)
        own = self._level(entity.score, active)
        entity.level = self.worst([own] + [c.level for c in entity.children])
        entity.stamp = self.signer.stamp(
            entity, self.rules_digest, entity.level)

    def _score(self, violations):
        """Points left after penalties, never below zero."""
        scoring = self.certification.get("scoring", {})
        penalties = scoring.get("penalties", {})
        lost = sum(penalties.get(v.severity, 0) for v in violations)
        return max(scoring.get("start", 100) - lost, 0)

    def _level(self, score, violations):
        """First level satisfied by the score and the violations."""
        counts = Counter(v.severity for v in violations)
        for level in self.levels:
            if self._satisfies(level, score, counts):
                return level["id"]
        return NOT_CERTIFIED

    @staticmethod
    def _satisfies(level, score, counts):
        """True when the element is within the level's limits."""
        limits = {"error": "max_errors", "warning": "max_warnings",
                  "info": "max_infos"}
        within = all(counts[sev] <= level.get(key, counts[sev])
                     for sev, key in limits.items())
        return within and score >= level.get("min_score", 0)

    def label(self, level_id):
        """Readable label of the level."""
        for level in self.levels:
            if level["id"] == level_id:
                return level.get("label", level_id)
        return "Not certified"
