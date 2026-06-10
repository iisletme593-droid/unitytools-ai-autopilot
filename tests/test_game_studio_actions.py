"""Deterministic GameStudio action planner tests."""

from unitytools.core.game_studio_actions import list_templates, plan_unreal_fast_action, preflight_prompt


def test_templates_are_auditable():
    templates = list_templates()
    assert templates
    arena = next(item for item in templates if item["key"] == "arena_survivor")
    assert arena["safe_prefix"] == "ASV001"
    assert "Arena" in arena["display_name"]
    assert arena["safety_notes"]


def test_generic_prompt_does_not_trigger_arena_template():
    plan = plan_unreal_fast_action("yeni bir orman koy oyunu olustur ve sahneyi duzenle")
    assert plan["ok"] is True
    assert plan["steps"] == []
    assert plan["template"] is None


def test_arena_playable_prompt_builds_safe_steps():
    plan = plan_unreal_fast_action("Arena survivor oynanabilir player pawn kur, runtime state resetle ve 4 enemy spawn et")
    tools = [step["tool"] for step in plan["steps"]]
    assert plan["template"] == "arena_survivor"
    assert "unreal_apply_arena_survivor_runtime_scaffold" in tools
    assert "unreal_reset_arena_survivor_runtime_state" in tools
    assert "unreal_spawn_arena_survivor_player_pawn" in tools
    assert "unreal_spawn_arena_survivor_placeholder_enemies" in tools
    assert all(step["kwargs"].get("prefix", "ASV001") == "ASV001" for step in plan["steps"] if "prefix" in step["kwargs"])


def test_arena_open_uses_template_level():
    plan = plan_unreal_fast_action("Arena prototype ac ve devam et")
    open_steps = [step for step in plan["steps"] if step["tool"] == "unreal_open_level"]
    assert open_steps
    assert open_steps[0]["kwargs"]["level_path"] == "/Game/UnrealTools/Maps/UT_ArenaSurvivor_V001"


def test_preflight_write_fast_action():
    report = preflight_prompt("Arena survivor player pawn kur ve enemy spawn et")
    assert report["route"] == "fast_action"
    assert report["risk"] == "write"
    assert report["template"] == "arena_survivor"
    assert "unreal_spawn_arena_survivor_player_pawn" in report["recommended_tools"]


def test_preflight_read_only_prompt():
    report = preflight_prompt("aktif unreal projedeki assetleri tara ve actorleri listele")
    assert report["route"] == "fast_action"
    assert report["risk"] == "read_only"
    assert "unreal_scan_project" in report["recommended_tools"]


def test_generic_read_only_prompt_builds_inspection_steps():
    plan = plan_unreal_fast_action("aktif unreal projedeki assetleri tara ve actorleri listele")
    tools = [step["tool"] for step in plan["steps"]]
    assert plan["template"] is None
    assert plan["display_name"] == "Unreal Project Inspection"
    assert "unreal_get_project_info" in tools
    assert "unreal_scan_project" in tools
    assert "unreal_list_level_actors" in tools
    assert all(step["write"] is False for step in plan["steps"])


def test_level_list_prompt_uses_level_selection_tool():
    plan = plan_unreal_fast_action("sahneleri listele hangi mapler var")
    tools = [step["tool"] for step in plan["steps"]]
    assert plan["display_name"] == "Unreal Level Selection"
    assert tools == ["unreal_get_project_info", "unreal_list_levels"]
    assert all(step["write"] is False for step in plan["steps"])


def test_level_name_open_prompt_uses_open_by_name():
    plan = plan_unreal_fast_action("Lvl_IntroRoom sahnesini ac")
    step = plan["steps"][0]
    assert step["tool"] == "unreal_open_level_by_name"
    assert step["kwargs"]["name"] == "Lvl_IntroRoom"
    assert step["kwargs"]["remember"] is True
    assert step["write"] is False


def test_scene_workbench_status_prompt_is_read_only():
    plan = plan_unreal_fast_action("sahne durumunu kontrol et ve risk ozetini goster")
    step = plan["steps"][0]
    assert step["tool"] == "unreal_get_scene_workbench_status"
    assert step["kwargs"]["top_n"] == 8
    assert step["write"] is False


def test_asset_list_prompt_does_not_get_misread_as_level_list():
    plan = plan_unreal_fast_action("agac sahne assetlerini listele")
    tools = [step["tool"] for step in plan["steps"]]
    assert "unreal_scan_project" in tools
    assert "unreal_list_levels" not in tools


def test_active_scene_work_prompt_remembers_current_level():
    plan = plan_unreal_fast_action("Bu aktif sahnede calis ve aktif map'i dogrula")
    step = plan["steps"][0]
    assert step["tool"] == "unreal_remember_active_level"
    assert step["write"] is False


def test_selected_actor_prompt_uses_read_only_selection_context():
    plan = plan_unreal_fast_action("secili actorleri oku ve context ozetle")
    step = plan["steps"][0]
    assert step["tool"] == "unreal_list_selected_actors"
    assert step["write"] is False


def test_ai_cleanup_preview_is_dry_run():
    plan = plan_unreal_fast_action("ai placed actors silmeden once onizle")
    step = plan["steps"][0]
    assert step["tool"] == "unreal_cleanup_ai_placed_actors"
    assert step["kwargs"]["dry_run"] is True
    assert step["write"] is False


def test_generic_lighting_prompt_uses_safe_scene_action_with_ascii_turkish():
    plan = plan_unreal_fast_action("aktif sahneye premium isik kamera ve sis ayarla")
    tools = [step["tool"] for step in plan["steps"]]
    assert plan["template"] is None
    assert plan["display_name"] == "Unreal Safe Scene Action"
    assert tools == ["unreal_setup_studio_lighting"]
    assert plan["steps"][0]["kwargs"]["style"] == "premium"


def test_generic_lighting_prompt_uses_safe_scene_action_with_real_turkish():
    prompt = "aktif sahneye premium \u0131\u015f\u0131k kamera ve sis ayarla"
    plan = plan_unreal_fast_action(prompt)
    tools = [step["tool"] for step in plan["steps"]]
    assert tools == ["unreal_setup_studio_lighting"]


def test_generic_blockout_prompt_uses_no_arena_tools():
    plan = plan_unreal_fast_action("yeni level icinde basit harita blockout olustur")
    tools = [step["tool"] for step in plan["steps"]]
    assert "unreal_create_blockout_map" in tools
    assert not any("arena_survivor" in tool for tool in tools)
    assert plan["steps"][0]["kwargs"]["create_new_level"] is True


def test_generic_primitive_prompt_is_prefixed():
    plan = plan_unreal_fast_action("sahneye bir \u006b\u00fc\u0070 ekle")
    assert plan["steps"][0]["tool"] == "unreal_spawn_basic_actor"
    assert plan["steps"][0]["kwargs"]["label"].startswith("UT_Generated_")


def test_generic_palette_prompt_targets_tree_category():
    plan = plan_unreal_fast_action("sahnedeki tum agaclari forest palet ile renklendir")
    assert plan["steps"][0]["tool"] == "unreal_apply_actor_material_palette"
    assert plan["steps"][0]["kwargs"]["category"] == "tree"
    assert plan["steps"][0]["kwargs"]["palette"] == "forest"
    assert plan["steps"][0]["write"] is True


def test_generic_dark_rock_palette_prompt():
    plan = plan_unreal_fast_action("kaya ve taslari dark material ile boya")
    step = plan["steps"][0]
    assert step["tool"] == "unreal_apply_actor_material_palette"
    assert step["kwargs"]["category"] == "rock"
    assert step["kwargs"]["palette"] == "dark"


def test_lod_decimation_prompt_is_read_only_plan():
    plan = plan_unreal_fast_action("sahne cok agir 55m triangle var lod decimation planla")
    tools = [step["tool"] for step in plan["steps"]]
    assert "unreal_plan_scene_lod_decimation" in tools
    assert all(step["write"] is False for step in plan["steps"] if step["tool"] == "unreal_plan_scene_lod_decimation")


def test_explicit_game_level_path_can_be_opened():
    plan = plan_unreal_fast_action("/Game/UnrealTools/Maps/UT_Blockout_Map sahnesini ac")
    assert plan["steps"][0]["tool"] == "unreal_open_level"
    assert plan["steps"][0]["kwargs"]["level_path"] == "/Game/UnrealTools/Maps/UT_Blockout_Map"


def test_tree_asset_placement_prompt_uses_semantic_assets():
    plan = plan_unreal_fast_action("sahneye 12 agac dogal dagit ve forest palet uygula")
    step = plan["steps"][0]
    assert step["tool"] == "unreal_place_semantic_assets"
    assert step["kwargs"]["category"] == "tree"
    assert step["kwargs"]["count"] == 12
    assert step["kwargs"]["palette"] == "forest"
    assert step["kwargs"]["align_to_ground"] is True
    assert step["write"] is True


def test_forest_asset_placement_prompt_mixes_categories():
    plan = plan_unreal_fast_action("orman icin 30 tree rock asset yerlestir")
    step = plan["steps"][0]
    assert step["tool"] == "unreal_place_semantic_assets"
    assert step["kwargs"]["category"] == "forest"
    assert step["kwargs"]["count"] == 30


def test_english_scatter_prompt_uses_semantic_assets():
    plan = plan_unreal_fast_action("scatter 8 rock assets in the current level")
    step = plan["steps"][0]
    assert step["tool"] == "unreal_place_semantic_assets"
    assert step["kwargs"]["category"] == "rock"
    assert step["kwargs"]["count"] == 8
    assert step["kwargs"]["align_to_ground"] is True


def test_ai_placed_cleanup_prompt_is_prefix_safe():
    plan = plan_unreal_fast_action("son koyduklarini temizle ai placed actors kaldir")
    step = plan["steps"][0]
    assert step["tool"] == "unreal_cleanup_ai_placed_actors"
    assert step["kwargs"]["prefix"] == "UT_Placed"
    assert step["write"] is True


def test_ai_placed_list_prompt_is_read_only_prefix_safe():
    plan = plan_unreal_fast_action("ai placed actors listele")
    step = plan["steps"][0]
    assert step["tool"] == "unreal_list_ai_placed_actors"
    assert step["kwargs"]["prefix"] == "UT_Placed"
    assert step["write"] is False


def test_open_world_ground_prepare_prompt_uses_ground_tool():
    plan = plan_unreal_fast_action("open world zemini hazirla hafif fog ve forest ground ayarla")
    step = plan["steps"][0]
    assert step["tool"] == "unreal_prepare_open_world_ground"
    assert step["kwargs"]["style"] == "forest"
    assert step["kwargs"]["scatter_count"] == 0
    assert step["write"] is True


def test_open_world_ground_with_scatter_infers_count():
    plan = plan_unreal_fast_action("orman zemini hazirla 12 agac ve kaya dagit")
    tools = [step["tool"] for step in plan["steps"]]
    assert tools == ["unreal_prepare_open_world_ground"]
    assert plan["steps"][0]["kwargs"]["scatter_count"] == 12


def test_ground_prompt_does_not_duplicate_lighting_or_scatter_steps():
    plan = plan_unreal_fast_action("open world zemini hazirla fog ve 6 agac dagit")
    tools = [step["tool"] for step in plan["steps"]]
    assert tools == ["unreal_prepare_open_world_ground"]
