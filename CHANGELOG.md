# Changelog

## [0.2.0] - 2026-02-06

### Added
- 3段階スキルパイプライン統合
  - `prompt_compactor`: コンテキスト圧縮でトークン削減
  - `low_cost_pipeline`: Haiku下書き → Sonnet清書（重要シーンのみ）
  - `script_quality_supervisor`: 品質チェック → 差分修正
- シーン重要度（intensity）による清書判定
  - intensity >= 4 のシーンのみSonnetで清書
- 品質チェック後の差分修正機能
  - 全再生成禁止、問題箇所のみ修正
- 登場人物設定フィールド追加

### Changed
- API: kie.ai → Anthropic直接API に変更
- モデル構成:
  - Haiku: `claude-3-5-haiku-20241022`
  - Sonnet: `claude-sonnet-4-20250514`
- コスト追跡の詳細化（Haiku/Sonnet別）

### Directory Structure
```
project/
├── skills/           # スキルファイル
├── context/          # 圧縮済みコンテキスト
├── drafts/           # 下書き
├── final/            # 最終版・修正版
└── exports/          # CSV/JSON出力
```

---

## [0.1.0] - 2026-02-05

### Added
- 初期GUI実装（CustomTkinter）
- kie.ai API統合（OpenAI互換）
- 基本的なCSV/JSON出力
- テーマ選択機能
- Danbooruタグ・SD Prompt Guide対応
- jailbreak.md によるNSFWモード

### Files
- `gui.py` - メインGUI
- `jailbreak.md` - NSFW生成ガイドライン
- `danbooru_tags.md` - タグリファレンス
- `sd_prompt_guide.md` - プロンプトガイド
- `run_gui.bat` - 起動バッチ
