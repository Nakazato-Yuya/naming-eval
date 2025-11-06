# -*- coding: utf-8 -*-
from src.scoring.features import extract_features

def test_mora_count_long_vowel():
    f = extract_features('コーーラ')  # こ + ー + ー + ら
    assert f['f_len'] == 4.0
    assert f['f_sp'] == 2.0 / 4.0
    assert f['f_open'] == 1.0
    assert f['f_yoon'] == 0.0
