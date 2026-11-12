import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set

@dataclass
class DiffHunk:
    old_start: int
    old_length: int
    new_start: int
    new_length: int
    header: str
    method_hint: Optional[str] = None
    lines_touched: List[int] = field(default_factory=list)

@dataclass
class FileDiff:
    old_path: str
    new_path: str
    file_name: str
    class_name: Optional[str]
    hunks: List[DiffHunk] = field(default_factory=list)
    modified_lines: Set[int] = field(default_factory=set)

@dataclass
class ParsedPatch:
    """
    Ground truth facts extracted from a developer Gold Patch.
    Separates production Java files from documentation and test files for thesis classification.
    """
    # All files modified in the diff
    all_files: List[FileDiff] = field(default_factory=list)

    # Distinct categories
    production_files: List[FileDiff] = field(default_factory=list)
    test_files: List[FileDiff] = field(default_factory=list)
    documentation_files: List[FileDiff] = field(default_factory=list)

    # Paths by category
    production_file_paths: Set[str] = field(default_factory=set)
    production_file_basenames: Set[str] = field(default_factory=set)
    documentation_file_paths: Set[str] = field(default_factory=set)
    documentation_file_basenames: Set[str] = field(default_factory=set)
    test_file_paths: Set[str] = field(default_factory=set)
    test_file_basenames: Set[str] = field(default_factory=set)

    # Defect Localization targets (strictly production Java source files)
    files: List[FileDiff] = field(default_factory=list)
    file_paths: Set[str] = field(default_factory=set)
    file_basenames: Set[str] = field(default_factory=set)

    class_names: Set[str] = field(default_factory=set)
    method_names: Set[str] = field(default_factory=set)
    lines_by_file: Dict[str, Set[int]] = field(default_factory=dict)

    @property
    def is_single_file_scope(self) -> bool:
        """True if exactly 1 production Java file is modified (localized defect)."""
        return len(self.production_files) == 1

    @property
    def is_multi_file_scope(self) -> bool:
        """True if 2 or more production Java files are modified (multi-file scope)."""
        return len(self.production_files) > 1

    @property
    def scope_label(self) -> str:
        count = len(self.production_files)
        return f"Single-file ({count})" if count == 1 else f"Multi-file ({count})"

class PatchParser:
    """
    Parses unified git diffs (.patch) to establish ground-truth fault localization targets.
    Categorizes production Java files separately from documentation and test files.
    """

    DIFF_FILE_RE = re.compile(r"^diff --git a/(.*?) b/(.*?)$")
    HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(?:\s*(.*))?$")
    METHOD_EXTRACT_RE = re.compile(r"(?:public|protected|private|static|\s)*[\w<>\[\],\s]+\s+(\w+)\s*\(")

    @staticmethod
    def classify_file(path_str: str) -> str:
        """
        Categorizes a file into:
        - 'production_java': Java source code under production tree
        - 'test': Test sources
        - 'documentation': Markdown, documentation, changelog, authors, etc.
        """
        p = Path(path_str)
        ext = p.suffix.lower()
        name = p.name.lower()

        is_test = (
            "src/test/" in path_str or "/test/" in path_str or path_str.startswith("test/") or
            p.stem.endswith("Test") or p.stem.endswith("Tests") or p.stem.endswith("TestCase")
        )
        if is_test:
            return "test"

        doc_extensions = {".md", ".markdown", ".txt", ".rst", ".html", ".htm", ".adoc", ".pdf"}
        doc_filenames = {"authors", "changes", "changelog", "license", "notice", "readme", "releasenotes"}
        is_doc = (
            ext in doc_extensions or
            name in doc_filenames or
            any(name.startswith(x) for x in doc_filenames) or
            "docs/" in path_str or "doc/" in path_str or "website/" in path_str
        )
        if is_doc:
            return "documentation"

        if path_str.endswith(".java"):
            return "production_java"

        return "other"

    @classmethod
    def parse(cls, patch_content: str) -> ParsedPatch:
        parsed = ParsedPatch()
        if not patch_content or not patch_content.strip():
            return parsed

        current_file: Optional[FileDiff] = None
        current_category: str = "production_java"
        lines = patch_content.splitlines()
        i = 0

        while i < len(lines):
            line = lines[i]
            diff_match = cls.DIFF_FILE_RE.match(line)
            if diff_match:
                old_path = diff_match.group(1)
                new_path = diff_match.group(2)
                file_name = Path(new_path).name
                class_name = cls._extract_class_name(new_path)
                category = cls.classify_file(new_path)
                current_category = category

                current_file = FileDiff(
                    old_path=old_path,
                    new_path=new_path,
                    file_name=file_name,
                    class_name=class_name
                )
                parsed.all_files.append(current_file)

                if category == "production_java":
                    parsed.production_files.append(current_file)
                    parsed.production_file_paths.add(new_path)
                    parsed.production_file_basenames.add(file_name)
                    # Production Java files are the target for defect localization
                    parsed.files.append(current_file)
                    parsed.file_paths.add(new_path)
                    parsed.file_basenames.add(file_name)
                    if class_name:
                        parsed.class_names.add(class_name)
                elif category == "documentation":
                    parsed.documentation_files.append(current_file)
                    parsed.documentation_file_paths.add(new_path)
                    parsed.documentation_file_basenames.add(file_name)
                elif category == "test":
                    parsed.test_files.append(current_file)
                    parsed.test_file_paths.add(new_path)
                    parsed.test_file_basenames.add(file_name)

                i += 1
                continue

            hunk_match = cls.HUNK_RE.match(line)
            if hunk_match and current_file:
                old_start = int(hunk_match.group(1))
                old_length = int(hunk_match.group(2)) if hunk_match.group(2) else 1
                new_start = int(hunk_match.group(3))
                new_length = int(hunk_match.group(4)) if hunk_match.group(4) else 1
                header = hunk_match.group(5) or ""

                # Only extract Java methods from production code
                if current_category == "production_java":
                    method_hint = cls._extract_method_from_header(header)
                    if method_hint:
                        parsed.method_names.add(method_hint)
                else:
                    method_hint = None

                # Collect line numbers touched in the unpatched file
                touched_lines = []
                # If old_length is 0 (pure insertion), touch the anchor line old_start
                if old_length == 0:
                    touched_lines.append(old_start)
                else:
                    touched_lines = list(range(old_start, old_start + old_length))

                for l_num in touched_lines:
                    current_file.modified_lines.add(l_num)

                hunk = DiffHunk(
                    old_start=old_start,
                    old_length=old_length,
                    new_start=new_start,
                    new_length=new_length,
                    header=header,
                    method_hint=method_hint,
                    lines_touched=touched_lines
                )
                current_file.hunks.append(hunk)

            i += 1

        for f in parsed.files:
            parsed.lines_by_file[f.new_path] = f.modified_lines
            parsed.lines_by_file[f.file_name] = f.modified_lines

        return parsed

    @classmethod
    def _extract_class_name(cls, path_str: str) -> Optional[str]:
        """
        Infers fully qualified class name from standard Java maven path.
        e.g. 'gson/src/main/java/com/google/gson/Gson.java' -> 'com.google.gson.Gson'
        """
        if not path_str.endswith(".java"):
            return None

        # Check for standard java source root
        for marker in ["src/main/java/", "src/test/java/", "java/"]:
            if marker in path_str:
                pkg_part = path_str.split(marker)[-1]
                return pkg_part[:-5].replace("/", ".")

        # Fallback to file basename
        return Path(path_str).stem

    @classmethod
    def _extract_method_from_header(cls, header: str) -> Optional[str]:
        """Extracts candidate method name from the diff @@ header."""
        if not header:
            return None
        match = cls.METHOD_EXTRACT_RE.search(header)
        if match:
            name = match.group(1)
            # Filter out non-methods like 'class', 'if', 'while'
            if name not in {"class", "interface", "enum", "if", "for", "while", "switch"}:
                return name
        return None
