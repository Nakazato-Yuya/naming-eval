from src.features.epi import evaluate_name, epi_weighted, to_mora, normalize_kana

def test_epi_weight_basic_good():
    # サクラはCV中心 → 発音しやすい → 品質型スコアは高い（旧ペナルティ型とは逆）
    r = evaluate_name("サクラ")
    assert 0.7 <= r["EPI"] <= 1.0

def test_epi_weight_specials_higher():
    # サクラ（発音しやすい）> シンブン（ンが多く発音しにくい）
    r1 = evaluate_name("サクラ")
    r2 = evaluate_name("シンブン")
    assert r1["EPI"] >= r2["EPI"]

def test_epi_weight_uses_config_weights():
    # kana 引数をオプション化したため1引数で呼び出せる（旧バグ修正）
    kana = normalize_kana("サクラ")
    mora = to_mora(kana)
    e = epi_weighted(mora)
    assert 0.0 <= e <= 1.0
