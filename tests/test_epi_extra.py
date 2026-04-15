# -*- coding: utf-8 -*-
from src.features.epi import evaluate_name

def _get(metric: str, d: dict) -> float:
    # evaluate_name の戻りが dict を想定（キーが無ければテスト失敗）
    assert metric in d, f"metric '{metric}' not in result keys={list(d)}"
    val = d[metric]
    assert isinstance(val, (int, float)), f"{metric} must be number: {type(val)}"
    return float(val)

def test_sp_yoon_behave():
    # r1: 拗音・特殊モーラが少ない（基準）
    r1 = evaluate_name("サクラ")
    # r2: 「ン」など特殊モーラが増える
    r2 = evaluate_name("シンブン")
    # r3: 拗音（ャ/ュ/ョなど）が増える
    r3 = evaluate_name("キャミ")

    f_sp_1 = _get("f_sp", r1)
    f_sp_2 = _get("f_sp", r2)
    f_yoon_1 = _get("f_yoon", r1)
    f_yoon_3 = _get("f_yoon", r3)

    # 品質型に変更: 特殊モーラが少ない r1(サクラ) > r2(シンブン)
    assert f_sp_1 > f_sp_2
    # 品質型に変更: 拗音が少ない r1(サクラ) >= r3(キャミ)
    assert f_yoon_1 >= f_yoon_3
