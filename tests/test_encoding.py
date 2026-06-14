"""Cycle 8: dual_agent.py prompts must be clean UTF-8, not double-encoded mojibake.

The Master/Reader/Worker prompts were stored as valid UTF-8 whose *characters* were
the mojibake string (e.g. "KullanÄ±cÄ±" instead of
"Kullanıcı"), wasting tokens and degrading the model's Turkish
comprehension on every planning call. Escapes are used here so this test file is
itself shell/encoding independent.
"""
import pathlib

DUAL_AGENT = pathlib.Path(__file__).resolve().parents[1] / "unitytools" / "core" / "dual_agent.py"


def test_no_bom():
    assert DUAL_AGENT.read_bytes()[:3] != b"\xef\xbb\xbf"


def test_valid_utf8_no_mojibake_markers():
    text = DUAL_AGENT.read_bytes().decode("utf-8")  # raises if not valid utf-8
    assert "Ä±" not in text   # "Ä±" — the classic mojibake of "ı"
    assert "Ã" not in text          # "Ã" — mojibake lead byte
    assert "�" not in text          # no lost/replacement chars


def test_correct_turkish_present():
    text = DUAL_AGENT.read_text(encoding="utf-8")
    assert "Kullanıcı" in text   # "Kullanıcı"
    assert "Geçmiş" in text       # "Geçmiş"
    assert "ağaç" in text         # "ağaç"
