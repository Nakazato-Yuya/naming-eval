import math
import jaconv
import unicodedata

# ---------------------------------------------------------
# 定数・設定 (Plane: 汎用標準モデル)
# ---------------------------------------------------------
WEIGHTS = {
    "f_len": 0.20,
    "f_open": 0.20,
    "f_sp": 0.15,
    "f_yoon": 0.15,
    "f_voiced": 0.15,
    "f_semi": 0.00,
    "f_vowel": 0.10,
    "f_density": 0.05
}
LEN_SIGMA = 1.2

SPECIALS_NO_VOWEL = {"ン", "ッ"}
SPECIALS_ALL = {"ン", "ッ", "ー"}
VOICED_CHARS = set("ガギグゲゴザジズゼゾダヂヅデドバビブベボ")
VOWELS = set("アイウエオ")
SMALL_Y = set("ャュョ")
ALL_SMALL = SMALL_Y | set("ァィゥェォヮ")


def normalize_kana(name):
    if not isinstance(name, str):
        return ""
    return jaconv.hira2kata(jaconv.normalize(name))


def _get_vowel(ch):
    if not ch:
        return None
    base = unicodedata.normalize('NFD', ch)[0]
    vowel_map = {
        "ア": "アイカサタナハマヤラワガザダバパ",
        "イ": "イキシチニヒミリギジヂビピ",
        "ウ": "ウクスツヌフムユルグズヅブプ",
        "エ": "エケセテネヘメレゲゼデベペ",
        "オ": "オコソトノホモヨロヲゴゾドボポ"
    }
    for v, chars in vowel_map.items():
        if base in chars:
            return v
    return None


def analyze_mora_phoneme(kana):
    moras, p_counts, vowels = [], [], []
    i = 0
    while i < len(kana):
        ch = kana[i]
        # セミコロンを削除し、適切な改行に修正
        if ch in ["ッ", "ン", "ー"]:
            moras.append(ch)
            p_counts.append(1)
            vowels.append(None)
            i += 1
            continue
        if i + 1 < len(kana) and kana[i+1] in ALL_SMALL:
            moras.append(ch + kana[i+1])
            p_counts.append(3)
            vowels.append(_get_vowel(kana[i+1]))
            i += 2
            continue
        moras.append(ch)
        p_counts.append(1 if ch in VOWELS else 2)
        vowels.append(_get_vowel(ch))
        i += 1
    return moras, p_counts, vowels


def _clamp01(x):
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


def calculate_epi_plane(name: str) -> dict:
    kana = normalize_kana(name)
    moras, p_counts, mora_vowels = analyze_mora_phoneme(kana)
    M = len(moras)

    if M == 0:
        return {k: 0.0 for k in WEIGHTS.keys()} | {
            "EPI_Score": 0.0,
            "M": 0,
            "kana": kana
        }

    # 長さスコアの算出
    d = 0.0 if 2 <= M <= 4 else (2 - M if M < 2 else M - 4)
    val_len = _clamp01(1.0 - math.exp(-(d * d) / (2 * LEN_SIGMA**2)))

    # 各指標の正規化
    val_open = sum(1 for m in moras if m not in SPECIALS_NO_VOWEL) / M
    val_sp = 1.0 - (sum(1 for m in moras if m in SPECIALS_ALL) / M)
    val_yoon = 1.0 - (sum(1 for m in moras if len(m) > 1) / M)
    val_voiced = 1.0 - (sum(1 for ch in kana if ch in VOICED_CHARS) / len(kana))
    val_vowel = len(set([v for v in mora_vowels if v is not None])) / M
    avg_phoneme = sum(p_counts) / M
    val_density = 1.0 - _clamp01(((avg_phoneme - 1.0) / 2.0))

    # 総合スコアの重み付け合計
    score = (
        WEIGHTS["f_len"] * val_len +
        WEIGHTS["f_open"] * val_open +
        WEIGHTS["f_sp"] * val_sp +
        WEIGHTS["f_yoon"] * val_yoon +
        WEIGHTS["f_voiced"] * val_voiced +
        WEIGHTS["f_vowel"] * val_vowel +
        WEIGHTS["f_density"] * val_density
    )

    return {
        "EPI_Score": score,
        "kana": kana,
        "M": M,
        "f_len": val_len,
        "f_open": val_open,
        "f_sp": val_sp,
        "f_yoon": val_yoon,
        "f_voiced": val_voiced,
        "f_vowel": val_vowel,
        "f_density": val_density
    }