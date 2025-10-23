from src.features.reading import normalize_kana, to_mora, kana_to_cv

def test_normalize_kana():
    # 長音の展開を許容（設定によってはカー/カアどちらもあり）
    s = normalize_kana("カー")
    assert s in ("カー", "カア")

def test_to_mora_basic():
    m = to_mora("サクラ")
    assert m == ["サ","ク","ラ"]

def test_to_mora_yoon():
    m = to_mora("キャミ")
    # 設定次第で ["キャ","ミ"] or ["キ","ャ","ミ"] を許容
    assert m in (["キャ","ミ"], ["キ","ャ","ミ"])

def test_kana_to_cv():
    cv = kana_to_cv(["サ","ク","ラ"])
    assert len(cv) == 3
