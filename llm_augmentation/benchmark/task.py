from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

@dataclass
class Task:
    """
    Represents an empirical bug task from SWE-Bench Multilingual (Java).
    """
    instance_id: str
    repo: str
    base_commit: str
    problem_statement: str
    patch: str
    test_patch: str
    hints_text: Optional[str] = None
    created_at: Optional[str] = None
    version: Optional[str] = None
    fail_to_pass: List[str] = field(default_factory=list)
    pass_to_pass: List[str] = field(default_factory=list)
    raw_data: Dict[str, Any] = field(default_factory=dict)

    @property
    def repo_short_name(self) -> str:
        """Returns short name of the repo (e.g. 'gson' for 'google/gson')."""
        return self.repo.split("/")[-1]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        return cls(
            instance_id=data["instance_id"],
            repo=data["repo"],
            base_commit=data["base_commit"],
            problem_statement=data.get("problem_statement", ""),
            patch=data.get("patch", ""),
            test_patch=data.get("test_patch", ""),
            hints_text=data.get("hints_text"),
            created_at=data.get("created_at"),
            version=data.get("version"),
            fail_to_pass=data.get("FAIL_TO_PASS", []),
            pass_to_pass=data.get("PASS_TO_PASS", []),
            raw_data=data
        )
