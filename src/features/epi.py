# src/features/epi.py
import math, yaml
from pathlib import Path
from src.features.reading import normalize_kana, to_mora

# ---- 設定 ---------------------------------------------------------------
def _load_weights():
    with open(Path("configs/weights.yaml"), "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

W = _load_weights()
LEN_SIGMA = float(W.get("final_params", {}).get("delta", 1.0))

# ---- 個別指標 -----------------------------------------------------------
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
    specials = {"ン", "ッ"}
    open_ratio = sum(1 for m in mora_list if m not in specials) / M
    return max(0.0, min(1.0, 1.0 - open_ratio))

def f_sp(mora_list) -> float:
    """特殊モーラ比（ン・ッの比率）"""
    M = len(mora_list) or 1
    specials = {"ン", "ッ"}
    return sum(1 for m in mora_list if m in specials) / M

def f_yoon(mora_list) -> float:
    """拗音比（「キャ」「シュ」等：1文字でないモーラを拗音とみなすMVP）"""
    M = len(mora_list) or 1
    return sum(1 for m in mora_list if len(m) > 1) / M

# ---- 合成EPI ------------------------------------------------------------
def epi_weighted(mora_list) -> float:
    """
    EPIの合成スコア（0=良い ～ 1=悪い）。
    configs/weights.yaml の epi_weights にあるキーのみを合成に使用。
    """
    w = W.get("epi_weights", {})
    m = len(mora_list)
    parts = {
        "f_len": f_len(m),
        "f_open": f_open(mora_list),
        "f_sp": f_sp(mora_list),
        "f_yoon": f_yoon(mora_list),
    }
    num = sum(w.get(k, 0.0) * parts[k] for k in parts)
    den = sum(w.get(k, 0.0) for k in parts)
    return num / den if den > 0 else 0.0

def evaluate_name(name: str) -> dict:
    """文字列から正規化→モーラ分割→各指標→合成EPIまで"""
    kana = normalize_kana(name)
    mora = to_mora(kana)
    return {
        "name": name, "kana": kana, "mora": mora, "M": len(mora),
        "f_len": f_len(len(mora)), "f_open": f_open(mora),
        "f_sp": f_sp(mora), "f_yoon": f_yoon(mora),
        "EPI": epi_weighted(mora),
    }

# --- Backward compatibility shim --------------------------------------------
def epi_from_name(name: str) -> dict:
    """旧API互換。従来のテストが import しても動くようにする。"""
    return evaluate_name(name)

# --- Backward compatibility shim --------------------------------------------
def epi_from_name(name: str) -> dict:
    """旧API互換。従来のテストが import しても動くようにする。"""
    return evaluate_name(name)
