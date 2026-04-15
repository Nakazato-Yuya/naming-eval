# -*- coding: utf-8 -*-
"""
tests/test_phonology.py

src/features/phonology.py の出力契約・数式・回帰テスト（28ケース）
"""
from __future__ import annotations

import math
import pytest

from src.features.phonology import (
    a_len, evaluate_phonology,
    is_generic,
)

# ================================================
# グループ1: a_len 数式検証
# ================================================

def test_a_len_optimal_is_1():
    """最適モーラ数 (2〜4) では 1.0 を返す"""
    assert a_len(2) == pytest.approx(1.0)
    assert a_len(3) == pytest.approx(1.0)
    assert a_len(4) == pytest.approx(1.0)


def test_a_len_outside_gaussian():
    """最適範囲外は d=|M-境界| のガウス減衰 exp(-d²/2σ²)"""
    sigma = 2.0
    expected_d1 = math.exp(-1.0 / (2 * sigma ** 2))  # d=1: exp(-1/8) ≈ 0.8825
    assert a_len(1) == pytest.approx(expected_d1, rel=1e-6)
    assert a_len(5) == pytest.approx(expected_d1, rel=1e-6)
    # 単調性: 範囲から遠いほど低い
    assert a_len(6) < a_len(5) < a_len(4)


def test_a_len_no_old_bug():
    """
    旧バグ修正の確認: epi_scoring_final_plane.py は 1-exp(-d²/2σ²) を
    使用しておりd=0（最適）のとき 0.0 を返していた。
    新実装では M=3 のとき 1.0（0.9 超）を返す。
    """
    assert a_len(3) > 0.9


# ================================================
# グループ2: a_open / a_sp の長音「ー」除外
# ================================================

def test_a_open_long_vowel_counted():
    """ー（長音）は開音節として扱われ a_open を下げない"""
    r_sony = evaluate_phonology("ソニー")
    r_cola = evaluate_phonology("コーラ")
    assert r_sony["a_open"] == pytest.approx(1.0)
    assert r_cola["a_open"] == pytest.approx(1.0)


def test_a_sp_long_vowel_no_penalty():
    """ー（長音）は a_sp のペナルティ対象外（旧実装の修正確認）"""
    r_sony = evaluate_phonology("ソニー")
    r_cola = evaluate_phonology("コーラ")
    assert r_sony["a_sp"] == pytest.approx(1.0)
    assert r_cola["a_sp"] == pytest.approx(1.0)


def test_a_sp_n_tsu_counted():
    """ッ は a_sp のフルペナルティ対象: ネット [ね,っ,と] → a_sp = 1 - 1.0/3 = 2/3"""
    r = evaluate_phonology("ネット")  # M=3, っ=1個 (重み1.0)
    assert r["a_sp"] == pytest.approx(2.0 / 3.0, rel=1e-6)


def test_a_sp_distinct_from_a_open():
    """ン（撥音）を含む名前では a_sp > a_open（重み差による独立指標）"""
    # ホンダ: ほ(o), ん(None), だ(a) → a_open=2/3, a_sp=1-0.5/3=5/6
    r_honda = evaluate_phonology("ホンダ")
    assert r_honda["a_sp"] > r_honda["a_open"]

    # シンブン: 2ン → a_open=0.5, a_sp=1-1.0/4=0.75
    r_shinbun = evaluate_phonology("シンブン")
    assert r_shinbun["a_sp"] > r_shinbun["a_open"]


def test_a_sp_sokuon_harder_than_n():
    """ッ1個(M=3) の a_sp < ン1個(M=3) の a_sp （ッのほうが発音が難しい）"""
    r_netto  = evaluate_phonology("ネット")   # M=3, ッ1個 → a_sp=2/3≈0.667
    r_honda  = evaluate_phonology("ホンダ")   # M=3, ン1個 → a_sp=5/6≈0.833
    assert r_netto["a_sp"] < r_honda["a_sp"]


# ================================================
# グループ3: a_yoon の方向性
# ================================================

def test_a_yoon_direction():
    """拗音が多いほど a_yoon が下がる"""
    r_pure  = evaluate_phonology("サクラ")   # 拗音なし
    r_yoon  = evaluate_phonology("キャミ")   # 拗音1/2
    assert r_pure["a_yoon"] > r_yoon["a_yoon"]


# ================================================
# グループ4: b_rhythm
# ================================================

def test_b_rhythm_repeat():
    """パナマ [a,a,a]: AAAA型 adj=1.0 → 1.0"""
    r = evaluate_phonology("パナマ")
    assert r["b_rhythm"] == pytest.approx(1.0)


def test_b_rhythm_varied():
    """メルカリ [e,u,a,i]: adj=0, p2=0 → 0.0（パターンなし）"""
    r = evaluate_phonology("メルカリ")
    assert r["b_rhythm"] == pytest.approx(0.0)


def test_b_rhythm_aba_pattern():
    """サクラ [a,u,a]: ABA型（V[0]==V[2]）→ period2=1.0 → b_rhythm=1.0"""
    r = evaluate_phonology("サクラ")
    assert r["b_rhythm"] == pytest.approx(1.0)


def test_b_rhythm_partial_abab():
    """アディダス [a,e,a,u]: V[0]==V[2] だが V[1]!=V[3] → period2=0.5"""
    r = evaluate_phonology("アディダス")
    assert r["b_rhythm"] == pytest.approx(0.5, rel=1e-6)


# ================================================
# グループ5: b_vowel
# ================================================

def test_b_vowel_harmony():
    """パナマ [a,a,a]: 後舌統一 → 3/3 = 1.0"""
    r = evaluate_phonology("パナマ")
    assert r["b_vowel"] == pytest.approx(1.0)


# ================================================
# グループ6: c_sharpness の方向性
# ================================================

def test_c_sharpness_range():
    """c_sharpness は -1〜+1 の範囲に収まる"""
    for name in ["トヨタ", "ソニー", "キキ", "ボボ", "メルカリ"]:
        r = evaluate_phonology(name)
        assert -1.0 <= r["c_sharpness"] <= 1.0, f"{name}: {r['c_sharpness']}"


def test_c_sharpness_direction():
    """前舌母音（イ・エ）優位 → 正値、後舌母音（ウ・オ・ア）優位 → 負値"""
    r_kiki = evaluate_phonology("キキ")   # i,i → +1.0
    r_bobo = evaluate_phonology("ボボ")   # o,o → -1.0
    r_toyo = evaluate_phonology("トヨタ")  # o,o,a → 後舌優位 → 負
    assert r_kiki["c_sharpness"] > 0
    assert r_bobo["c_sharpness"] < 0
    assert r_toyo["c_sharpness"] < 0


# ================================================
# グループ7: 出力契約（CLAUDE.md 準拠）
# ================================================

_NAMES_FOR_CONTRACT = ["トヨタ", "キャラメル", "シンブン", "パナソニック", "コーラ"]
_KEYS_01 = [
    "a_len", "a_open", "a_sp", "a_yoon", "axis_a",
    "b_rhythm", "b_vowel", "axis_b",
    "c_strength", "c_fluency",
]


def test_output_contract_raw_range():
    """CLAUDE.md 出力契約: raw=[0,1]（c_sharpness のみ [-1,1]）"""
    for name in _NAMES_FOR_CONTRACT:
        r = evaluate_phonology(name)
        for k in _KEYS_01:
            assert 0.0 <= r[k] <= 1.0, f"{k} out of [0,1] for '{name}': {r[k]}"
        assert -1.0 <= r["c_sharpness"] <= 1.0


def test_output_contract_display():
    """CLAUDE.md 出力契約: display=[0,100]"""
    r = evaluate_phonology("メルカリ")
    assert 0 <= r["axis_a_display"] <= 100
    assert 0 <= r["axis_b_display"] <= 100


def test_output_contract_drivers():
    """CLAUDE.md 出力契約: Drivers 必須キー M と mora_str が存在する"""
    r = evaluate_phonology("キャラメル")
    assert "M" in r and isinstance(r["M"], int) and r["M"] > 0
    assert "mora_str" in r and "|" in r["mora_str"]


# ================================================
# グループ8: 回帰テスト
# ================================================

def test_regression_korara():
    """コーーラ: M=4, a_open=1.0, a_sp=1.0（ー2個はペナルティなし）"""
    r = evaluate_phonology("コーーラ")
    assert r["M"] == 4
    assert r["a_open"] == pytest.approx(1.0)
    assert r["a_sp"]   == pytest.approx(1.0)


def test_regression_good_brands_axis_a():
    """優良ブランド名（短・開音節）は axis_a >= 0.9 を期待"""
    for name in ["トヨタ", "ソニー", "コーラ", "サクラ"]:
        r = evaluate_phonology(name)
        assert r["axis_a"] >= 0.9, f"'{name}': axis_a={r['axis_a']:.3f}"


# ================================================
# グループ9: is_generic 汎用語フラグ
# ================================================

def test_is_generic_detects_common_words():
    """汎用語リスト内の名前は True を返す"""
    for name in ["システム", "サービス", "グループ", "テクノロジー", "デザイン"]:
        assert is_generic(name) is True, f"'{name}' should be generic"


def test_is_generic_passes_brand_names():
    """固有ブランド名（汎用語でない）は False を返す"""
    for name in ["トヨタ", "ソニー", "メルカリ", "サクラ", "パナマ", "キキ"]:
        assert is_generic(name) is False, f"'{name}' should not be generic"


def test_is_generic_result_in_evaluate_phonology():
    """evaluate_phonology の戻り値に is_generic キーが存在する"""
    r_generic = evaluate_phonology("システム")
    r_brand   = evaluate_phonology("トヨタ")
    assert "is_generic" in r_generic
    assert r_generic["is_generic"] is True
    assert r_brand["is_generic"] is False


def test_is_generic_hiragana_input():
    """ひらがな入力でも汎用語判定が動作する"""
    assert is_generic("しすてむ") is True
    assert is_generic("とよた") is False


# ================================================
# グループ10: 拗音母音の回帰テスト（旧バグ修正確認）
# ================================================

def test_yoon_vowel_is_small_kana():
    """
    拗音の母音は小書き文字（ょ/ゅ/ゃ）で決まる。
    旧バグ: 先頭文字（し→i）で決めていたため しょ=i と誤判定していた。
    正しくは しょ→ょ→o, じょ→ょ→o, きゃ→ゃ→a, ちゅ→ゅ→u。
    """
    from src.scoring.features import kana_to_moras, to_hira

    # しょ の母音は o（ょ由来）、i ではない
    moras_sho = kana_to_moras(to_hira("ショ"))
    assert moras_sho[0].vowel == "o", f"しょ の母音が {moras_sho[0].vowel!r}（期待: 'o'）"

    # じょ の母音も o
    moras_jo = kana_to_moras(to_hira("ジョ"))
    assert moras_jo[0].vowel == "o"

    # きゃ → a
    moras_kya = kana_to_moras(to_hira("キャ"))
    assert moras_kya[0].vowel == "a"

    # ちゅ → u
    moras_chu = kana_to_moras(to_hira("チュ"))
    assert moras_chu[0].vowel == "u"


def test_yoon_vowel_affects_c_sharpness():
    """
    拗音母音修正後、ショウジョ（しょ・う・じょ）は後舌母音優位 → c_sharpness < 0。
    旧バグでは しょ=i（前舌）と誤判定し正値になっていた。
    """
    r = evaluate_phonology("ショウジョ")
    # しょ(o), う(u), じょ(o): 後舌3/3 → c_sharpness = -1.0
    assert r["c_sharpness"] < 0, f"ショウジョ c_sharpness={r['c_sharpness']:.3f}（期待: < 0）"


def test_empty_result_has_is_generic():
    """空文字・変換不能入力でも is_generic キーが存在する"""
    for name in ["", "   ", "TOYOTA", "123"]:
        r = evaluate_phonology(name)
        assert "is_generic" in r, f"{name!r} に is_generic キーなし"
        assert r["is_generic"] is False
