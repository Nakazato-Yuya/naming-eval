import math
import jaconv
import unicodedata

# ---------------------------------------------------------
# 定数・設定 (Plane: 汎用標準モデル)
# ---------------------------------------------------------
WEIGHTS = {
    "f_len": 0.20,      # 長さ
    "f_open": 0.20,     # 開放感
    "f_sp": 0.15,       # 特殊音
    "f_yoon": 0.15,     # 拗音
    "f_voiced": 0.15,   # 濁音
    "f_semi": 0.00,     # 半濁音
    "f_vowel": 0.10,    # 母音多様性
    "f_density": 0.05   # 密度
}
LEN_SIGMA = 1.2

# 定義セット
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
    if base in "アイカサタナハマヤラワガザダバパ":
        return "ア"
    if base in "イキシチニヒミリギジヂビピ":
        return "イ"
    if base in "ウクスツヌフムユルグズヅブプ":
        return "ウ"
    if base in "エケセテネヘメレゲゼデベペ":
        return "エ"
    if base in "オコソトノホモヨロヲゴゾドボポ":
        return "オ"
    return None


def analyze_mora_phoneme(kana):
    moras, p_counts, vowels = [], [], []
    i = 0
    while i < len(kana):
        ch = kana[i]
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

    # エラー回避: 0モーラの場合もキーを含めて返す
    if M == 0:
        return {k: 0.0 for k in WEIGHTS.keys()} | {"EPI_Score": 0.0, "M": 0, "kana": kana}

    # 長さスコア
    low, high = 2, 4
    if low <= M <= high:
        d = 0.0
    elif M < low:
        d = low - M
    else:
        d = M - high
    val_len = _clamp01(1.0 - math.exp(-(d * d) / (2 * LEN_SIGMA * LEN_SIGMA)))

    # 各種指標計算
    open_count = sum(1 for m in moras if m not in SPECIALS_NO_VOWEL)
    val_open = open_count / M

    sp_count = sum(1 for m in moras if m in SPECIALS_ALL)
    val_sp = sp_count / M

    yoon_count = sum(1 for m in moras if len(m) > 1)
    val_yoon = yoon_count / M

    voiced_count = sum(1 for ch in kana if ch in VOICED_CHARS)
    val_voiced = voiced_count / len(kana) if len(kana) > 0 else 0

    unique_vowels = set([v for v in mora_vowels if v is not None])
    val_vowel = len(unique_vowels) / M if M > 0 else 0

    avg_phoneme = sum(p_counts) / M
    val_density = _clamp01(((avg_phoneme - 1.0) / 2.0))

    # 総合スコア
    score = (
        WEIGHTS["f_len"] * val_len +
        WEIGHTS["f_open"] * val_open +
        WEIGHTS["f_sp"] * (1.0 - val_sp) +
        WEIGHTS["f_yoon"] * (1.0 - val_yoon) +
        WEIGHTS["f_voiced"] * (1.0 - val_voiced) +
        WEIGHTS["f_vowel"] * (1.0 - val_vowel) +
        WEIGHTS["f_density"] * (1.0 - val_density)
    )

    # ★修正ポイント: ここで "kana" と "M" を辞書に含める
    return {
        "EPI_Score": score,
        "M": M,
        "kana": kana,
        "f_len": val_len,
        "f_open": val_open,
        "f_sp": 1.0 - val_sp,
        "f_yoon": 1.0 - val_yoon,
        "f_voiced": 1.0 - val_voiced,
        "f_vowel": val_vowel,
        "f_density": 1.0 - val_density
    }