import re
import jaconv
import yaml
from pathlib import Path

# 設定読み込み（正規化ルール）
def load_norm():
    with open(Path("configs/normalization.yaml"), "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

# 1) 正規化：カタカナ/長音/外来音ゆれ の整理
def normalize_kana(name: str, norm=None) -> str:
    norm = norm or load_norm()
    # 全角・結合文字などを正規化 → ひらがな → カタカナ
    s = jaconv.hira2kata(jaconv.normalize(name))
    # 長音の扱い（例：カー→カア）
    if norm.get("long_vowel") == "repeat_prev_vowel":
        s = re.sub(r"([アイウエオ])ー", r"\1\1", s)
    # 外来音の表記ゆれをmapで置換
    for k, v in norm.get("foreign_map", {}).items():
        s = s.replace(k, v)
    return s

# 2) 簡易モーラ分割（MVP：拗音は1モーラとして扱う）
_YOON = set("ャュョァィゥェォヮ")
_SOKUON = "ッ"

def to_mora(kana: str, norm=None):
    norm = norm or load_norm()
    res = []
    i = 0
    while i < len(kana):
        ch = kana[i]
        # 促音（ッ）は独立モーラ
        if ch == _SOKUON:
            res.append(ch)
            i += 1
            continue
        # 拗音は直前と結合して1モーラ扱い
        if i + 1 < len(kana) and kana[i+1] in _YOON and norm.get("yoon_as_single_mora", True):
            res.append(kana[i] + kana[i+1])
            i += 2
            continue
        # 通常
        res.append(ch)
        i += 1
    return res

# 3) ざっくりCV化（MVP）
_VOWELS = "アイウエオ"

def kana_to_cv(mora_list):
    cv = []
    for m in mora_list:
        # 促音・撥音のような特殊モーラはそのまま記録
        if m in ("ン", "ッ"):
            cv.append(("∅", m))
            continue
        # 最終文字が母音ならそれをVに
        v = m[-1] if m[-1] in _VOWELS else "∅"
        # 先頭が母音でなければ「仮の子音」を置く（MVPではカナ1文字目）
        c = "∅"
        if len(m) >= 1 and m[0] not in _VOWELS:
            c = m[0]
        cv.append((c, v))
    return cv
