# CustomTkinter Material You (M3) UXスキル

このスキルは **CustomTkinter デスクトップアプリ** 専用の Material Design 3 ガイドです。
Web フレームワーク (React/Tailwind/MUI) は対象外。CTk ウィジェットのみ扱います。

---

## 1. コンポーネント決定マトリクス

| 用途 | ウィジェット | バリアント/備考 |
|------|-------------|----------------|
| 主要アクション | `MaterialButton` variant=`filled` | 画面に 1〜2 個まで |
| 補助アクション | `MaterialButton` variant=`filled_tonal` | filled の横に並べる |
| 低優先アクション | `MaterialButton` variant=`outlined` | テンプレート選択等 |
| テキストリンク風 | `MaterialButton` variant=`text` | 設定/詳細リンク |
| 浮動アクション | `MaterialFAB` | 画面右下固定、1 個のみ |
| グループ情報 | `MaterialCard` variant=`filled`/`outlined` | collapsible=True で折り畳み |
| フィルタ選択 | `MaterialChip` chip_type=`filter` | 複数選択可 |
| 補助選択 | `MaterialChip` chip_type=`assist` | 単発アクション |
| テキスト入力 | `CTkEntry` + M3 スタイル | border_width=1, corner_radius=6 |
| 複数行入力 | `CTkTextbox` + M3 スタイル | SURFACE_CONTAINER 背景 |
| ドロップダウン | `CTkOptionMenu` | CTkComboBox は使わない（テキスト直接編集不要の場合） |
| 通知 | `Snackbar` | duration=3000〜5000ms |
| ホバー説明 | `MaterialTooltip` / `add_tooltip()` | delay=500ms |
| プログレス | `CTkProgressBar` + フェーズラベル | PRIMARY 色 |
| スライダー | `CTkSlider` | number_of_steps で離散化 |

### バリアント選択フロー
```
ユーザーに最も注目させたい？
  → Yes → filled (PRIMARY 背景)
  → No  → 次の選択肢がある？
            → Yes → filled_tonal (SECONDARY_CONTAINER 背景)
            → No  → 枠線で区別？
                      → Yes → outlined (OUTLINE 枠)
                      → No  → text (装飾なし)
```

---

## 2. カラートークンクイックリファレンス

### Primary
| トークン | 値 | 用途 |
|---------|-----|------|
| `PRIMARY` | #6750A4 | ボタン/リンク/アクセント |
| `PRIMARY_CONTAINER` | #E8DBFF | 選択状態の背景 |
| `ON_PRIMARY` | #FFFFFF | PRIMARY 上のテキスト |
| `ON_PRIMARY_CONTAINER` | #1C0055 | PRIMARY_CONTAINER 上のテキスト |

### Secondary
| トークン | 値 | 用途 |
|---------|-----|------|
| `SECONDARY` | #5A5370 | 補助ボタン/セカンダリ要素 |
| `SECONDARY_CONTAINER` | #DFD8F0 | filled_tonal ボタン背景 |

### Surface 階層 (明→暗)
| トークン | 値 | 用途 |
|---------|-----|------|
| `SURFACE_CONTAINER_LOWEST` | #FFFFFF | 最明背景 |
| `SURFACE_CONTAINER_LOW` | #F2EDFA | カード背景/行背景 |
| `SURFACE_CONTAINER` | #E8E1F2 | 入力フィールド背景 |
| `SURFACE_CONTAINER_HIGH` | #DCD4EA | スライダートラック |
| `SURFACE_CONTAINER_HIGHEST` | #D0C7E0 | ホバー強調 |

### テキスト
| トークン | 値 | 用途 |
|---------|-----|------|
| `ON_SURFACE` | #151318 | 本文テキスト |
| `ON_SURFACE_VARIANT` | #49454F | ラベル/補助テキスト |
| `OUTLINE` | #79747E | ボーダー/区切り線 |
| `OUTLINE_VARIANT` | #B0A8BF | 薄いボーダー |

### Inverse (Tooltip/Snackbar)
| トークン | 値 | 用途 |
|---------|-----|------|
| `INVERSE_SURFACE` | #313033 | Tooltip/Snackbar 背景 |
| `INVERSE_ON_SURFACE` | #F4EFF4 | Tooltip/Snackbar テキスト |

### セマンティック
| トークン | 値 | 用途 |
|---------|-----|------|
| `ERROR` | #B3261E | エラー表示 |
| `SUCCESS` | #1B6B32 | 成功表示 |
| `WARNING` | #F59E0B | 警告表示 |

---

## 3. タイポグラフィスケール

```python
FONT_JP = "Noto Sans JP"  # 日本語本文
FONT_ICON = "Font Awesome 6 Free Solid"  # アイコン

# M3 Type Scale (CTkFont 対応)
# Display   — 未使用 (デスクトップ向けに大きすぎ)
# Headline  — size=20, weight="bold"    タブ/セクションヘッダ
# Title     — size=16, weight="bold"    カードタイトル
# Body L    — size=15                   入力フィールド
# Body M    — size=14                   本文/ドロップダウン
# Body S    — size=13                   ラベル/補助テキスト
# Label L   — size=14, weight="bold"    ボタン (medium)
# Label M   — size=12, weight="bold"    ボタン (small)/チップ
# Label S   — size=11                   キャプション
```

### Font Awesome 6 アイコン使用ルール
- `CTkLabel(font=CTkFont(family=FONT_ICON, size=N))` で使用
- テキストとアイコンを混在させない (別ラベルで横並び)
- サイズはテキストと同じか +2 まで

---

## 4. 8dp スペーシンググリッド

すべての padding/margin は **4 の倍数** を使用:

| 値 | 用途 |
|----|------|
| 4 | チップ間/最小間隔 |
| 8 | セクション内要素間/ラベル→入力 |
| 12 | カード間/セクション区切り |
| 16 | カード内パディング |
| 20 | セクション間 |
| 24 | 大セクション間 |
| 32 | ページ上下余白 |

### CTk での適用例
```python
# カード間: pady=(0, 12)
card.pack(fill="x", pady=(0, 12))

# ラベル→入力: pady=(8, 0) + pady=(2, 0)
label.pack(anchor="w", pady=(8, 0))
entry.pack(anchor="w", pady=(2, 0))

# グリッド内: padx/pady は 4 の倍数
btn.grid(row=0, column=0, padx=(0, 8), pady=4)

# カード内コンテンツ: 自動 padding 16
# MaterialCard.content_frame が内部で処理
```

---

## 5. レイアウトパターン

### pack vs grid 使い分け
| レイアウト | 方式 | 理由 |
|-----------|------|------|
| 縦積み (フォーム) | `pack(fill="x")` | 上から順にスタック |
| 横並びグリッド | `grid(row, column)` | テンプレート/チップ配列 |
| 横並び 2〜3 個 | `pack(side="left")` | スライダー行/ラベル+値 |
| カード列 | `pack(fill="x", pady=...)` | 折り畳みセクション |

### フォーム構造パターン
```python
# 標準フォームセクション
card = MaterialCard(parent, title="セクション名", variant="outlined",
                    collapsible=True, start_collapsed=True)
card.pack(fill="x", pady=(0, 8))
frame = card.content_frame

# ラベル + ドロップダウン
ctk.CTkLabel(frame, text="ラベル",
    font=ctk.CTkFont(family=FONT_JP, size=13, weight="bold"),
    text_color=MaterialColors.ON_SURFACE_VARIANT
).pack(anchor="w", pady=(6, 0))

dd = ctk.CTkOptionMenu(frame, values=options,
    font=ctk.CTkFont(family=FONT_JP, size=14), width=350,
    fg_color=MaterialColors.SURFACE_CONTAINER,
    button_color=MaterialColors.PRIMARY,
    text_color=MaterialColors.ON_SURFACE,
    dropdown_text_color=MaterialColors.ON_SURFACE,
    dropdown_fg_color=MaterialColors.SURFACE)
dd.pack(anchor="w", pady=(2, 0))
```

### グループ化行パターン (テンプレートグリッド等)
```python
row_frame = ctk.CTkFrame(parent,
    fg_color=MaterialColors.SURFACE_CONTAINER_LOW,
    corner_radius=8)
row_frame.pack(fill="x", pady=(0, 4))

ctk.CTkLabel(row_frame, text="カテゴリ", width=80, ...).grid(
    row=0, column=0, padx=(8, 6), pady=4, sticky="w")
for i, item in enumerate(items):
    btn = MaterialButton(row_frame, text=item, variant="outlined",
        size="small", width=90, ...)
    btn.grid(row=0, column=i+1, padx=(0, 6), pady=4, sticky="w")
    add_tooltip(btn, "説明テキスト")
```

---

## 6. インタラクティブ状態

### ホバー
- CTkButton: `hover_color` で自動処理
- MaterialButton: バリアント定義に含まれる
- カスタムホバー: `widget.bind("<Enter>", ...)` + `configure(fg_color=...)`

### フォーカス
- CTkEntry: 自動で枠線色変更
- カスタムフォーカスリング: `widget.bind("<FocusIn>", ...)` で `border_color` 変更

### 無効状態
```python
btn.configure(state="disabled")
# テキスト色を ON_SURFACE_VARIANT に、背景を SURFACE_CONTAINER に
```

### ローディング
```python
# ボタンをローディング状態に
btn.configure(state="disabled", text="処理中...")
# 完了後
btn.configure(state="normal", text="元のテキスト")
```

### Tooltip
```python
add_tooltip(widget, "説明テキスト")  # 500ms delay, M3 inverse スタイル
```

---

## 7. アクセシビリティ

### コントラスト比
- 本文テキスト: ON_SURFACE (#151318) on SURFACE (#FAF8FF) → 18:1 ✓
- ラベル: ON_SURFACE_VARIANT (#49454F) on SURFACE → 8.5:1 ✓
- ボタンテキスト: ON_PRIMARY (#FFF) on PRIMARY (#6750A4) → 5.5:1 ✓
- Tooltip: INVERSE_ON_SURFACE on INVERSE_SURFACE → 12:1 ✓

### ターゲットサイズ
- ボタン最小: 32px (small) — M3 準拠
- タッチ推奨: 40px (medium) — デフォルト
- チップ: 32px — M3 準拠

### キーボードナビゲーション
- `Ctrl+Enter`: 生成開始
- `Esc`: キャンセル/閉じる
- Tab: 標準フォーカス移動 (CTk 自動)

---

## 8. アンチパターン

### ❌ やってはいけないこと

| アンチパターン | 理由 | 正解 |
|--------------|------|------|
| `CTkComboBox` を選択専用に使う | テキスト編集が混乱する | `CTkOptionMenu` |
| `fg_color` にハードコード色 | テーマ変更不可 | `MaterialColors.TOKEN` |
| `font=("Arial", 14)` | 日本語崩れ | `CTkFont(family=FONT_JP, ...)` |
| カード内に `pack` と `grid` 混在 | Tkinter エラー | どちらかに統一 |
| `pady=5` や `padx=7` | グリッド崩れ | 4 の倍数のみ |
| filled ボタン 3 個以上横並び | 視覚的過負荷 | 1-2 filled + outlined |
| ネガティブプロンプトをUIに含める | ユーザー独自設定 | 絶対に追加しない |
| `CTkToplevel` を tooltip 以外で多用 | ウィンドウ管理地獄 | Snackbar/Card で代替 |
| `widget.place()` を通常レイアウトに | 位置計算地獄 | pack/grid を使う |
| アイコンとテキストを同一ラベルに | フォント競合 | 別ラベルで side="left" |

### ❌ CTk 固有の落とし穴

1. **CTkOptionMenu の値変更**: `.set(value)` 必須。`configure(variable=...)` は不可
2. **CTkTextbox の読み取り**: `.get("1.0", "end-1c")` — `end` だと末尾改行が入る
3. **CTkEntry の読み取り**: `.get()` — Textbox と API が異なる
4. **pack と grid の混在**: 同一親フレーム内で混ぜると `TclError`
5. **CTkToplevel の位置**: `wm_geometry(f"+{x}+{y}")` で明示指定しないとずれる
6. **after() キャンセル忘れ**: tooltip/timer は必ず `after_cancel()` で解除
7. **CTkFont のキャッシュ**: 同じ設定の CTkFont は再利用される（問題なし）
8. **日本語パス**: `subprocess` で `-c` 引数に日本語→スクリプトファイルで対処
