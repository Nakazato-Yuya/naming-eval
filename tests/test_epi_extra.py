from src.features.epi import evaluate_name

def test_sp_yoon_behave():
    r1 = evaluate_name("サクラ")      # 特殊/拗音ほぼ無し
    r2 = evaluate_name("シンブン")    # 特殊↑
    r3 = evaluate_name("キャミ")      # 拗音↑
    assert r2["f_sp"] > r1["f_sp"]
    assert r3["f_yoon"] >= r1["f_yoon"]
