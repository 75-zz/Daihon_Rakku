"""hermes_pipeline — Daihon Rakku → Hermes → Grok web → ComfyUI/Anima

本番 Daihon Rakku とは独立した実験パイプライン。既存コード無改修。

Phase 1: Daihon export ZIP → Grok 投入用テキスト生成 (このディレクトリ)
Phase 2: Hermes browser skill (grok.com 自動操作)
Phase 3: Hermes ComfyUI skill (Anima workflow 実行)
Phase 4: エンドツーエンド統合
"""

__version__ = "0.1.0-phase1"
