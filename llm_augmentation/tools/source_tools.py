import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

SOURCE_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "search_source_code",
        "description": "Searches the target Java repository source code for a specific keyword, class name, or method signature. Returns matching file paths and line numbers.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Text, class name, or regex pattern to search for (e.g. 'class TypeAdapter', 'doubleAdapter')"
                },
                "file_pattern": {
                    "type": "string",
                    "description": "Optional glob pattern for files to search in (defaults to '*.java')"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of matching lines to return (default: 20)"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "read_source_file",
        "description": "Reads source code lines from a specific Java file in the repository.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Relative or absolute path to the Java file (e.g. 'gson/src/main/java/com/google/gson/Gson.java' or 'TypeAdapters.java')"
                },
                "start_line": {
                    "type": "integer",
                    "description": "Starting line number to read (1-indexed, default: 1)"
                },
                "end_line": {
                    "type": "integer",
                    "description": "Ending line number to read (inclusive, default: 100)"
                }
            },
            "required": ["file_path"]
        }
    },
    {
        "name": "find_files",
        "description": "Finds files matching a glob pattern across the repository (e.g. '*TypeAdapter*.java', '*Gson*.java'). Helps locate files by name without knowing the full path.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_pattern": {
                    "type": "string",
                    "description": "Glob pattern to match file names (e.g. '*TypeAdapter*.java')"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of file paths to return (default: 30)"
                }
            },
            "required": ["file_pattern"]
        }
    },
    {
        "name": "list_directory",
        "description": "Lists files and subdirectories in a specific repository directory, or root if path is empty. Helps navigate packages and discover project layout.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative directory path (e.g. 'gson/src/main/java' or empty for repository root)"
                },
                "max_depth": {
                    "type": "integer",
                    "description": "Maximum directory traversal depth (default: 2)"
                }
            }
        }
    }
]

class SourceToolsExecutor:
    """
    Executes repository source navigation tools directly against the target codebase on disk.
    """

    TOOL_NAMES = {"search_source_code", "read_source_file", "find_files", "list_directory"}

    @classmethod
    def execute(cls, tool_name: str, arguments: Dict[str, Any], repo_path: Path) -> str:
        if not repo_path or not repo_path.exists():
            return f"Error: Repository path '{repo_path}' does not exist on disk."
        repo_path = repo_path.resolve()
        repo_path = Path(repo_path).resolve()

        if tool_name == "search_source_code":
            query = arguments.get("query", "")
            file_pattern = arguments.get("file_pattern", "*.java")
            max_results = int(arguments.get("max_results", 20))
            return cls.search_source_code(query, repo_path, file_pattern=file_pattern, max_results=max_results)

        elif tool_name == "read_source_file":
            file_path = arguments.get("file_path", "")
            start_line = int(arguments.get("start_line", 1))
            end_line = int(arguments.get("end_line", 100))
            return cls.read_source_file(file_path, repo_path, start_line=start_line, end_line=end_line)

        elif tool_name == "find_files":
            file_pattern = arguments.get("file_pattern", "*.java")
            max_results = int(arguments.get("max_results", 30))
            return cls.find_files(file_pattern, repo_path, max_results=max_results)

        elif tool_name == "list_directory":
            path_str = arguments.get("path", "")
            max_depth = int(arguments.get("max_depth", 2))
            return cls.list_directory(path_str, repo_path, max_depth=max_depth)

        return f"Unknown source tool: {tool_name}"

    @classmethod
    def search_source_code(
        cls,
        query: str,
        repo_path: Path,
        file_pattern: str = "*.java",
        max_results: int = 20
    ) -> str:
        if not query or not query.strip():
            return "Error: query parameter is required."

        if not repo_path or not repo_path.exists():
            return f"Error: Repository path '{repo_path}' does not exist on disk."
        repo_path = repo_path.resolve()

        results: List[str] = []
        try:
            pattern = re.compile(re.escape(query), re.IGNORECASE)
        except Exception:
            pattern = re.compile(query, re.IGNORECASE)

        for path in repo_path.rglob(file_pattern):
            if any(part.startswith(".") or part in ["target", "build", ".git"] for part in path.parts):
                continue

            try:
                rel_path = path.relative_to(repo_path)
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    for line_num, line in enumerate(f, start=1):
                        if pattern.search(line):
                            snippet = line.strip()
                            if len(snippet) > 120:
                                snippet = snippet[:117] + "..."
                            results.append(f"{rel_path}:{line_num}: {snippet}")
                            if len(results) >= max_results:
                                break
            except Exception:
                continue

            if len(results) >= max_results:
                break

        if not results:
            return f"No matches found for query '{query}' across {file_pattern} files in {repo_path.name}."

        header = f"=== Search Results for '{query}' ({len(results)} matches) ===\n"
        return header + "\n".join(results)

    @classmethod
    def read_source_file(
        cls,
        file_path_str: str,
        repo_path: Path,
        start_line: int = 1,
        end_line: int = 100
    ) -> str:
        if not file_path_str or not file_path_str.strip():
            return "Error: file_path parameter is required."

        if not repo_path or not repo_path.exists():
            return f"Error: Repository path '{repo_path}' does not exist."

        # Locate target file
        candidate = repo_path / file_path_str
        target_file: Optional[Path] = None

        if candidate.is_file():
            target_file = candidate
        else:
            # Try searching by basename or partial path
            base_name = Path(file_path_str).name
            matches = [
                p for p in repo_path.rglob(base_name)
                if p.is_file() and not any(part.startswith(".") or part in ["target", "build", ".git"] for part in p.parts)
            ]
            if matches:
                target_file = matches[0]

        if not target_file:
            # Suggest possible files with similar names
            base_query = Path(file_path_str).stem
            similar = [
                str(p.relative_to(repo_path)) for p in repo_path.rglob(f"*{base_query}*")
                if p.is_file() and not any(part in ["target", "build", ".git"] for part in p.parts)
            ][:5]
            if similar:
                return f"Error: File '{file_path_str}' not found. Did you mean:\n - " + "\n - ".join(similar)
            return f"Error: File '{file_path_str}' not found in repository {repo_path.name}."

        rel_path = target_file.relative_to(repo_path)
        try:
            with open(target_file, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
        except Exception as e:
            return f"Error reading file {rel_path}: {e}"

        total_lines = len(lines)
        start_idx = max(1, start_line)
        end_idx = min(total_lines, max(start_idx, end_line))

        output = [f"=== File: {rel_path} (Lines {start_idx}-{end_idx} of {total_lines}) ==="]
        for idx in range(start_idx - 1, end_idx):
            line_no = idx + 1
            line_content = lines[idx].rstrip("\r\n")
            output.append(f"{line_no:4d} | {line_content}")

        return "\n".join(output)

    @classmethod
    def find_files(
        cls,
        file_pattern: str,
        repo_path: Path,
        max_results: int = 30
    ) -> str:
        if not file_pattern or not file_pattern.strip():
            return "Error: file_pattern parameter is required."

        if not repo_path or not repo_path.exists():
            return f"Error: Repository path '{repo_path}' does not exist on disk."
        repo_path = repo_path.resolve()

        matches: List[str] = []
        for path in repo_path.rglob(file_pattern):
            if any(part.startswith(".") or part in ["target", "build", ".git", "node_modules"] for part in path.parts):
                continue
            try:
                rel = str(path.relative_to(repo_path))
                matches.append(rel)
                if len(matches) >= max_results:
                    break
            except Exception:
                continue

        if not matches:
            return f"No files matching '{file_pattern}' found in {repo_path.name}."

        header = f"=== Found {len(matches)} files matching '{file_pattern}' in {repo_path.name} ===\n"
        return header + "\n".join(f"- {m}" for m in matches)

    @classmethod
    def list_directory(
        cls,
        path_str: str,
        repo_path: Path,
        max_depth: int = 2
    ) -> str:
        if not repo_path or not repo_path.exists():
            return f"Error: Repository path '{repo_path}' does not exist on disk."
        repo_path = repo_path.resolve()

        target_dir = (repo_path / path_str.strip()).resolve() if path_str and path_str.strip() else repo_path.resolve()

        # Guard against traversal outside repo
        try:
            target_dir.relative_to(repo_path.resolve())
        except ValueError:
            return f"Error: Path '{path_str}' is outside repository root."

        if not target_dir.exists() or not target_dir.is_dir():
            return f"Error: Directory '{path_str}' does not exist in repository {repo_path.name}."

        lines: List[str] = []
        rel_root = target_dir.relative_to(repo_path)
        rel_root_str = str(rel_root) if str(rel_root) != "." else "/"

        def _traverse(current_dir: Path, current_depth: int):
            if current_depth > max_depth:
                return
            try:
                entries = sorted(current_dir.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
            except Exception:
                return

            for entry in entries:
                if entry.name.startswith(".") or entry.name in ["target", "build", ".git", "node_modules"]:
                    continue
                rel_entry = entry.relative_to(repo_path)
                indent = "  " * (current_depth - 1)
                if entry.is_dir():
                    lines.append(f"{indent}[DIR]  {rel_entry}/")
                    _traverse(entry, current_depth + 1)
                elif entry.is_file():
                    lines.append(f"{indent}[FILE] {rel_entry}")

        _traverse(target_dir, 1)

        if not lines:
            return f"=== Directory: {rel_root_str} (Empty or all entries ignored) ==="

        max_lines = 100
        if len(lines) > max_lines:
            truncated_count = len(lines) - max_lines
            lines = lines[:max_lines]
            lines.append(f"... ({truncated_count} more entries truncated)")

        header = f"=== Directory Listing: {rel_root_str} (max depth: {max_depth}) ===\n"
        return header + "\n".join(lines)
