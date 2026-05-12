# Phase 2 設計書 — Daihon Rakku export に character.json 統合

**日付**: 2026-05-12
**前提**: Phase 1 で `presets/characters/*.json` の `danbooru_tags` 修正と hermes_pipeline 側読み込みは完了。
本書は **gui.py の export 機能改修で character.json を自動添付する** 段取りの設計書。

---

## 現状

`gui.py:15361 _do_export` で `csv / json / xlsx / sd_prompts / wildcard / dialogue / fukidashi / markdown` の 8 形式をエクスポートしている。
ユーザーは EXPORTS_DIR から手動で必要ファイルを選び ZIP 化、`outputs/hermes_pipeline/<work>/` に展開している。

現状 hermes_pipeline が必要とするファイル:
- `script_<timestamp>.csv`
- `sd_prompts_<timestamp>.txt` (sd_natural_en 含む)
- `fukidashi_<timestamp>.csv`
- `wildcard_<timestamp>.txt` (オプション)

**抜けているもの: キャラ正規 Danbooru タグの伝達経路**。
これを補うために Phase 1 では `character.json` を手動配置している。Phase 2 で export 自動化する。

---

## Phase 2 で追加する成果物

`EXPORTS_DIR / "character_<timestamp>.json"`

スキーマ (`presets/characters/char_*.json` から派生):
```json
{
  "exported_at": "2026-05-12T11:22:33",
  "exporter_version": "daihon-rakku-X.Y.Z",
  "characters": [
    {
      "char_id": "char_a1b2c3d1",
      "character_name": "中野一花",
      "work_title": "五等分の花嫁",
      "danbooru_tags": [...],
      "danbooru_tags_negative": [...],
      "anima_meta": {
        "weight": 1.2,
        "character_tag": "nakano_ichika",
        "series_tag": "go-toubun_no_hanayome",
        "with_faceless_male": true
      }
    }
  ],
  "primary_char_id": "char_a1b2c3d1"
}
```

複数キャラに対応するため `characters` を配列に。`primary_char_id` は今回シーンで主役のキャラ。

---

## 実装ステップ

### 1. `gui.py` UI 改修
- `_do_export` のチェックボックス候補に `"character"` 追加。
- ラベル: 「キャラ情報 (character.json)」
- デフォルト: ON (新規ユーザーが気付かなくても自動で含まれるよう)

### 2. `export_character_json(results, path, character_presets)` 関数追加
場所候補: `exports.py` または `gui.py` 内 (既存 export 関数群の隣)。
仕様:
- 引数 `results` (Scene list) と `character_presets` (キャラ ID → preset dict)
- シーン内に登場する全キャラ ID を集計
- presets から `danbooru_tags` / `danbooru_tags_negative` / `anima_meta` を抽出
- `characters` 配列に追加
- `primary_char_id` は最頻出キャラ
- `path` に JSON 書き出し (UTF-8 / ensure_ascii=False / indent=2)

### 3. `hermes_pipeline/parser.py` 改修
`parse_zip` (または別関数 `parse_character_json`) で ZIP 内の `character_*.json` を読み込み:
- ZIP に含まれていなければ従来通り (None を返す)
- 含まれていれば dict を返し、呼び出し側で `prepare_prompt.py` 等に渡す

`Scene` データクラスには影響しない。キャラ情報は scene と分離して保持。

### 4. `prepare_prompt.py` 改修
`work_dir/character.json` の代わりに、または併用で、ZIP 解凍時に出力された `character_<timestamp>.json` を読む経路を追加。
優先順位:
1. `work_dir/character.json` (Phase 1 手動配置、明示的最優先)
2. `work_dir/character_*.json` (Phase 2 自動配置、tail glob 最新)
3. なし (フォールバック: Grok 出力をそのまま使用)

### 5. 後方互換テスト
- 旧 ZIP (character.json なし) で `parse_zip` が壊れないこと
- 旧 anima_prompts (character_source: none) で compare_models_v2.py が動くこと

---

## 移行プラン

| ステップ | 内容 | 所要 |
|---|---|---|
| Phase 1 (完了) | preset 修正 + hermes_pipeline 側読込 + 手動 character.json 配置 | — |
| Phase 2-a | gui.py に `"character"` チェックボックス追加 + `export_character_json` 実装 | 30 分 |
| Phase 2-b | parser.py に `parse_character_json` 追加 + prepare_prompt 連携 | 20 分 |
| Phase 2-c | 既存全 preset の `danbooru_tags` 検証スクリプト (`scripts/validate_anima_tags.py`) — Danbooru wiki と照合し誤りをレポート | 60 分 |
| Phase 2-d | Daihon Rakku UI で「Anima タグ未設定キャラ」を可視化 + 編集 UI 追加 | 90 分 |

Phase 2-a, b は本作業の延長線上で最優先。c, d は別セッション。

---

## 既存 preset の `danbooru_tags` 検証

`scripts/validate_anima_tags.py` (新規)。
- presets/characters/*.json を全件走査
- `danbooru_tags` のうち、Danbooru wiki に存在しない or キャラ wiki と矛盾するタグを検出
- レポート (JSON / Markdown) を出力

実装は要 Web アクセス。バッチで 255 キャラ全部チェックすると 30 分〜。

---

## CLAUDE.md 整合性

本改修は **API コスト 0**。LLM 呼び出しは増えない。`gui.py` への影響は export 機能のみで、生成パイプラインに副作用なし。デプロイ前チェックリストの引数伝播・import 確認は必須。
