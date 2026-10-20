import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from .task import Task

@dataclass
class RepoContext:
    """
    Context representing a prepared target codebase for a task.
    """
    repo_path: Path
    task_id: str
    base_commit: str
    target_classes_dirs: List[Path] = field(default_factory=list)
    is_compilable: bool = True
    compile_error: Optional[str] = None

    @property
    def target_classes_arg(self) -> str:
        """Returns comma-separated target/classes paths for SootUp."""
        return ",".join(str(p.resolve()) for p in self.target_classes_dirs)

class RepoManager:
    """
    Manages target Java codebases: locates repos, checks out base commits,
    discovers compiled bytecode, and handles compilation validation.
    """

    KNOWN_WORKSPACE_ROOTS = [
        Path("workspace"),
        Path("/Volumes/BrainStorm/Github/SootUp-Store/thesis-experiments"),
        Path("/Volumes/BrainStorm/Github/SootUp-Store/swebench-java-evaluation/workspace"),
    ]

    def __init__(self, workspace_roots: Optional[List[Path | str]] = None):
        self.workspace_roots: List[Path] = []
        if workspace_roots:
            self.workspace_roots.extend([Path(r).resolve() for r in workspace_roots])
        for default_root in self.KNOWN_WORKSPACE_ROOTS:
            if default_root.exists() and default_root.resolve() not in self.workspace_roots:
                self.workspace_roots.append(default_root.resolve())

    def find_repo_dir(self, repo_name: str) -> Optional[Path]:
        """
        Locates the directory for a repo like 'google/gson' or 'apache/druid'.
        """
        short_name = repo_name.split("/")[-1]
        owner = repo_name.split("/")[0] if "/" in repo_name else ""

        # Search patterns
        search_candidates = [
            f"{owner}/{short_name}",
            f"{owner}-{short_name}/{short_name}",
            short_name,
        ]

        for root in self.workspace_roots:
            for cand in search_candidates:
                candidate_path = root / cand
                if candidate_path.is_dir() and (candidate_path / ".git").exists():
                    return candidate_path

            # Direct recursive shallow search
            for p in root.glob(f"**/{short_name}"):
                if p.is_dir() and (p / ".git").exists():
                    return p

        return None

    def prepare_repo_for_task(
        self,
        task: Task,
        checkout: bool = False,
        compile_if_needed: bool = True
    ) -> RepoContext:
        """
        Prepares target repo for task: checks out base_commit and verifies compiled bytecode.
        """
        repo_dir = self.find_repo_dir(task.repo)
        if not repo_dir:
            return RepoContext(
                repo_path=Path("."),
                task_id=task.instance_id,
                base_commit=task.base_commit,
                is_compilable=False,
                compile_error=f"Repository for '{task.repo}' not found in known workspace paths."
            )

        context = RepoContext(
            repo_path=repo_dir,
            task_id=task.instance_id,
            base_commit=task.base_commit
        )

        # 1. Checkout base_commit if requested
        if checkout:
            try:
                subprocess.run(
                    ["git", "checkout", "-f", task.base_commit],
                    cwd=repo_dir,
                    check=True,
                    capture_output=True,
                    text=True
                )
            except subprocess.CalledProcessError as e:
                context.is_compilable = False
                context.compile_error = f"Git checkout to {task.base_commit} failed: {e.stderr}"
                return context

        # 2. Find compiled target/classes directories
        class_dirs = self.find_target_classes(repo_dir)

        # 3. If no target classes found and compile_if_needed is True, attempt compilation
        if not class_dirs and compile_if_needed:
            pom_file = repo_dir / "pom.xml"
            if pom_file.exists():
                try:
                    subprocess.run(
                        ["mvn", "compile", "-DskipTests", "-q"],
                        cwd=repo_dir,
                        check=True,
                        capture_output=True,
                        text=True,
                        timeout=300
                    )
                    class_dirs = self.find_target_classes(repo_dir)
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
                    err = getattr(e, "stderr", str(e))
                    context.is_compilable = False
                    context.compile_error = f"Bytecode compilation failed: {err}"
                    return context
            else:
                context.is_compilable = False
                context.compile_error = "No pom.xml found to compile bytecode."
                return context

        context.target_classes_dirs = class_dirs
        if not class_dirs:
            context.is_compilable = False
            context.compile_error = "No compiled target/classes directories found after compilation check."

        return context

    @classmethod
    def find_target_classes(cls, repo_dir: Path) -> List[Path]:
        """
        Finds all target/classes directories (including multi-module Maven projects).
        """
        dirs = []
        for p in repo_dir.glob("**/target/classes"):
            if p.is_dir() and any(p.iterdir()):
                dirs.append(p)
        return dirs
