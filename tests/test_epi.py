from src.features.epi import f_len, epi_from_name

def test_f_len_range_zero():
    # 旧実装はペナルティ型（最適=0.0）だったが、品質型（最適=1.0）に変更
    assert f_len(2) == 1.0 and f_len(3) == 1.0 and f_len(4) == 1.0

def test_f_len_outside_positive():
    assert f_len(1) > 0.0
    # 品質型: 最適範囲(2〜4)に近いほどスコアが高い → f_len(5) > f_len(6)
    assert 0.0 < f_len(6) <= f_len(5) < f_len(4)

def test_f_open_basic():
    # 旧実装はペナルティ型（全開音節=0.0）だったが、品質型（全開音節=1.0）に変更
    res = epi_from_name("サクラ")
    assert res["f_open"] == 1.0

def test_f_open_specials():
    res = epi_from_name("シンブン")  # ["シ","ン","ブ","ン"] → 開音節2/4
    assert abs(res["f_open"] - 0.5) < 1e-6

def test_epi_pipeline_fields():
    r = epi_from_name("キャミ")
    for k in ["name","kana","mora","M","f_len","f_open"]:
        assert k in r
    assert r["M"] == len(r["mora"])
