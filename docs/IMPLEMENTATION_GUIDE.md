# IMPLEMENTATION_GUIDE — 実装指針

## 原則
- 特徴量は1箇所に集約（UI/CLIで重複しない）
- I/Oとスコア計算を分離（純関数寄り）
- 出力契約をテストで守る

## 推奨モジュール分割（例）
- src/scoring/features.py：EPI/Meaning/Ortho/Confの要素計算
- src/scoring/scoring.py：合成・最終スコア・Drivers整形
- src/scoring/batch_eval.py：CSV入出力やバッチ実行
- app/：UI層（Streamlit等）

## テスト（必須）
- mora解析（「ー」「ッ」「ン」「拗音」）
- tokenization（過分割禁止）
- raw/display範囲
- confusability単調性
- 回帰：「コーーラ」