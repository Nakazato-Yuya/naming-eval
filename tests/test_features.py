# tests/test_features.py
# -*- coding: utf-8 -*-
import math
from src.scoring.features import extract_features

def test_mora_count_long_vowel():
    # 「コーーラ」= モーラ列: コ | ー | ー | ラ → M=4
    f = extract_features("コーーラ")

    # 生のモーラ数は _M で確認
    assert int(f["_M"]) == 4

    # f_len は 0..1 に正規化（短いほど1）
    # 仕様: f_len = 1 - (M - 2) / (9 - 2) （M<=2で1, M>=9で0の線形）
    expected_f_len = 1.0 - (4 - 2) / (9 - 2)  # = 1 - 2/7
    assert math.isclose(f["f_len"], expected_f_len, rel_tol=1e-9)

    # 特殊モーラ（ー/っ/ん）: 「コーーラ」では ー が2つ → n_special=2
    # f_sp は「少ないほど1」なので 1 - (2/4) = 0.5
    assert math.isclose(f["f_sp"], 1.0 - (2.0 / 4.0), rel_tol=1e-9)

    # f_open は「母音を持つモーラ比」（ーも母音持ちとして数える）→ 全4/4で 1.0
    assert math.isclose(f["f_open"], 1.0, rel_tol=1e-9)

    # 拗音（ゃゅょ等）は無し → 割合0、f_yoon は 1 - 0 = 1.0
    assert math.isclose(f["f_yoon"], 1.0, rel_tol=1e-9)
