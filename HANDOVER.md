# HANDOVER.md — Daihon Rakku プロジェクト引き継ぎ

**作成日**: 2026-02-12
**最終コミット**: `dc6ec8a` feat: v2.7.0 UI/UXリデザイン(Font Awesome 6+Noto Sans JP) + APIコスト節約
**現バージョン**: v2.7.0+（未コミットの変更あり）

---

## 1. プロジェクト概要

FANZA同人CG集の脚本を自動生成するデスクトップツール。
**CustomTkinter (Material You風UI)** + **Claude API** で、コンセプト入力 → あらすじ → シーン分割 → 各シーン生成 → 品質検証 → CSV/Excelエクスポートまで一貫して行う。

- **GUI**: `gui.py` (6536行、メインアプリケーション全体)
- **キャラビルダー**: `char_builder.py` (プリセット200体 + オリジナルキャラ作成)
- **タグDB**: `danbooru_tags.json` (16820エントリー/168カテゴリ)
- **スキル**: `skills/` 配下に14個のスキルファイル (パイプライン/セリフ品質/NSFW/ビジュアル等)

---

## 2. 未コミットの変更（重要！最優先で確認）

### gui.py に196行追加/45行削除の変更あり

#### A. キャラクター入力フィールドの個別化（最大の変更）
- **旧**: `characters_text` (単一の `CTkTextbox`) にキャラ情報をフリーテキストで記述
- **新**: 5つの個別 `CTkEntry` フィールドに分離
  - `char_name_field` — 名前（例: 中野一花（五等分の花嫁））
  - `char_personality_field` — 性格
  - `char_first_person_field` — 一人称
  - `char_endings_field` — 語尾
  - `char_appearance_field` — 外見
- **新メソッド追加**:
  - `_get_characters_text()` — 個別フィールド → パイプライン用テキスト組み立て
  - `_get_characters_fields()` — 個別フィールド → 構造化dict
  - `_set_characters_fields(fields)` — dict → 個別フィールドに設定
  - `_set_characters_text(value)` — 旧テキスト形式をパースして個別フィールドへ（後方互換）
- **config保存**: `characters_fields` (構造化dict) を新規追加、`characters` (テキスト) も併存
- **config読込**: `characters_fields` 優先、なければ `characters` テキストをパース（後方互換）
- **プリセット選択**: `_apply_preset()` が `_set_characters_fields()` で直接設定するよう変更

#### B. MaterialCard の折りたたみ強化
- `start_collapsed` パラメータ追加（初期状態で折りたたみ可能に）
- ヘッダー全体クリックで折りたたみトグル（ボタンだけでなくタイトル部分も）
- `cursor="hand2"` でクリック可能を視覚的に示す
- オリジナル作成タブの全カード（基本情報/性格・口調/外見/エロシーン設定/追加設定）を `start_collapsed=True` に変更

#### C. SD プロンプト自動改善
- `enhance_sd_prompts()`: intensity ≥ 3 のシーンに `1boy` + `faceless_male` を自動付与

#### D. その他の変更
- `other_chars_text` にデフォルト値追加: `"相手役の男性（顔なし）\nSD: 1boy, faceless_male"`
- フッターの著作権テキスト削除（プレゼン用）
- プリセットリスト: フィルタ切り替え時に先頭スクロール追加
- オリジナル作成タブ: `CTkScrollableFrame` → 通常の `CTkFrame` (fill="x") に変更
- `_custom_scroll` を `_build_scrollable_canvas()` の inner_frames から除去

### 未追跡ファイル（4件）
| ファイル | 内容 | 対応方針 |
|---|---|---|
| `skills/sd_prompt_director.skill.md` | SD Prompt Director スキル（台本⇔SDプロンプト整合性検証） | **コミット候補** — 新スキルとして有用 |
| `02_全タグ.txt` | リアルSDプロンプト集（66行、タグDB拡充の参考資料） | gitignore推奨（参考資料） |
| `20260210.png` | スクリーンショット | gitignore推奨 |
| `sp_エロ行為04.yml` | エロ行為YAML（旧資料？2025/3/20） | gitignore推奨（参考資料） |

---

## 3. 主な設計決定と理由

### キャラフィールド個別化の理由
- フリーテキストだとパイプラインへの渡し方が曖昧で、AIがキャラの一人称・語尾を正しく反映しないことがある
- 構造化データにすることで、スキル（セリフ品質チェック等）が一人称・語尾を確実に参照できる
- プリセット選択時のデータ反映も確実になる
- **後方互換**: 旧 `characters` テキスト形式も読み込み可能（パース処理あり）

### faceless_male 自動付与の理由
- FANZA CG集では「顔なし男」が標準。SD生成時に男キャラの顔が出ると品質低下
- intensity ≥ 3 はエロシーンなので、自動で `1boy, faceless_male` を確保

### オリジナルカード折りたたみの理由
- 5セクションが全展開だと画面を圧迫。必要な項目だけ展開する方がUX向上

---

## 4. 現在の状態と残タスク

### 完了済み
- v2.7.0 UI/UXリデザイン（Font Awesome 6 + Noto Sans JP）コミット済み
- キャラフィールド個別化の実装（未コミット）
- MaterialCard折りたたみ強化（未コミット）
- faceless_male自動付与（未コミット）
- sd_prompt_director.skill.md 新規作成（未追跡）

### 要確認・未完了の可能性
1. **キャラフィールド変更のテスト不足の可能性**
   - プリセット選択 → 個別フィールド反映 → パイプラインで正しくテキスト化されるか
   - 既存config.jsonの `characters` テキストが正しくパースされるか
   - `save_config()` → `load_config()` の往復で情報が欠落しないか
   - オリジナルキャラビルダーからの反映（`save_custom_character` 等）
2. **オリジナルタブのスクロール変更**
   - `CTkScrollableFrame` → `CTkFrame(fill="x")` に変更されたが、コンテンツが画面に収まらない場合のスクロールが失われていないか確認
3. **sd_prompt_director スキルの統合**
   - スキルファイルは作成されたが、パイプライン（`gui.py`）から呼び出す仕組みが未実装

---

## 5. 次にやるべきステップ（優先順）

### P0: 未コミット変更の動作確認とコミット
1. `gui.py` を起動して以下を手動テスト:
   - プリセットキャラ選択 → 5フィールドに正しく反映されるか
   - フィールド入力 → 生成実行 → パイプラインに正しく渡るか
   - config保存/読込の往復テスト
   - オリジナルタブの折りたたみ/展開動作
   - オリジナルタブのスクロール（コンテンツ量が多い場合）
2. 問題なければコミット（suggested message: `feat: キャラ入力フィールド個別化 + MaterialCard折りたたみ強化 + faceless_male自動付与`）
3. `sd_prompt_director.skill.md` も追加コミット

### P1: パイプライン品質改善
- sd_prompt_director スキルをパイプラインに組み込む（品質検証フェーズで呼び出し）
- セリフスキルの自動選択ロジックがキャラフィールドの構造化データを活用するよう改善

### P2: 将来の拡張候補（MEMORY.mdより）
- 個別シーン再生成機能
- アウトライン手動編集機能
- 結果プレビューパネル（GUI内で確認 + SDプロンプトコピー）

---

## 6. 絶対に触ってはいけないもの・制約

### 禁止事項
- **ネガティブプロンプトはツールに含めない**。ユーザーが独自に設定するもの。エクスポートにも絶対に追加しない
- `danbooru_tags.json` のフォーマット変更（既存パイプラインが依存）
- `char_builder.py` のプリセットキャラデータ構造変更（200体分の整合性が崩壊する）

### 技術的制約
- **max_tokens**: Haiku上限4096。`generate_scene_batch` で5000を指定すると壊れる（過去の教訓）
- **Windowsパス**: `-c` 引数に日本語パスを渡すとエスケープ問題。スクリプトファイル経由で対処
- **CTk Widget操作**:
  - `CTkTextbox`: `get("1.0","end-1c")` / `delete("1.0","end")` + `insert("1.0",v)`
  - `CTkEntry`: `get()` / `delete(0,"end")` + `insert(0,v)`
- **Python**: `C:\Users\k75mi\AppData\Local\Programs\Python\Python312\python.exe`

---

## 7. アーキテクチャ概要

```
gui.py (6536行) — メインアプリ
├── パイプライン関数群
│   ├── compress_context()     — コンテキスト圧縮
│   ├── generate_outline()     — あらすじ生成 (Haiku 1回)
│   ├── split_scenes()         — シーン分割 (Haiku 1回)
│   ├── generate_scene_draft() — シーン生成 (N回: Haiku/Sonnet)
│   ├── validate_script()      — 品質検証 (ローカル)
│   └── enhance_sd_prompts()   — SDプロンプト最適化 (ローカル)
├── UI クラス群
│   ├── MaterialCard            — Material You風カードコンポーネント
│   ├── Snackbar               — 通知表示
│   └── App(ctk.CTk)           — メインウィンドウ
├── エクスポート
│   ├── export_csv()
│   └── export_excel()
└── 設定管理
    ├── save_config() / load_config()
    └── SETTING_STYLES (和風/ファンタジー自動検出)

char_builder.py — プリセット200体 + オリジナルキャラ作成
danbooru_tags.json — タグDB v13.2 (16820エントリー/168カテゴリ)
skills/ — 14スキルファイル (パイプライン/セリフ/NSFW/ビジュアル等)
config.json — ユーザー設定保存
```

---

## 8. スキル一覧と役割

| スキル | 役割 |
|---|---|
| `low_cost_pipeline` | パイプライン全体制御 |
| `prompt_compactor` | コンテキスト圧縮 |
| `script_quality_supervisor` | FANZA基準品質検証 |
| `danbooru_nsfw_tags` | NSFWタグリファレンス |
| `nsfw_scene_composer` | NSFWシーン構成（体位/表情/体液/カメラ） |
| `ero_serihu_nomal` | セリフ品質（通常） |
| `ero_serihu_ohogoe` | セリフ品質（アヘ顔系） |
| `ero_serihu_jyunai` | セリフ品質（純愛） |
| `ero_serihu_tundere` | セリフ品質（ツンデレ） |
| `eromanga_serihu_sensei` | セリフ診断（8大パターン不自然チェック） |
| `cg_visual_variety` | カメラアングル多様性 |
| `material_design` | Material You UIガイド |
| `material-you-ui-designer` | Material You UIデザイナー |
| `sd_prompt_director` | **NEW** SD Prompt整合性監督（未統合） |

---

## 9. 重要な文脈

### FANZA CG集の黄金ルール（パイプラインに組み込み済み）
- エロ比率 75-85%（導入10-15%以内）
- 吹き出し: 1-10文字、2-3個/ページ
- 男セリフ: 0-1個/ページ厳守
- 同じ喘ぎパターン連続禁止
- description: 具体的行為・体位必須（抽象表現禁止）

### セリフスキル自動選択ロジック
- `_select_serihu_skill(theme, char_profiles)` でテーマ・キャラから判定
- ツンデレキャラ → `tundere`
- 純愛テーマ → `jyunai`
- NTR等 → `ohogoe`
- デフォルト → `nomal`

### 設定スタイル自動検出
- コンセプトのキーワードから3スタイルを自動判定:
  - `traditional_japanese_rural` (夜這い/村/田舎等)
  - `traditional_japanese_urban` (遊郭/花街等)
  - `fantasy_medieval` (異世界/魔法等)
- SDタグの自動置換・禁止・追加を実行

---

**これを HANDOVER.md として保存しました。次のセッションで最初にこのファイルを読んでください。**
