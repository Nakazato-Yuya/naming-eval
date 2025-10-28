# -*- coding: utf-8 -*-
import pytest
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

    # 特殊モーラ比は r2 > r1 を期待
    assert f_sp_2 > f_sp_1
    # 拗音比は r3 >= r1 を期待（同等可）
    assert f_yoon_3 >= f_yoon_1
