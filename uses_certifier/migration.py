"""Gradual migration of existing programs to certified code.

In migration mode a project builds even when it is not fully certified.
A source file that reaches the required level is *migrated*: from then
on the build checks it like in a strict project, and certify refuses to
let it fall back below the level. The other files are *legacy*: they are
recorded in the certificate, but the build does not enforce them. The
share of migrated files is the coverage, and the project can require a
minimum coverage that is raised over time.
"""
from dataclasses import dataclass

from .model import NOT_CERTIFIED


@dataclass
class Policy:
    """What the build requires of a project and its certificate."""

    min_level: str = ""
    migration: bool = False
    min_coverage: float = 0

    @classmethod
    def of(cls, project, min_level=None):
        """Policy of a project; min_level overrides the configured one."""
        return cls(min_level or project.min_level, project.migrating,
                   project.migration_min_coverage)

    def wanted(self, levels):
        """Level a file needs to count as migrated."""
        return self.min_level or (levels[-1] if levels else NOT_CERTIFIED)


def at_level(level, wanted, levels):
    """True when level is at least as good as wanted."""
    order = list(levels) + [NOT_CERTIFIED]
    return order.index(level) <= order.index(wanted)


def migrated(data, policy):
    """Paths of the certificate's files that reached the wanted level."""
    levels = data["levels"]
    wanted = policy.wanted(levels)
    return {f["path"] for f in data["files"]
            if at_level(f["level"], wanted, levels)}


def regressions(previous, current, policy):
    """Files migrated in the previous certificate that are now below
    the level, or no longer analysable, as 'path (level)'."""
    now = {f["path"]: f["level"] for f in current["files"]}
    now.update({path: "failed" for path in current["failures"]})
    done = migrated(current, policy)
    return sorted(f"{path} ({now[path]})"
                  for path in migrated(previous, policy)
                  if path in now and path not in done)


def coverage(done, total):
    """Percentage of migrated source files."""
    return 100.0 * done / total if total else 100.0


def coverage_note(done, total, policy, wanted):
    """One line on the progress of the migration."""
    required = (f", required {policy.min_coverage:g}%"
                if policy.min_coverage else "")
    return (f"migration: {done} of {total} source files at {wanted} or "
            f"better ({coverage(done, total):.0f}%{required}); the others "
            f"are legacy and not enforced")
