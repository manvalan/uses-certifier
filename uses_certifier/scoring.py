"""Punteggio, livello e bollino di ogni elemento."""
from collections import Counter

from .hashing import digest
from .model import NOT_CERTIFIED


class Scorer:
    """Assegna punteggi e livelli secondo certification.yaml."""

    def __init__(self, certification, rules_digest):
        scoring = certification.get("scoring", {})
        self.start = scoring.get("start", 100)
        self.penalties = scoring.get("penalties", {})
        self.levels = certification.get("levels", [])
        self.rules_digest = rules_digest

    def order(self, level_id):
        """Posizione del livello: più bassa è migliore."""
        ids = [level["id"] for level in self.levels]
        return ids.index(level_id) if level_id in ids else len(ids)

    def score_tree(self, entity):
        """Assegna il bollino all'elemento dopo averlo dato ai figli."""
        for child in entity.children:
            self.score_tree(child)
        active = [v for v in entity.violations if not v.suppressed]
        entity.score = self._score(active)
        own = self._level(entity.score, active)
        entity.level = self.worst([own] + [c.level for c in entity.children])
        entity.stamp = digest(
            entity.source_hash + self.rules_digest + entity.level)[:16]

    def worst(self, levels):
        """Il livello peggiore di un elenco."""
        return max(levels, key=self.order)

    def _score(self, violations):
        """Punti rimasti dopo le penalità, mai sotto zero."""
        lost = sum(self.penalties.get(v.severity, 0) for v in violations)
        return max(self.start - lost, 0)

    def _level(self, score, violations):
        """Primo livello soddisfatto dal punteggio e dalle violazioni."""
        counts = Counter(v.severity for v in violations)
        for level in self.levels:
            if self._satisfies(level, score, counts):
                return level["id"]
        return NOT_CERTIFIED

    @staticmethod
    def _satisfies(level, score, counts):
        """Vero se l'elemento rientra nei limiti del livello."""
        limits = {"error": "max_errors", "warning": "max_warnings",
                  "info": "max_infos"}
        within = all(counts[sev] <= level.get(key, counts[sev])
                     for sev, key in limits.items())
        return within and score >= level.get("min_score", 0)

    def label(self, level_id):
        """Etichetta leggibile del livello."""
        for level in self.levels:
            if level["id"] == level_id:
                return level.get("label", level_id)
        return "Non certificato"
