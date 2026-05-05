"""Semantic asset search smoke tests with a fake Unity bridge."""
from __future__ import annotations

import unitytools.tools.asset_tools as asset_tools


class FakeUnity:
    def is_connected(self):
        return True

    def call(self, method, params=None, timeout=None):
        params = params or {}
        if method != "find_assets":
            raise AssertionError(f"unexpected method: {method}")
        query = (params.get("query") or "").lower()
        rows = [
            {
                "guid": "tree-1",
                "path": "Assets/FantasyRPG/Models/PolyHaven/Nature/Trees/Nature_Trees_04_PineTree.glb",
                "main_type": "GameObject",
            },
            {
                "guid": "rock-1",
                "path": "Assets/FantasyRPG/Models/PolyHaven/Nature/Rocks/Nature_Rocks_01_Boulder1.glb",
                "main_type": "GameObject",
            },
            {
                "guid": "mat-1",
                "path": "Assets/FantasyRPG/Generated/Materials/HDRP_M_WetRock.mat",
                "main_type": "Material",
            },
        ]
        hits = [row for row in rows if query in row["path"].lower()]
        if query in {"tree", "pine", "forest", "real relis realist tree"}:
            hits = [rows[0]]
        if query in {"rock", "boulder", "stone"}:
            hits = [rows[1], rows[2]]
        return {"ok": True, "query": query, "count": len(hits), "results": hits}


def run_test():
    old_unity = asset_tools._UNITY
    asset_tools._UNITY = FakeUnity()
    try:
        result = asset_tools.unity_search_assets_semantic(
            "real relis realist tree",
            max_results=5,
            instantiable_only=True,
        )
        assert result["ok"] is True
        assert result["category"] == "tree"
        assert result["count"] >= 1
        assert "PineTree.glb" in result["results"][0]["path"]
        print("OK semantic tree typo search")

        result = asset_tools.unity_find_rock_assets(max_results=5)
        assert result["ok"] is True
        assert any("Boulder1.glb" in item["path"] for item in result["results"])
        print("OK rock category search")
    finally:
        asset_tools._UNITY = old_unity


if __name__ == "__main__":
    run_test()
