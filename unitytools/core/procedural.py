"""Procedural generation — a deterministic, seedable RNG (P9 step 1).

The studio can already build, assess, vary, and persist games. P9 adds
*reproducible variety*: the same seed always yields the same game, a different
seed a different (but deterministic) one. Crucially this RNG is pure and
deterministic — it hashes the seed and runs splitmix64, with NO use of system
time or a global random source — so seeded plans are byte-for-byte reproducible,
shareable, and unit-testable.
"""
from __future__ import annotations

import hashlib

_U64 = 0xFFFFFFFFFFFFFFFF
_GOLDEN = 0x9E3779B97F4A7C15


def _hash_seed(seed: object) -> int:
    """Map any seed (str/int/anything) to a stable 64-bit integer via SHA-256."""
    digest = hashlib.sha256(str(seed).encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


class SeededRng:
    """A tiny deterministic RNG (splitmix64) seeded by hashing ``seed``.

    Same seed -> same sequence, on every machine, forever. No system time, no
    global state. Methods mirror a subset of ``random``: random/uniform/randint
    (inclusive)/choice/shuffle.
    """

    __slots__ = ("_state",)

    def __init__(self, seed: object):
        self._state = _hash_seed(seed) or _GOLDEN

    def _next(self) -> int:
        self._state = (self._state + _GOLDEN) & _U64
        z = self._state
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & _U64
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & _U64
        return (z ^ (z >> 31)) & _U64

    def random(self) -> float:
        """A float in [0, 1)."""
        return self._next() / 2.0 ** 64

    def uniform(self, low: float, high: float) -> float:
        """A float in [low, high)."""
        return low + (high - low) * self.random()

    def randint(self, low: int, high: int) -> int:
        """An int in [low, high] inclusive (low if low >= high)."""
        if high <= low:
            return low
        return low + int(self.random() * (high - low + 1))

    def choice(self, seq):
        """A deterministic element of a non-empty sequence."""
        if not seq:
            raise IndexError("choice from an empty sequence")
        return seq[self.randint(0, len(seq) - 1)]

    def shuffle(self, items: list) -> list:
        """Return a new deterministically shuffled list (Fisher-Yates)."""
        out = list(items)
        for i in range(len(out) - 1, 0, -1):
            j = self.randint(0, i)
            out[i], out[j] = out[j], out[i]
        return out


def seeded_rng(seed: object) -> SeededRng:
    """Build a deterministic RNG from ``seed`` (string or number)."""
    return SeededRng(seed)
