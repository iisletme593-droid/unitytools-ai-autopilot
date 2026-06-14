"""P3 (cycle 12): smarter memory recall — IDF-weighted Jaccard over normalized,
stopword-filtered tokens, replacing the raw keyword-overlap count. Pure Python
(no neural embeddings — GPU-free).
"""
import time

from unitytools.core.memory_system import MemorySystem, MemoryEntry, _content_tokens


def _e(request, ts):
    return MemoryEntry(timestamp=ts, request=request, plan={}, execution={},
                       success=True, duration=1.0, tools_used=[])


# --- token helper ----------------------------------------------------------

def test_content_tokens_filters_and_folds():
    toks = _content_tokens("Create a BIG forest with 20 trees")
    assert "forest" in toks and "trees" in toks
    assert "create" not in toks and "a" not in toks and "with" not in toks
    assert "20" not in toks                       # numbers filtered
    # Turkish folds: "ağaç" -> "agac"
    assert _content_tokens("ağaç dizilimi") == {"agac", "dizilimi"}


# --- recall ranking --------------------------------------------------------

def test_ranks_more_similar_first(tmp_path):
    m = MemorySystem(storage_path=tmp_path)
    m.remember(_e("create a pine forest scene", 1.0))
    m.remember(_e("create a desert canyon level", 2.0))
    res = m.recall_similar("a lush pine forest", limit=5)
    assert res and res[0].request == "create a pine forest scene"
    # the unrelated desert entry shares no content token -> excluded
    assert all("desert" not in r.request for r in res)


def test_rare_shared_token_outranks_common_one(tmp_path):
    m = MemorySystem(storage_path=tmp_path)
    for i in range(5):
        m.remember(_e(f"a forest area number {i}", float(i)))   # "forest" common
    m.remember(_e("a spooky dungeon crypt", 10.0))               # "dungeon" rare
    res = m.recall_similar("forest dungeon", limit=10)
    # sharing the rare "dungeon" beats sharing the common "forest"
    assert res[0].request == "a spooky dungeon crypt"


def test_verbs_and_articles_ignored(tmp_path):
    m = MemorySystem(storage_path=tmp_path)
    m.remember(_e("build a tall tower", 1.0))
    # different verb/article, same subject -> still recalled
    res = m.recall_similar("make the tall tower", limit=3)
    assert any("tower" in r.request for r in res)


def test_turkish_normalized_recall(tmp_path):
    m = MemorySystem(storage_path=tmp_path)
    m.remember(_e("ormanda agac dizilimi yap", 1.0))
    res = m.recall_similar("ağaç dizilimi", limit=3)   # ağaç -> agac
    assert any("agac" in r.request for r in res)


def test_empty_and_no_match(tmp_path):
    m = MemorySystem(storage_path=tmp_path)
    assert m.recall_similar("anything") == []
    m.remember(_e("create a forest", 1.0))
    assert m.recall_similar("xyzzy unrelated") == []   # no shared content token
