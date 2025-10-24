import math, yaml
from pathlib import Path
from src.features.reading import normalize_kana, to_mora

def _load_weights():
    with open(Path("configs/weights.yaml"), "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

W = _load_weights()
LEN_SIGMA = float(W.get("final_params", {}).get("delta", 1.0))

def f_len(mora_count: int, low: int = 2, high: int = 4) -> float:
    if mora_count <= 0:
        return 1.0
    if low <= mora_count <= high:
        d = 0.0
    elif mora_count < low:
        d = low - mora_count
    else:
        d = mora_count - high
    sigma = max(1e-6, LEN_SIGMA)
    return max(0.0, min(1.0, 1.0 - math.exp(-(d*d)/(2*sigma*sigma))))

def f_open(mora_list) -> float:
    M = len(mora_list)
    if M == 0:
        return 1.0
    specials = {"ン","ッ"}
    open_ratio = sum(1 for m in mora_list if m not in specials) / M
    return max(0.0, min(1.0, 1.0 - open_ratio))

def epi_from_name(name: str) -> dict:
    kana = normalize_kana(name)
    mora = to_mora(kana)
    return {
        "name": name, "kana": kana, "mora": mora, "M": len(mora),
        "f_len": f_len(len(mora)), "f_open": f_open(mora),
    }

# ---- 合成EPI（重み付き） -----------------------------------------------------
def epi_weighted(mora_list) -> float:
    """
    EPIの合成スコア（0=良い ～ 1=悪い）。
    現時点では f_len と f_open を weights.yaml の epi_weights で合成。
    将来 f_sp, f_yoon, ... を追加しやすい設計。
    """
    w = W.get("epi_weights", {})
    # 個別スコア
    m = len(mora_list)
    s = {
        "f_len": f_len(m),
        "f_open": f_open(mora_list),
        # ここに将来 f_sp, f_yoon, ... を足す
    }
    # 合成（未定義の重みは0扱い）
    num = sum(w.get(k, 0.0) * s[k] for k in s.keys())
    den = sum(w.get(k, 0.0) for k in s.keys())
    return num / den if den > 0 else 0.0

def evaluate_name(name: str) -> dict:
    """文字列から合成EPIまで一気に返すユーティリティ。"""
    kana = normalize_kana(name)
    mora = to_mora(kana)
    return {
        "name": name,
        "kana": kana,
        "mora": mora,
        "M": len(mora),
        "f_len": f_len(len(mora)),
        "f_open": f_open(mora),
        "EPI": epi_weighted(mora),
    }
