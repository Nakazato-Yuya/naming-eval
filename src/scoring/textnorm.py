import re
import unicodedata

KATAKANA_RANGE = r'\u30A0-\u30FF'  # カタカナ全域（長音含む）

def to_katakana(s: str) -> str:
    # NFKC → ひらがな→カタカナ
    s = unicodedata.normalize('NFKC', s)
    # ひらがな→カタカナ（Unicode 差分のトリック）
    s = ''.join(chr(ord(ch) + 0x60) if 'ぁ' <= ch <= 'ゖ' else ch for ch in s)
    # 許可：カタカナ全域（長音 ー を含む）
    s = re.sub(fr'[^{KATAKANA_RANGE}]', '', s)
    # 小書きカナの扱いはモーラ分割側で行う
    return s
