"""P3 kernel (cycle 4): weak-point inference normalizes metric scale + direction.

Before this, _infer_weak_points summed raw metric values, so fps_average (~90) was
never the smallest and a good fun_score (~7) was wrongly flagged as 'weakest'.
Now each metric is normalized to a 0..1 goodness before ranking.
"""
from unitytools.core.game_studio_kernel import _infer_weak_points, _metric_goodness


def test_goodness_scales_and_clamps():
    assert _metric_goodness("fun_score", 10) == 1.0
    assert _metric_goodness("fun_score", 5) == 0.5
    assert _metric_goodness("fps_average", 60) == 1.0
    assert _metric_goodness("fps_average", 30) == 0.5
    assert _metric_goodness("fps_average", 120) == 1.0  # clamped, not 2.0
    assert _metric_goodness("fun_score", -3) == 0.0     # clamped low


def test_low_fps_outranks_high_fun_as_weak():
    # fun 9/10 (goodness .9) is GOOD; fps 30/60 (goodness .5) is the real weak point.
    weak = _infer_weak_points([{"metrics": {"fun_score": 9, "fps_average": 30}}], focus="fun")
    assert weak[0] == "fps", weak
    # old (buggy) logic would have ranked fun(9) below fps(30) and flagged fun.


def test_genuinely_low_fun_is_flagged():
    weak = _infer_weak_points([{"metrics": {"fun_score": 2, "fps_average": 58}}], focus="fun")
    assert weak[0] == "fun", weak


def test_high_fps_does_not_dominate():
    weak = _infer_weak_points([{"metrics": {"fps_average": 120, "fun_score": 1}}], focus="fun")
    assert weak[0] == "fun", weak  # fps clamps to 1.0 goodness, fun 0.1 is weakest


def test_averages_per_metric_presence():
    rows = [
        {"metrics": {"fun_score": 8, "fps_average": 30}},
        {"metrics": {"fun_score": 8}},  # no fps here
    ]
    weak = _infer_weak_points(rows, focus="fps")
    # fps present once (goodness .5) vs fun twice (goodness .8) -> fps weaker
    assert weak[0] == "fps", weak


def test_empty_and_no_metrics_defaults():
    assert _infer_weak_points([], focus="fun")[0] == "fun"
    assert _infer_weak_points([{"metrics": {"notes": ["nice"]}}], focus="clarity")[0] == "clarity"
