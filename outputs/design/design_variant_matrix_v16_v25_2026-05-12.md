---
title: V16-V25 Variant Matrix 設計書
date: 2026-05-12
author: workflow-designer
task: Task #4 (animayume-research team)
---

# V16-V25 バリアント設計 — AnimaYume sweet-spot 探索

## 背景と目的

Scene 1 で V01-V15 を比較した結果、V06 / V07 / V08 (UNet = animayume_v04) が最良と判定された。
本フェーズでは以下の 3 軸を深堀りして sweet spot を特定する。

1. **masterpieces LoRA 強度スイープ** — 0.3〜0.7 の 5 段階 (V16-V20)
2. **解像度・アスペクト比** — 縦長/横長の AnimaYume 公式推奨値 (V21-V22)
3. **サンプラー/CFG 高品質設定** — steps=50 / CFG=5.0 (V23)
4. **プロンプト最小化** — 最小構成で Grok 本体をそのまま活かす (V24)
5. **追加 LoRA** — Task #1 (CIVITAI) 結果待ち / 暫定 Anima Aesthetic Boost v1.0 (V25)

ベースライン: **V08** (yume + masterpieces 0.5 + aesthetic tag + er_sde 30step CFG4.0)

---

## VARIANTS リスト追加分スニペット

compare_models_v2.py の `VARIANTS` リストの末尾 (`]` の直前) に以下を追加する。

```python
    # ─── V16-V25: AnimaYume sweet-spot 探索 ─────────────────────────────────
    # V16-V20: masterpieces strength sweep (全 AESTHETIC tag / er_sde 固定)
    {"name": "V16_yume_mast03_aesth", "unet": "animayume_v04.safetensors",
     "loras": [(LORA_MASTERPIECES, 0.3)], "tag": "aesthetic", "neg": "min",
     "sampler": "er_sde", "scheduler": "simple", "steps": 30, "cfg": 4.0},
    {"name": "V17_yume_mast04_aesth", "unet": "animayume_v04.safetensors",
     "loras": [(LORA_MASTERPIECES, 0.4)], "tag": "aesthetic", "neg": "min",
     "sampler": "er_sde", "scheduler": "simple", "steps": 30, "cfg": 4.0},
    # V18 = V08 の再録 (ベースライン確認用)
    {"name": "V18_yume_mast05_aesth_baseline", "unet": "animayume_v04.safetensors",
     "loras": [(LORA_MASTERPIECES, 0.5)], "tag": "aesthetic", "neg": "min",
     "sampler": "er_sde", "scheduler": "simple", "steps": 30, "cfg": 4.0},
    {"name": "V19_yume_mast06_aesth", "unet": "animayume_v04.safetensors",
     "loras": [(LORA_MASTERPIECES, 0.6)], "tag": "aesthetic", "neg": "min",
     "sampler": "er_sde", "scheduler": "simple", "steps": 30, "cfg": 4.0},
    {"name": "V20_yume_mast07_aesth", "unet": "animayume_v04.safetensors",
     "loras": [(LORA_MASTERPIECES, 0.7)], "tag": "aesthetic", "neg": "min",
     "sampler": "er_sde", "scheduler": "simple", "steps": 30, "cfg": 4.0},

    # V21: 縦長 1024x1536 (AnimaYume 公式推奨縦長)
    {"name": "V21_yume_mast05_aesth_portrait", "unet": "animayume_v04.safetensors",
     "loras": [(LORA_MASTERPIECES, 0.5)], "tag": "aesthetic", "neg": "min",
     "sampler": "er_sde", "scheduler": "simple", "steps": 30, "cfg": 4.0,
     "width": 1024, "height": 1536},

    # V22: 横長 1152x896
    {"name": "V22_yume_mast05_aesth_landscape", "unet": "animayume_v04.safetensors",
     "loras": [(LORA_MASTERPIECES, 0.5)], "tag": "aesthetic", "neg": "min",
     "sampler": "er_sde", "scheduler": "simple", "steps": 30, "cfg": 4.0,
     "width": 1152, "height": 896},

    # V23: 高品質設定 steps=50 / CFG=5.0
    {"name": "V23_yume_mast05_aesth_hq50", "unet": "animayume_v04.safetensors",
     "loras": [(LORA_MASTERPIECES, 0.5)], "tag": "aesthetic", "neg": "min",
     "sampler": "er_sde", "scheduler": "simple", "steps": 50, "cfg": 5.0},

    # V24: 最小プロンプト (min tag) で Grok 本体をそのまま活かす
    {"name": "V24_yume_mast05_min_clean", "unet": "animayume_v04.safetensors",
     "loras": [(LORA_MASTERPIECES, 0.5)], "tag": "min", "neg": "min",
     "sampler": "er_sde", "scheduler": "simple", "steps": 30, "cfg": 4.0},

    # V25: 追加 LoRA (Task #1 CIVITAI 結果次第で差し替え)
    # 暫定: Anima Aesthetic Boost v1.0 相当 (ファイル名は実環境に合わせて変更)
    {"name": "V25_yume_mast05_aestheticboost", "unet": "animayume_v04.safetensors",
     "loras": [(LORA_MASTERPIECES, 0.5),
               ("anima-aesthetic-boost-v1.0.safetensors", 0.4)],
     "tag": "aesthetic", "neg": "min",
     "sampler": "er_sde", "scheduler": "simple", "steps": 30, "cfg": 4.0},
```

### build_workflow への width/height 伝播 (V21/V22 用)

現行の `generate_one` はすでに `build_workflow(... width=..., height=...)` を受け取れる
シグネチャになっているため、`variant.get("width", 1024)` / `variant.get("height", 1024)` を
渡すよう `generate_one` 内の呼び出し 1 箇所を修正するだけでよい:

```python
        wf = build_workflow(
            unet_name=variant["unet"], positive=positive, negative=negative,
            seed=seed, filename_prefix=filename_prefix,
            loras=variant["loras"] or None,
            width=variant.get("width", 1024),   # ← 追加
            height=variant.get("height", 1024),  # ← 追加
            steps=variant.get("steps", 30), cfg=variant.get("cfg", 4.0),
            sampler=variant.get("sampler", "er_sde"),
            scheduler=variant.get("scheduler", "simple"),
        )
```

---

## バリアント設計根拠

| V# | 目的 | 変数 | 期待 |
|----|------|------|------|
| V16 | mast 強度下限 | strength=0.3 | 0.5 より線が柔らかくなるか確認 |
| V17 | mast 強度 | strength=0.4 | V16 と V08(0.5) の中間 |
| V18 | ベースライン再確認 | strength=0.5 (V08 複製) | seed 固定で V08 と同一→再現性確認 |
| V19 | mast 強度 | strength=0.6 | V03/V02 の base 結果と Yume で比較 |
| V20 | mast 強度上限 | strength=0.7 | 過剰適用でアーティファクトが出るか |
| V21 | 縦長解像度 | 1024×1536 | AnimaYume 公式推奨。全身/上半身構図に向く |
| V22 | 横長解像度 | 1152×896 | 複数人・横並びシーン向け |
| V23 | 高品質 | steps=50 / CFG=5.0 | 線の細部・色乗りの改善量 vs 時間コスト確認 |
| V24 | 最小プロンプト | min tag | プレフィックス量が少ない方が Grok 本体の情報量が活きるか |
| V25 | 追加 LoRA | aesthetic boost 0.4 | 色彩/シャープネス向上効果の確認 |

### V18 (ベースライン複製) の意義

同一 seed で V08 と V18 を比較することで、ランが再現可能かを確認できる。
もし出力が異なれば ComfyUI 側の非決定性やモデルキャッシュの問題を示す。

---

## 実行コスト見積もり

### 単 variant の時間

| 条件 | 推定時間 |
|------|---------|
| steps=30 / 1024×1024 (V16-V20, V22, V24-V25) | 50〜100 s |
| steps=30 / 1024×1536 (V21 縦長) | 70〜130 s (1.5× pixel 数) |
| steps=30 / 1152×896 (V22 横長) | 65〜120 s (1.01× pixel 数) |
| steps=50 / 1024×1024 (V23) | 80〜160 s (steps ×5/3) |

→ **10 variant × 1 scene の合計: 約 11〜14 分** (GPU 次第、RTX 3090 基準)

### GPU 電力

- RTX 3090 TDP 350W、1 variant あたり 100s → 約 9.7 Wh/variant
- 10 variant = 約 97 Wh ≒ 0.1 kWh → 電気代 3〜4 円

### タイムアウト推奨値

| バリアント | 推奨 --timeout |
|-----------|---------------|
| V16-V20 (std) | 300 s |
| V21 縦長 | 400 s |
| V22 横長 | 350 s |
| V23 steps=50 | 450 s |
| V24-V25 (std) | 300 s |

コマンド例 (V16-V25 のみ実行):
```
python compare_models_v2.py <work_dir> --scenes 1 --variants V16,V17,V18,V19,V20,V21,V22,V23,V24,V25 --timeout 450 --seed 42
```

---

## V25 差し替え条件

Task #1 (CIVITAI リサーチ) が新 LoRA を発見した場合は以下の優先順で差し替え:

1. AnimaYume 公式推奨 LoRA (作者 HauhauCS 系)
2. Anima Aesthetic Boost v1.0 (現暫定)
3. Mixed Styles v4 (LORA_MIXED_STYLES) の Yume 適用 — V09 との差分を確認

ファイル名だけ `"anima-aesthetic-boost-v1.0.safetensors"` → 実ファイル名に置換すれば
その他のコードは変更不要。

---

## Task #3 プロンプト最適化との連携

Task #3 の結果が出た時点で以下を検討:
- V24 の `"min"` tag profile に最適化テンプレートを新 TAG_PROFILES エントリとして追加
- V24 を V24b_optimized として差し替え実行 (V16-V25 batch の 2nd run として実施)

現時点では V24 は `min` tag で Grok 本体の自然言語情報量を最大化する構成とした。

---

## まとめ

- V16-V20 で masterpieces 強度の sweet spot を特定 (最重要)
- V21/V22 で解像度/アスペクト比の影響を確認
- V23 で steps=50/CFG=5.0 の品質向上コストを定量化
- V24 で最小プロンプト戦略の有効性を検証
- V25 は Task #1 次第でファイル名だけ差し替え可能な可変スロット
- build_workflow は width/height を既にサポート → generate_one に `variant.get("width/height", 1024)` を 1 行追加するだけで動作
- 全 10 variant × 1 scene の推定所要時間: 11〜14 分、電気代 3〜4 円
