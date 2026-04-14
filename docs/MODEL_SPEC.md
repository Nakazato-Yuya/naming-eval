# MODEL_SPEC — Naming-Eval モデル仕様

## 1. 目的（要約）
ネーミングを EPI / Meaning / Orthography / Confusability の4軸で定量評価し、
Drivers と反事実差分で説明可能な一次選抜・改善支援を行う。

## 2. 入力
- name（表記）
- reading_kana（推奨：カタカナ読み。ない場合は正規化で推定）
- category（カテゴリ限定運用が前提）
- competitors（同カテゴリの既存名称リスト）

## 3. 出力契約（必須）
- raw sub-scores: [0,1]
- display scores: 0–100
- Drivers: 最大5件（短く・具体的・行動可能）
- Confusability: best match と sound/semantic/ortho の内訳

## 4. スコア群
### 4.1 EPI（発音容易性）
- かな正規化 → モーラ分解 → 特徴量（例：長さ、開音節、特殊モーラ、拗音、濁音、母音多様性、密度）
- raw=[0,1]、重み付き合成→100点化

### 4.2 Meaning Fluency（意味的認知容易性）
- 透明度（コンセプト一致） − 陳腐化（競合出現率） − 曖昧語ペナルティ 等
- 辞書注入でカテゴリに合わせて調整可能

### 4.3 Orthographic Clarity（表記明瞭性）
- 表記混在、読み割れ（辞書/読み欄で補強）、記号、視覚紛らわし等
- 「表記」+「カタカナ読み」2欄入力を推奨（読み問題を構造で解決）

### 4.4 Confusability（混同リスク）
- sound: CV列の編集距離類似
- semantic: token Jaccard
- ortho: 文字n-gram Jaccard
- カテゴリ別に閾値（p90/p95）を校正して hard 判定

## 5. 反事実差分（Counterfactual）
- keyword の add/remove による各スコアのΔを返す
- 意思決定の争点（トレードオフ）を可視化する