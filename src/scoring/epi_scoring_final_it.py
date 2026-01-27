import math
import jaconv
import unicodedata

# ---------------------------------------------------------
# 定数・設定 (IT Special: 情報・通信特化)
# ---------------------------------------------------------
SPECIALS_ALL = {"ン", "ッ", "ー"}
SPECIALS_NO_VOWEL = {"ン", "ッ"} 

VOICED_CHARS = set("ガギグゲゴザジズゼゾダヂヅデドバビブベボ")
SEMI_VOICED_CHARS = set("パピプペポ")
ALL_VOICED = VOICED_CHARS | SEMI_VOICED_CHARS

SMALL_Y = set("ャュョ")
SMALL_VOWELS = set("ァィゥェォヮ")
ALL_SMALL = SMALL_Y | SMALL_VOWELS

VOWELS = set("アイウエオ")

# ★ IT業界特化の重み設定 ★
# 情報・通信系は「濁音（力強さ）」「閉音節（Tech, Net）」が多いため、
# それらを減点せず、逆に「長さ（冗長性）」を厳しくチェックする。
WEIGHTS = {
    "f_len": 0.35,      # 【強化】複合語になりやすいため、短さを最重要視
    "f_open": 0.05,     # 【緩和】「ネット」「コム」などは閉音節なので許容
    "f_sp": 0.05,       # 【緩和】「システム(ン)」「ネットワーク(ッ)」などを許容
    "f_yoon": 0.05,     # 【緩和】「ソリューション」などの拗音を許容
    "f_voiced": 0.00,   # 【無効化】「ギガ」「デジ」など濁音はペナルティなし
    "f_vowel": 0.10,    # 維持
    "f_density": 0.40   # 【強化】専門用語でも「言いやすさ」を担保するため厳しく見る
}
LEN_SIGMA = 1.0

# ---------------------------------------------------------
# 内部ヘルパー関数 (共通)
# ---------------------------------------------------------
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

def _clamp01(x: float) -> float:
    return 0.0 if x < 0.0 else 1.0 if x > 1.0 else x

def normalize_kana(name: str) -> str:
    if not isinstance(name, str):
        return ""
    return jaconv.hira2kata(jaconv.normalize(name))

def analyze_mora_phoneme(kana: str):
    moras = []
    phoneme_counts = []
    vowels = []
    i = 0
    while i < len(kana):
        ch = kana[i]
        if ch in ["ッ", "ン", "ー"]:
            moras.append(ch)
            phoneme_counts.append(1)
            vowels.append(None)
            i += 1
            continue
        if i + 1 < len(kana) and kana[i+1] in ALL_SMALL:
            mora_str = ch + kana[i+1]
            moras.append(mora_str)
            phoneme_counts.append(3) 
            vowels.append(_get_vowel(kana[i+1]))
            i += 2
            continue
        moras.append(ch)
        p_count = 1 if ch in VOWELS else 2
        phoneme_counts.append(p_count)
        vowels.append(_get_vowel(ch))
        i += 1
    return moras, phoneme_counts, vowels

# ---------------------------------------------------------
# 計算メインロジック (IT Special)
# ---------------------------------------------------------
def calculate_epi_it(name: str) -> dict:
    kana = normalize_kana(name)
    moras, p_counts, mora_vowels = analyze_mora_phoneme(kana)
    M = len(moras)
    
    if M == 0:
        return {k: 0.0 for k in WEIGHTS.keys()} | {"EPI_Score": 0.0, "M": 0}

    # 1. f_len
    low, high = 2, 4
    if low <= M <= high:
        d = 0.0
    elif M < low:
        d = low - M
    else:
        d = M - high
    val_len = _clamp01(1.0 - math.exp(-(d * d) / (2 * LEN_SIGMA * LEN_SIGMA)))

    # 各種指標
    open_count = sum(1 for m in moras if m not in SPECIALS_NO_VOWEL)
    val_open = open_count / M
    
    sp_count = sum(1 for m in moras if m in SPECIALS_ALL)
    val_sp = sp_count / M
    
    yoon_count = sum(1 for m in moras if len(m) > 1)
    val_yoon = yoon_count / M
    
    voiced_char_count = sum(1 for ch in kana if ch in ALL_VOICED)
    val_voiced = voiced_char_count / len(kana) if len(kana) > 0 else 0
    
    unique_vowels = set([v for v in mora_vowels if v is not None])
    val_vowel = len(unique_vowels) / M if M > 0 else 0
    
    avg_phoneme = sum(p_counts) / M
    val_density = _clamp01(((avg_phoneme - 1.0) / 2.0))

    # 総合計算 (IT重み適用)
    score = (
        WEIGHTS["f_len"] * val_len +
        WEIGHTS["f_open"] * val_open +
        WEIGHTS["f_sp"] * (1.0 - val_sp) +
        WEIGHTS["f_yoon"] * (1.0 - val_yoon) +
        # 濁音はペナルティなし(0.0)なので、計算しても0だが形式的に残す
        WEIGHTS["f_voiced"] * (1.0 - val_voiced) + 
        WEIGHTS["f_vowel"] * (1.0 - val_vowel) +
        WEIGHTS["f_density"] * (1.0 - val_density)
    )

    return {
        "EPI_Score": score,
        "Type": "IT_Specialized",
        "M": M,
        "f_len": val_len, "f_open": val_open, "f_sp": val_sp,
        "f_yoon": val_yoon, "f_voiced": val_voiced, "f_vowel": val_vowel,
        "f_density": val_density
    }