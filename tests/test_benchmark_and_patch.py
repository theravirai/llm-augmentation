import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from llm_augmentation.benchmark import TaskLoader, RepoManager
from llm_augmentation.evaluation.patch_parser import PatchParser

def test_task_loading():
    loader = TaskLoader()
    tasks = loader.list_tasks()
    assert len(tasks) == 43, f"Expected 43 tasks, got {len(tasks)}"

    gson_tasks = loader.list_tasks(repo_filter="gson")
    assert len(gson_tasks) == 9, f"Expected 9 gson tasks, got {len(gson_tasks)}"

    druid_tasks = loader.list_tasks(repo_filter="druid")
    assert len(druid_tasks) == 5, f"Expected 5 druid tasks, got {len(druid_tasks)}"

    task_gson = loader.get_task("google__gson-2158")
    assert task_gson is not None
    assert task_gson.repo == "google/gson"

    task_druid = loader.get_task("apache__druid-14136")
    assert task_druid is not None
    assert task_druid.repo == "apache/druid"

    print("TaskLoader tests passed!")

def test_patch_parser_gson():
    loader = TaskLoader()
    task = loader.get_task("google__gson-2158")
    assert task is not None

    parsed = PatchParser.parse(task.patch)
    assert "Gson.java" in parsed.file_basenames
    assert "TypeAdapters.java" in parsed.file_basenames

    # Verify classes inferred
    assert "com.google.gson.Gson" in parsed.class_names
    assert "com.google.gson.internal.bind.TypeAdapters" in parsed.class_names

    # Verify method extracted from hunk header
    assert "doubleAdapter" in parsed.method_names

    # Verify line numbers are captured
    assert "Gson.java" in parsed.lines_by_file
    lines_gson = parsed.lines_by_file["Gson.java"]
    assert any(395 <= l <= 405 for l in lines_gson)

    print("PatchParser Gson tests passed!")

def test_patch_parser_druid():
    loader = TaskLoader()
    task = loader.get_task("apache__druid-14136")
    assert task is not None

    parsed = PatchParser.parse(task.patch)
    assert len(parsed.files) == 3, f"Expected 3 files in Druid patch, got {len(parsed.files)}"
    assert "JodaUtils.java" in parsed.file_basenames
    assert "MultipleIntervalSegmentSpec.java" in parsed.file_basenames
    assert "VersionedIntervalTimeline.java" in parsed.file_basenames

    assert "condenseIntervals" in parsed.method_names

    print("PatchParser Druid tests passed!")

def test_repo_manager_gson():
    repo_manager = RepoManager()
    repo_dir = repo_manager.find_repo_dir("google/gson")
    assert repo_dir is not None, "google/gson repo directory should be discovered"

    target_classes = RepoManager.find_target_classes(repo_dir)
    assert len(target_classes) > 0, "google/gson target/classes should exist"
    print(f"RepoManager found Gson classes at: {target_classes}")

if __name__ == "__main__":
    test_task_loading()
    test_patch_parser_gson()
    test_patch_parser_druid()
    test_repo_manager_gson()
    print("\nAll Benchmark & Patch Parser tests passed successfully!")
