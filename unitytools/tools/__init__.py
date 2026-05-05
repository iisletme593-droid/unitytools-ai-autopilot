"""Tool kayıtları. Bu modülü import etmek tüm tool'ları registry'e ekler.

Tool fonksiyonları bridge nesnelerine ihtiyaç duyar; bu nedenle
`init_tools(blender, unity)` ile inject edilirler.
"""
from . import blender_tools, unity_tools, pipeline_tools, procedural_tools  # noqa: F401


def init_tools(blender_bridge, unity_bridge) -> None:
    """Tool modüllerine bridge referanslarını inject et."""
    blender_tools._BLENDER = blender_bridge
    unity_tools._UNITY = unity_bridge
    pipeline_tools._BLENDER = blender_bridge
    pipeline_tools._UNITY = unity_bridge
    procedural_tools._UNITY = unity_bridge
