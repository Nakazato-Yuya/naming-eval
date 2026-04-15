# Naming-Eval
![CI](https://github.com/Nakazato-Yuya/naming-eval/actions/workflows/ci.yml/badge.svg)

Japanese brand naming evaluator — 3-axis phonology framework.

## 3軸フレームワーク

| 軸 | 概要 | 指標 |
|---|---|---|
| **A軸 発音容易性** | 短く・開音節・特殊音なし | `a_len`, `a_open`, `a_sp`, `a_yoon` → `axis_a` |
| **B軸 音韻パターン性** | リズム規則性・母音調和（音韻パターンの強さ） | `b_rhythm`, `b_vowel` → `axis_b` |
| **C軸 印象・方向性** | 参考指標（合計スコアに含まず）| `c_strength`, `c_sharpness`, `c_fluency` |

スコアはすべて品質型（高=良い, raw=[0,1]）。`c_sharpness` のみ [-1,+1]。

> **スコープ**: 音韻のみを評価します。意味・独自性・商標的差別化は評価対象外です。
> 汎用語（「システム」「サービス」等）は音韻的には高スコアを得ることがありますが、
> ブランド名としての適切性は別途判断が必要です。`is_generic()` で汎用語判定が可能です。

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest -q
```

## Quick Run

**UI（3軸レイアウト）**:
```bash
PYTHONPATH=. streamlit run app/app.py
```

**CLI バッチ評価**（デフォルトパス）:
```bash
python -m src.scoring.batch_eval
```

カスタム重みを指定:
```bash
python -m src.scoring.batch_eval data/processed/brand_names.csv reports/brand_eval.csv \
  --a-len 0.35 --a-open 0.30 --a-sp 0.20 --a-yoon 0.15 \
  --b-rhythm 0.50 --b-vowel 0.50 \
  --axis-a-weight 0.70 --axis-b-weight 0.30
```

旧オプション（後方互換エイリアス）:
```bash
python -m src.scoring.batch_eval --w-len 0.35 --w-open 0.30 --w-sp 0.20 --w-yoon 0.15
```

### Smoke test
```bash
python -m src.scoring.batch_eval && head -n 3 reports/sample_eval.csv
# → axis_a / axis_b 列が存在し、値が [0,1] の範囲内であること
```

**Env**: Python 3.12 / macOS ARM 動作確認済み  
**Tip**: Streamlit は `pip install watchdog` でホットリロード快適。
