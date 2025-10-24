from src.features.epi import f_len, f_open, epi_from_name

def test_f_len_range_zero():
    assert f_len(2) == 0.0 and f_len(3) == 0.0 and f_len(4) == 0.0

def test_f_len_outside_positive():
    assert f_len(1) > 0.0
    assert f_len(6) >= f_len(5) >= 0.0

def test_f_open_basic():
    res = epi_from_name("サクラ")
    assert res["f_open"] == 0.0

def test_f_open_specials():
    res = epi_from_name("シンブン")  # ["シ","ン","ブ","ン"] → 開音節2/4
    assert abs(res["f_open"] - 0.5) < 1e-6

def test_epi_pipeline_fields():
    r = epi_from_name("キャミ")
    for k in ["name","kana","mora","M","f_len","f_open"]:
        assert k in r
    assert r["M"] == len(r["mora"])
