"""P3 learning: cross-session memory recall (write -> 'restart' -> recall).

Guards the central 'learns across sessions' goal: before the _load_long_term fix,
long_term_memory.jsonl was write-only and a fresh MemorySystem recalled nothing.
"""
import time

from unitytools.core.memory_system import MemorySystem, MemoryEntry


def _entry(request, success=True, lessons=None, ts=None):
    return MemoryEntry(
        timestamp=ts if ts is not None else time.time(),
        request=request,
        plan={"goal": request},
        execution={},
        success=success,
        duration=1.0,
        tools_used=["unity_create_primitive"],
        errors=([] if success else ["boom"]),
        lessons=(lessons or []),
    )


def test_long_term_recall_survives_restart(tmp_path):
    m1 = MemorySystem(storage_path=tmp_path)
    m1.remember(_entry("create a forest of pine trees"))

    # New instance over the SAME storage simulates a process restart.
    m2 = MemorySystem(storage_path=tmp_path)
    assert m2.session_memories == []          # fresh session, nothing in RAM
    assert len(m2.long_term_memories) == 1    # but prior session loaded from disk

    recalled = m2.recall_similar("create a forest", limit=5)
    assert any("forest" in e.request for e in recalled), "cross-session recall failed"


def test_lessons_recalled_across_sessions(tmp_path):
    m1 = MemorySystem(storage_path=tmp_path)
    m1.remember(_entry("build a tall tower", success=False, lessons=["towers need a wide base"]))

    m2 = MemorySystem(storage_path=tmp_path)
    lessons = m2.get_lessons("build a tall tower")
    assert "towers need a wide base" in lessons


def test_recall_does_not_duplicate_session_and_disk(tmp_path):
    m = MemorySystem(storage_path=tmp_path)
    m.remember(_entry("scatter rocks", ts=123.0))
    res = m.recall_similar("scatter rocks")
    assert len([x for x in res if x.request == "scatter rocks"]) == 1


def test_load_reads_all_recent_entries(tmp_path):
    m1 = MemorySystem(storage_path=tmp_path)
    for i in range(5):
        m1.remember(_entry(f"make object {i}"))
    m2 = MemorySystem(storage_path=tmp_path)
    assert len(m2.long_term_memories) == 5
    assert m2.max_long_term_recall >= 5


def test_malformed_lines_are_skipped(tmp_path):
    mfile = tmp_path / "long_term_memory.jsonl"
    mfile.write_text(
        '{"timestamp": 1.0, "request": "good one", "success": true}\n'
        "this is not json\n"
        "\n",
        encoding="utf-8",
    )
    m = MemorySystem(storage_path=tmp_path)
    assert len(m.long_term_memories) == 1
    assert m.long_term_memories[0].request == "good one"


def test_empty_when_no_file(tmp_path):
    m = MemorySystem(storage_path=tmp_path)
    assert m.long_term_memories == []
    assert m.recall_similar("anything") == []
