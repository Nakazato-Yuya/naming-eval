from src.features.epi import evaluate_name, epi_weighted, to_mora, normalize_kana

def test_epi_weight_basic_good():
    # サクラはCV中心 → EPI（ペナルティ）は低いはず
    r = evaluate_name("サクラ")
    assert 0.0 <= r["EPI"] <= 0.3

def test_epi_weight_specials_higher():
    # シンブンは撥音が多い → f_open↑ → 合成EPIも相対的に高い
    r1 = evaluate_name("サクラ")
    r2 = evaluate_name("シンブン")
    assert r2["EPI"] >= r1["EPI"]

def test_epi_weight_uses_config_weights():
    kana = normalize_kana("サクラ")
    mora = to_mora(kana)
    e = epi_weighted(mora)
    assert 0.0 <= e <= 1.0
