# Changelog

## [7.4.0] - 2026-02-18

### Added (SDプロンプト設定セクション + PNG Info読み取り)

#### SDプロンプト設定UI
- **折り畳みMaterialCard**: 「SDプロンプト設定」セクション新設（デフォルト折り畳み）
- **クオリティタグモード切替**: 自動（`(masterpiece, best_quality:1.2)`）/ カスタム入力のラジオボタン
- **プレフィックス/サフィックスタグ**: 全シーン先頭/末尾に追加されるカスタムタグ入力欄
  - LoRAタグ `<lora:model:0.7>` 等はdeduplicateをバイパス（壊れ防止）
- **設定永続化**: sd_quality_mode/sd_quality_custom/sd_prefix_tags/sd_suffix_tags の4キーを保存・復元

#### PNG Info読み取り（マルチフォーマット対応）
- **SD WebUI形式のメタデータ抽出**: PNG tEXt / JPEG EXIF UserComment / WebP EXIF対応
- **6段階抽出パイプライン**: PNG tEXt → EXIF sub-IFD → raw EXIF bytes → JPEG COM → img.info → ファイルバイトスキャン
- **piexif/Pillow互換**: `UNICODE\x00` + UTF-16-LE / latin-1誤デコード / 複数エンコーディング自動判定
- **抽出結果プレビュー**: 読み取り専用テキストボックスでプロンプト表示
- **適用ボタン**: 「プレフィックスに適用」「サフィックスに適用」で即座に反映

#### ドラッグ&ドロップ対応
- **windnd統合**: PNG/JPEG/WebP画像をドロップゾーンにD&Dで読み込み
- **ドロップゾーンUI**: アイコン+ヒントテキスト+クリックでファイル選択にも対応
- **日本語パス対応**: `force_unicode=True`でUnicodeパスを正しく処理
- **ビジュアルフィードバック**: 読み取り成功/失敗でボーダー色変化

### Changed
- `enhance_sd_prompts()`: sd_quality_tags/sd_prefix_tags/sd_suffix_tags 3パラメータ追加
- `generate_pipeline()`: 同3パラメータを転送
- PIL/windnd条件付きimport追加（未インストール時もクラッシュしない）

---

## [7.3.0] - 2026-02-18

### Added (ローカルプール生成 + セリフ品質根本修正)

#### character_pool_generator.py（新規）
- **ローカルキャラ固有プール生成**: API不要・即座に生成
- `detect_personality_type()`: 9性格タイプ自動判定
- `generate_moan_pool()`: MOAN_POOLからスコアリング+shyness補正で8個×5intensity選出
- `generate_speech_pool()`: 性格×フェーズの2Dマトリクス重み付きサンプリング+一人称置換+語尾適応
- `generate_thought_pool()`: 同様ロジック（語尾適応なし）

#### batch_generate_pools.py（新規）
- 255体一括プール生成CLI（--dry-run/--force/--char）
- 255体を1.8秒で生成（API版: $10 → ローカル: $0）

#### 男性セリフ観察型修正
- SPEECH_MALE_POOL dirty/praise「～だな」観察パターン除去→命令/挑発型に
- system prompt: 「身体観察」→「挑発」に変更、男性セリフ観察実況禁止ルール追加
- auto_fix Step 9a: _MALE_OBSERVATION_PATTERNS辞書+正規表現で自動置換
- validate_script: 男性観察型セリフ検出追加

#### thought部位ラベル冒頭修正
- THOUGHT_POOL body_awareness/general: 「太もも…」「膝…」等→感覚主語に全面書換
- auto_fix Step 9b: _BODY_PART_RE正規表現で25部位×「…」冒頭パターン自動置換
- validate_script: thought部位ラベル冒頭検出追加

### Changed
- gui.py: upgrade_character_pool_api()でspeech+thoughtのみAPI補正（moan維持）
- gui.py: load_preset_character()でプリセットプールコピー or ローカルオンザフライ生成
- cg_bubble_writer.skill.md: パターンE（部位ラベル冒頭禁止）追加
- 255体プール再生成完了（body-part-first 0件確認済み）

---

## [7.2.0] - 2026-02-17

### Added (キャラ固有セリフプール + フェーズ別セリフDB)

#### SCENE_PHASE_SPEECH_MAP新設（ero_dialogue_pool.py）
- 6フェーズ×5タイプ = 338エントリー
- intro(38)/approach(41)/foreplay(70)/penetration(73)/climax(76)/afterglow(40)
- 各フェーズにspeech/thought/male/moan/onomatopoeia

#### infer_phase()
- intensity+scene位置→フェーズ自動推定
- i1=intro / i2=approach / i3=foreplay|penetration / i4=penetration|climax / i5=climax|afterglow

#### generate_character_pool()
- キャラプロファイルからAPI 1回で専用セリフプール生成
- moan i1-5×8個 + speech 6phase×5個 + thought 6phase×5個 = ~100個/キャラ
- 保存先: characters/{char_id}_pool.json / Sonnet使用 / ~$0.03-0.05/キャラ

### Changed
- get_speech_pool(): phase引数追加（後方互換維持）
- build_character() Step 4追加: キャラ生成時に自動でプール生成+JSON保存
- auto_fix_script連携: Step 8a/8b/9/10でキャラプール優先混合
- _deduplicate_across_scenes連携: moan/thought/speechでキャラプール優先混合
- generate_scene_draft連携: common_systemにキャラ固有セリフ例をfew-shotとして注入
- shorten_male_speech除去（ユーザー指示）

---

## [7.1.0] - 2026-02-17

### Fixed (口調・セリフ精度向上)

#### MOAN_POOL不自然子音修正（46エントリー）
- i1: 12件 / i2: 15件 / i3: 6件 / i4: 5件 / i5: 5件
- 不自然子音組み合わせ（ひふ/くふ/はく/やふっ/ぐひっ等）→自然な喘ぎに置換

#### セリフプール修正
- THOUGHT_POOL長文修正: 6件20文字超→短縮
- SPEECH_FEMALE_POOL修正: 4エントリー短縮
- SPEECH_MALE_POOL修正: doctor 19文字→15文字
- THOUGHT_POOL guilt/resignation差別化: guilt=自責系、resignation=諦め系

### Changed
- _UNNATURAL_REPLACEMENTS +17パターン（書き言葉→話し言葉変換）
- _HIRAGANA_MAP +4パターン（嫌い/遅い/重い/狭い）
- validate_script +3新チェック: intensity不一致/語尾パターン3連続/thought20文字超
- auto_fix_script Step20追加: intensity不一致自動修正

---

## [7.0.0] - 2026-02-17

### Added (セリフ・プロンプト大幅拡張)

#### ero_dialogue_pool.py v7.0（4259→4782行 / 合計4400+エントリー）
- SPEECH_FEMALE_POOL 29→36カテゴリ / 835→990エントリー
  - +oral_react/afterglow/teasing/size_react/anger/praise_react/bondage_react
- THOUGHT_POOL 21→27カテゴリ / 591→701エントリー
  - +pleasure_denial/addiction/rage/resignation/confusion/guilt
- SPEECH_MALE_POOL 16→20カテゴリ / 400→480エントリー
  - +teacher/yakuza/classmate/stepfather
- ONOMATOPOEIA_POOL 12→17カテゴリ / 138→185+
  - +anal/throat/vibrator/dripping/breathing
- NEUTRAL_POOL 50→75 / AFTERMATH_POOL 50→75 / MALE_SHORT_REPLACEMENTS 30→50

#### ルーティング拡張
- bondage/stepfather/teacher/yakuza/classmate用speech+thought+male分岐追加
- forced→rage+pleasure_denial+resignation統合 / sibling→guilt統合 / corruption→addiction統合

### Changed
- _UNNATURAL_REPLACEMENTS +25パターン（拘束/義父/フェラ/小説的表現/硬い接続詞）
- _HIRAGANA_MAP +11エントリー（痛い/苦しい/太い/硬い/壊れる等）
- _INTENSITY_EXPRESSION_MAP intensity1-2追加 + 4-5に新タグ
- CLOTHING_ESCALATION拡張 / FLUID_PROGRESSION拡張 / _CONTRADICTORY_PAIRS +5ペア

---

## [6.0.0] - 2026-02-16

### Added (ユニバーサルテーマ拡張)

#### テーマ自動推定エンジン
- `_infer_theme_from_concept()`: THEME_KEYWORD_MAP 30テーマ×キーワードで自動推定
- `_build_dynamic_theme_guide()`: テーマ未マッチ時も最低限のガイド生成
- generate_pipeline()統合: テーマ未指定時→自動推定→動的フォールバックの3段階

#### THEME_OPTIONS 17→31（+14テーマUI）
- isekai/onsen/sleep/gangbang/medical/swimsuit/sports/idol/neighbor/prostitution/voyeur/tentacle/reverse_rape/cosplay

#### THEME_GUIDES 16→30（+14テーマ設定）
- 各テーマにintensity_curve/foreplay_ratio/intro_ratio/sd_tags等

#### ero_dialogue_pool.py v6.0（4236→5276+行 / 合計3500+エントリー）
- STORY_PATTERN_LIBRARY 31→46パターン / 690 key_lines
- SPEECH_FEMALE_POOL +7カテゴリ / THOUGHT_POOL +3カテゴリ / SPEECH_MALE_POOL +4カテゴリ
- ルーティング拡張: isekai/onsen/sleep/gangbang/medical/idol用分岐追加

---

## [5.0.0] - 2026-02-16

### Fixed (50シーン品質崩壊の根本修正 + 痴漢/公共テーマ完全対応)

#### 7根本原因修正
- ascending curve空文字 / chikan foreplay_ratio / 男性セリフ反復 / title品質 / location多様性 / プール不足 / 50シーンプロンプト

#### ero_dialogue_pool.py v5.0（3162→4236行 / 合計3000+エントリー）
- STORY_PATTERN_LIBRARY +3パターン（public_molestation/toilet_trap/stranger_assault）
- SPEECH_MALE_POOL +3カテゴリ（chikan/taunt/public）
- SPEECH_FEMALE_POOL +1カテゴリ（chikan）
- THOUGHT_POOL +2カテゴリ（public_shame/chikan_resistance）

### Changed
- chikan intensity_curve ascending→wave / foreplay_ratio 0.10→0.20
- validate_script: title品質チェック + 男性セリフ末尾反復チェック
- auto_fix: pool男性修正 / ハードコード代替 / title修正 / description混入修正
- long_script_section: 25+シーン用mini-arc/i4連続上限5/男性セリフ多様性

---

## [4.0.0] - 2026-02-15

### Added (ストーリー＆セリフ回しパターン大幅拡充)

#### ero_dialogue_pool.py v4.0（2472→3162行 / 合計2800+エントリー）
- STORY_PATTERN_LIBRARY 16→28パターン（+12新パターン）
- SPEECH_FEMALE_POOL 21カテゴリ/645エントリー
- THOUGHT_POOL 16カテゴリ/491エントリー
- SPEECH_MALE_POOL 9カテゴリ/255エントリー
- ONOMATOPOEIA_POOL 12カテゴリ/138エントリー

#### ルーティング拡張
- 調教/SM/近親/義妹/アナル専用ルート追加

### Changed
- MOAN_POOL intensity4補完

---

## [3.9.0] - 2026-02-15

### Added (ストーリーパターン学習データ + Wild Cardエクスポート)

#### STORY_PATTERN_LIBRARY（エロ漫画頻出16パターン）
- **ero_dialogue_pool.py**にストーリー展開パターンライブラリを新設
- 各パターンに`beats`(展開ビート)、`dialogue_evolution`(セリフ進化)、`intensity_pattern`、`key_lines`(early/mid/late)を構造化
- 収録パターン16種:
  - `blackmail_corruption`(脅迫→堕落) / `childhood_friend`(幼なじみ再会) / `tutor_student`(家庭教師×教え子)
  - `drunk_mistake`(酔った勢い) / `massage_escalation`(マッサージ→エスカレート) / `caught_masturbating`(自慰目撃)
  - `bet_game`(賭け→罰ゲーム) / `bodyswap_possession`(入れ替わり/憑依) / `overnight_stay`(お泊まり→夜這い)
  - `gratitude_repayment`(恩返し) / `reunion_ex`(元カレ/元カノ再会) / `secret_relationship`(秘密の関係)
  - `aphrodisiac_effect`(媚薬/薬効果) / `dare_challenge`(王様ゲーム) / `rescue_gratitude`(助け→好意) / `peeping_discovered`(覗き→共犯)
- **`select_story_pattern(theme, concept)`**: テーマ/コンセプトからBESTマッチのパターンを自動選択
- **`get_pattern_key_lines(theme, concept, phase)`**: フェーズ別key_linesを返すユーティリティ

#### generate_outline()パターン注入
- アウトライン生成時に`select_story_pattern()`でマッチしたパターンのビート・セリフ進化・intensity展開を「参考ストーリーパターン」としてプロンプトに自動注入
- あらすじの内容を優先しつつ、展開テンポや感情の流れの参考としてLLMに提示

#### get_speech_pool()パターン連動
- `concept`引数追加（後方互換維持）
- intensity→phase推定（1-2=early, 3-4=mid, 5=late）でSTORY_PATTERN_LIBRARYのkey_linesをセリフプールに混合
- 内部実装を`_get_speech_pool_core()`に分離してラップ

#### Wild Cardエクスポート
- **`export_wildcard()`新規**: 各シーンのSDプロンプトを1行1プロンプトで出力（SD Wild Cardの`__filename__`で参照可能）
- ExportDialogに「Wild Card」フォーマット追加
- 生成完了時の自動エクスポートにも追加（`wildcard_{timestamp}.txt`）

### Changed

#### CSVシーン番号付与
- `export_csv()`の`sd_prompt`列末尾に`"シーンN"`をダブルクォート付きで自動付与
- 空のsd_promptには付与しない
- Wild CardファイルのSDプロンプトにも同様にシーン番号を付与

### Performance
- ero_dialogue_pool.py: v3.8→v3.9（+365行、STORY_PATTERN_LIBRARY 16パターン）
- 品質スコア: リグレッションなし

---

## [3.4.0] - 2026-02-14

### Added (コスト最適化 + 529耐障害性 + 品質自動修正強化)

#### 529 Overloadedエラー耐障害性
- **Sonnet自動フォールバック**: Haiku 4.5が529エラー3回連続→自動でSonnetに切替（シーン欠落防止）
- **段階的リトライ**: MAX_RETRIES_OVERLOADED=6、待機時間15→30→45→60秒の段階的増加
- **グローバルクールダウン**: シーンループレベルで529検出時60秒待機→再リトライ1回
- 旧動作: 529×3回→シーン欠落（12分浪費）→ 新動作: 529×3回→Sonnet即座切替（5秒）

#### 入力トークン削減
- **story_so_far 3層スライディングウィンドウ**: 直近3シーン=フル / 4-8前=圧縮 / 9+前=1行概要
  - S30時点: 4,750→2,095トークン（-56%）
- **outline_roadmap近傍圧縮**: 全N行→現在シーン±5行のみ送信（-63%）
  - 30シーン合計: 100,050→54,630トークン（-45.4%）

#### 品質自動修正強化
- **体位分布リバランス** (`enhance_sd_prompts` Step 8): spread_legs等40%超過→30%以下に自動削減
- **description具体化修正** (`auto_fix_script` Step 16): intensity≥4で抽象description→具体表現自動追加（8パターン/intensity）
- **story_flow重複修正** (`auto_fix_script` Step 14): 先頭20字一致→接続詞変換（10パターン）
- **speech重複修正** (`auto_fix_script` Step 15): 同一セリフ→末尾バリエーション付加（4パターン）
- **description重複修正** (`auto_fix_script` Step 12): 先頭30字一致→intensity別挿入文（8パターン×5段階+4段階フォールバック）

### Changed

#### モデルルーティング最適化（2-tier化）
- **シーン生成**: 全intensity→Haiku 4.5（Haiku 3はキャラ名化け "ボアため" 等のため除外）
- **アウトライン≤12シーン**: haiku_fast→Haiku 4.5（品質確保）、max_tokens 4096→8192
- **haiku_fast残留**: compact_context / synopsis のみ（テキスト要約専用）
- **Haikuモデル更新**: claude-3-haiku-20240307 → claude-haiku-4-5-20251001

#### コスト表示修正
- model_typeラベル: "fast"→"Haiku(4.5)"に修正（実際のモデルと一致）
- estimate_cost: 2-tier計算に簡略化（haiku_fast=圧縮/あらすじ、haiku=その他全て）
- コスト表示: "fast×N + Haiku4.5×M + Sonnet×K"→"Haiku4.5×M + Sonnet×K"

#### テーマ検出拡張（5テーマ対応）
- NTRのみ→ ntr / forced / corruption / reluctant / vanilla の5テーマ自動検出
- forced/reluctantテーマ: 合意セリフ（"もっと♡"等）を抑制、denial/embarrassedプールから選択

### Performance
- 品質スコア: 平均91.3/100（90点以上 24/35件）
- description抽象的: 69件→12件（-83%）
- 体位分布偏り: 9件→0件（完全解消）
- 30シーン推定コスト: ~$0.66→~$0.61（-7.5%）

---

## [3.3.0] - 2026-02-14

### Added (台本精度100点改善)

#### 体位重複防止システム
- **POSITION_TAGS**(34個): SD体位タグの完全リスト
- **POSITION_FALLBACKS**(18体位): 各体位の代替候補3つ
- **intensity別優先度**: 高intensityでは激しい体位を優先選択
- `validate_script`: 連続同一体位検出
- `enhance_sd_prompts`: 前シーンと同一体位→自動代替置換

#### セリフ自動修正拡張
- **_UNNATURAL_REPLACEMENTS**(53パターン): 不自然表現→自然な話し言葉変換
- **_MALE_SPEECH_REPLACEMENTS**(6パターン): 男性セリフの♡除去・moan→speech変換
- **_HIRAGANA_MAP**(16パターン): 漢字表現→ひらがな変換
- `validate_script`: 不自然表現/医学用語/過剰敬語チェック3種追加

#### 複合テーマ・性格対応
- **_detect_personality_type**: 9タイプ（ツンデレ/ヤンデレ/クーデレ等）自動判定
- **_select_serihu_skill**: 性格優先→テーマフォールバック、複合テーマ(+区切り)対応
- 混合比率による段階的スキル選択

#### 設定スタイル拡張
- **SETTING_STYLES** 3→9スタイル: school/urban/hot_spring/beach/sci_fi追加
- **_loc_map** 25→108エントリー（場所名→背景タグ変換）
- **bg_tags+_bg_kw** 86エントリー同期

#### その他
- 濁点喘ぎ正規化: ゛゜結合濁点を除去して類似判定精度向上
- description具体性チェック: _CONCRETE_DESC_KW(40+キーワード)
- 3連続同一location自動修正: _fix_consecutive_locations(8種variation)
- dialogue→bubbles自動変換: validate_script+auto_fix_scriptで旧フォーマット完全対応
- 吹き出し数上限トリミング: 4個超→moan>thought>speech優先で4個に削減

### Changed
- ero_dialogue_pool.py: 不自然表現プール矛盾7エントリー修正
- story_so_farスライディングウィンドウ: 直近2=フル/3-5=圧縮/6+=1行概要

---

## [3.2.0] - 2026-02-14

### Added (スキーマバリデーション + エクスポート拡充)

#### スキーマバリデーション (`schema_validator.py`)
- パイプライン全フェーズの構造検証（純Python/外部依存なし）
- validate_context / validate_outline / validate_scene / validate_results / validate_pipeline_output
- gui.pyの7箇所に統合（parse直後+フェーズ完了時）、警告のみ・処理ブロックなし

#### エクスポート3新形式
- **SDプロンプト一括TXT**: 全シーンのsd_promptを1ファイルに出力
- **セリフ一覧TXT**: 全吹き出しテキストを話者/種類別に出力
- **マークダウン脚本**: 読みやすいMarkdown形式で脚本全体を出力

#### ExportDialogクラス
- M3デザイン、6形式複数選択+JSONインポート機能
- export_json メタデータ拡充: version/concept/theme/characters/cost/quality_score/synopsis
- 生成完了時にCSV/JSON/Excel/SDプロンプト/セリフ一覧の5形式を自動同時出力

### Changed
- generate_pipeline()戻り値拡張: results, cost_tracker, pipeline_metadata
- 「再エクスポート」ボタン追加（生成完了後に有効化）

#### チャンク分割リッチアウトライン生成
- **_generate_outline_chunk()新関数**: 13シーン以上を10シーンずつチャンク生成
- 常にフル12フィールド形式（scene_id/title/intensity/location/situation/goal/emotional_arc/beats/story_flow/erotic_level/viewer_hook/time）
- 前チャンク結果を次チャンクに伝搬して一貫性確保
- 旧: >12シーンで5フィールドのみ→物語崩壊 → 新: 常にフル形式

#### ストーリーロードマップ注入
- outline_roadmap: 全シーンの概要を★マーク付きで各シーン生成に渡す
- LLMが「シーンNが全体のどこに位置するか」を把握可能に

#### アウトラインフィールド明示抽出
- JSON dump→構造化フォーマット（goal/situation/emotional_arc/beats/story_flow等を明示的に展開）
- LLMの指示追従率向上

#### キャラ名切り詰め修正
- 11文字超のキャラ名が途中で切れる問題→auto_fixでフルネーム自動復元

---

## [3.1.0] - 2026-02-13

### Added (セリフ自然さ大幅強化 + エロセリフプール + 文脈認識重複除去)

#### エロセリフプール新設 (`ero_dialogue_pool.py`)
- **MOAN_POOL**: intensity 1-5の5段階×80パターン（計400エントリー）
- **SPEECH_FEMALE_POOL**: 8カテゴリ（甘え/否定/懇願/堕落/絶頂/混乱/事後/日常）各20-25エントリー
- **THOUGHT_POOL**: 6カテゴリ（NTR罪悪感/快楽自覚/混乱/堕落受容/事後/日常）各15-20エントリー
- **SPEECH_MALE_POOL**: 5カテゴリ（支配/事実描写/挑発/NTR/調教）各15-20エントリー
- **NEUTRAL_POOL**: 非エロシーン用25+25エントリー（歩行/会話/帰宅シーン向け）
- **AFTERMATH_POOL**: 事後シーン用25+25エントリー（放心/疲労/余韻）
- `pick_replacement(pool, used, max_len=10)`: 使用済み管理付きランダム選択
- `get_speech_pool(theme, intensity)`: テーマ×intensity自動選択
- `get_male_speech_pool_for_theme(theme)`: テーマ別男性セリフプール

#### 文脈認識シーン分類 (`_analyze_scene_context`)
- シーンのdescription/title/mood/intensityから5種類を自動判定:
  - `non_sexual`: 歩行/食事/会話/帰宅等の非エロシーン
  - `foreplay`: 脱衣/愛撫/キス等
  - `sexual`: 本番行為
  - `climax`: 絶頂・痙攣
  - `aftermath`: 事後・放心
- 重複除去時に文脈に合ったプールから代替を選択（歩行シーンに喘ぎが混入しない）

#### CG集吹き出し専門スキル (`cg_bubble_writer.skill.md`)
- 書き言葉→話し言葉変換テーブル12組（「信じられない」→「うそ…」等）
- NGパターン4カテゴリ（説明的セリフ/文語表現/不自然な途切れ/説明的thought）
- intensity別指針5段階 + 事後シーン指針
- 男性セリフ鉄則 + 品質チェックリスト8項目
- `generate_scene_draft`/`generate_scene_batch`両方のシステムプロンプトに組み込み

#### 男性セリフ制御スキル (`male_serihu_controller.skill.md`)
- 10の絶対ルール（♡禁止/最大8文字/命令形基本/甘え語尾禁止等）
- 4テーマ別トーンマッピング（NTR/純愛/調教/痴漢）
- 文法パターンテンプレート（命令形/体言止め/短い断定/挑発疑問）

### Changed

#### セリフ重複除去の全面リライト (`_deduplicate_across_scenes`)
- 文脈認識: `_analyze_scene_context()`で非エロ/前戯/本番/絶頂/事後を判定
- 非エロシーン: NEUTRAL_POOLからのみ代替選択（エロセリフ混入防止）
- 事後シーン: AFTERMATH_POOLからのみ代替選択
- 反復パターン追跡: 「初めて」「彼のこと」「感じ」等の頻出フレーズを全体で2回以下に制限
- 長文セリフ: 強制切断を完全廃止→プールから短い代替を選択

#### 不自然表現の自動修正 (`auto_fix_script` ステップ4.7)
- 句点「。」→「…」自動変換
- 書き言葉→話し言葉 自動置換15パターン（「信じられない」→「うそ…」等）
- ひらがな化6パターン（「気持ちいい」→「きもちぃ」、「大好き」→「だいすき」等）

#### 男性セリフ自動修正 (`auto_fix_script` ステップ4.5)
- ♡♥自動除去
- moan→speech自動変換（男は喘がない）
- 後処理で再検証（validate_script）追加

#### 既存セリフスキル5種の文字数統一
- `ero_serihu_nomal/ohogoe/jyunai/tundere` + `eromanga_serihu_sensei`
- 「15〜35文字目安」→「1〜10文字」に全修正（CG集フォーマットに統一）
- 「。」禁止ルール追加、書き言葉→話し言葉変換ルール追加
- 主語・目的語削除ルール追加、ひらがな優先ルール追加

#### `eromanga_serihu_sensei` パターン拡張（8→11パターン）
- パターン9: 男女セリフ混同検出
- パターン10: キャラ口調逸脱検出
- パターン11: シーン-セリフ不整合検出

#### プロンプト強化 (`generate_scene_draft`)
- 鉄則セクション: 「。」禁止/ひらがな優先ルール追加
- NG表現→正しい変換12組をインラインで追加
- 最終チェック: 非エロシーン保護/男性女性表現/反復制限等7項目追加
- intensity 1-2: 喘ぎ・♡・エロ系セリフの絶対禁止を明示

---

## [3.0.0] - 2026-02-13

### Added (プリセット255体 + タグDB v18.0 + テンプレート32種)

#### プリセットキャラ +55体（200→255体）
- **新タイトル12作品**: 薬屋のひとりごと / 負けヒロインが多すぎる！ / 義妹生活 / ロシデレ / 魔法科高校の劣等生 / ダンまち / 俺だけレベルアップな件 / 100カノジョ / 無職転生 / 転スラ / ゼノブレイド3 / ゼンレスゾーンゼロ(ルーシー)
- **既存タイトル追加**: ワンピース(ビビ/レベッカ) / 呪術廻戦(歌姫/冥冥) / 鬼滅(カナヲ) / ダンダダン(アイラ) / チェンソーマン(レゼ/アサ) / ヒロアカ(梅雨) / ブルアカ(アコ/ワカモ/ナツ) / 原神(モナ/宵宮) / スタレ(フォフォ) / ウマ娘(スズカ/スペ) / NIKKE(ドロシー) / 学マス(手毬/麻央) / FGO(頼光/牛若丸) / アズレン(高雄) / P5(武見妙) / FF7(ジェシー)
- **カテゴリ別**: ソシャゲ60 / アニメ42 / ジャンプ40 / ラノベ34 / ゲーム25 / VTuber20 / マガジン14 / ジャンプ+10 / サンデー10
- 6エージェント並列作成、全55体JSON整合性検証済み

#### タグDB v18.0（61,508→63,819エントリー、195→202カテゴリ、+2,311タグ）
- **新カテゴリ7個**:
  - `male_body_types`(150): 顔なし男体型、手ポジション、腕シルエット、男性器関連
  - `male_clothing_states`(123): 男性衣服状態（ズボン下ろし、シャツ乱れ等）
  - `sweat_fluid_physics`(147): 汗粒・唾液糸・愛液・精液の物理描写
  - `cross_section_anatomy`(129): 断面図・X線・子宮内・精子描写
  - `clothing_body_friction`(131): 布越し触り・食い込み・伝線・透け・引き裂き
  - `erotic_lighting`(119): ラブホ照明・肌テカリ・月光裸体・汗逆光
  - `nsfw_male_pov_details`(120): 男性POV構図（撮影POV・行為POV等）
- **既存12カテゴリ拡充** (+1,392タグ):
  - nsfw_fluids 300→448 / nsfw_expression_sex 450→552 / nsfw_penetration_details 300→419
  - nsfw_body_reactions 300→419 / nsfw_orgasm_climax 300→420 / nsfw_aftermath 300→401
  - nsfw_camera_angles 350→448 / skin_details 300→408 / effects 450→550
  - nsfw_dirty_talk 300→472 / nsfw_clothed_sex 300→405 / genital_details 300→404

#### テンプレート拡張（20→32種）
- **異種族系**: サキュバス / 獣耳メイド / ダークエルフ / 天使堕ち
- **シチュ特化**: 催眠JK / 女騎士 / 陰キャ同級生 / 配信者
- **年齢差系**: 女上司 / ママ友 / 若妻先生 / 寮母さん

#### アーキタイプ拡張（12→14種）
- **サキュバス系**: 妖艶な誘惑者、本気の恋には不器用、余裕の崩壊が見どころ
- **陰キャ・オタク**: 内向的趣味人、推しのためなら行動力あり、自虐と純愛のギャップ

### Changed
- `_INTENSITY_EXPRESSION_MAP` レベル3-5に汗タグ追加（sweat_drops/sweaty_body/sweat_glistening/skin_glistening）
- `enhance_sd_prompts()` に男性体型タグ自動注入ロジック追加（intensity≥3 + 1boy時にmuscular_male/veiny_arms付与）
- `CLOTHING_OPTIONS` に「鎧・アーマー」追加
- `DANBOORU_CLOTHING_MAP` に鎧・アーマーマッピング追加
- danbooru_tags.json: version 17.0→18.0
- テンプレートグリッド: 5行→8行（カテゴリ別4列レイアウト維持）
- アーキタイプチップグリッド: 3行→4行

---

## [2.8.0] - 2026-02-12

### Added (ストーリー構成バー + タグDB v16.0 + 品質強化)

#### ストーリー構成バー（Story Composition Bar）
- **プロローグ/本編/エピローグ比率をGUIで視覚的に調整可能に**
  - 3色セグメントバー（Canvas描画）でリアルタイムプレビュー
  - スライダー2本: プロローグ5-30% / エピローグ5-20%（本編は自動算出）
  - 5プリセット: 標準バランス(10/80/10) / エロ重視(5/90/5) / ストーリー重視(20/70/10) / じっくり展開(15/75/10) / カスタム
  - `generate_outline()` / `generate_pipeline()` に透過的に反映
  - 設定保存・復元対応

#### タグDB v16.0（20,792→34,998エントリー、+14,206タグ、+68%）
- **全180カテゴリを最低120以上に底上げ**（最小40→120に大幅改善）
- 9エージェント並列（2波）で全カテゴリ一斉拡充
- 分布: 100-150帯50cats / 150-200帯81cats / 200-300帯38cats / 300+帯11cats
- 100未満のカテゴリ: 88→**0**（全カテゴリが実用水準に）

#### エロ表情タグ系統的強化
- 新カテゴリ: `erotic_expression_intensity`(130) / `sex_scene_body_reactions`(81)
- `nsfw_expression_sex` 284→362（ahegao×体位コンボ、アーキタイプ別段階、感情遷移）
- `_INTENSITY_EXPRESSION_MAP`: intensity 3-5で表情タグ自動注入
- `WEIGHT_EXPRESSION`拡張（head_back/drooling/heart-shaped_pupils等追加）

#### セリフ重複チェック大幅強化
- `_normalize_bubble_text()`: ♡♥…っー除去 + カタカナ→ひらがな正規化
- `_is_similar_bubble()`: 完全一致/正規化一致/先頭3文字一致の3段階判定
- `_deduplicate_across_scenes()`: speech/moan/thought全タイプ対応 + 類似度判定
- SE重複チェック: 隣接→3シーン窓に拡大
- ブラックリスト形式改善（明示的ヘッダー + ❌箇条書き）

#### 新スキル2種
- `danbooru_tag_expander.skill.md`: タグ拡充の命名規則・品質基準・カテゴリ別戦略
- `sd_tag_effective_use.skill.md`: intensity連動タグ選択・カテゴリ横断組み合わせ・ウェイト付与・多様性確保ルール

### Changed
- `script_quality_supervisor.skill.md`: 65→160行（重複チェック/body reaction/intensity jump検証追加）
- `sd_prompt_director.skill.md`: 410→454行（expression×intensity連携/エスカレーション追加）
- `cg_visual_variety.skill.md`: 89→136行（ショット分布/表情視認性/POV一貫性追加）
- danbooru_tags.json: version 15.0→16.0

---

## [2.7.0] - 2026-02-11

### Changed (UI/UXリデザイン + APIコスト節約)

#### UI/UXリデザイン
- **Font Awesome 6アイコンフォント導入**: 全絵文字(🎬🔑📁🎭📖⚙️💰📋🚀💾⏹✨❌⚠️等)をFont Awesome 6 Solidアイコンに置換
  - `fonts/fa-solid-900.ttf` 配置、`Icons`クラスで20アイコン定義
  - `icon_text_label()` ヘルパーでセクションヘッダーをアイコン+テキスト分離構成に
  - ログ・コールバック文字列は `[OK]`/`[ERROR]`/`[WARN]`/`[SCENE]`等のテキストプレフィックスに統一
  - Snackbar・ボタンテキストから絵文字除去（type色で意味を伝達）
- **フォント移行**: Segoe UI → Noto Sans JP（日本語表示品質向上）
- **フォントサイズ全面拡大**: 全UIフォント+2pt（9→11, 10→12, 11→13, 12→14, 13→15, 14→16, 18→20）
- **Material Design 3カラーパレット微調整**: PRIMARY `#5B3FA0`→`#6750A4` / ON_SURFACE_VARIANT→`#49454F` / OUTLINE→`#79747E`
- **余白・スペーシング全面拡大**: M3の4dp倍数グリッドに準拠
  - カード間ギャップ: `pady=(0,12)`→`(0,16)` / 内部パディング: `padx=16`→`20`
  - ヘッダー高さ: 52→56 / ボタン高さ: 46→48 / プリセットタブ余白全般拡大
- **入力フィールドフォーカス状態**: FocusIn時にborder_color=PRIMARYでハイライト

#### APIコスト節約（品質維持）
- **Sonnet使用閾値変更**: `intensity >= 4` → `intensity >= 5` のみSonnet使用（Sonnetコスト約半減）
- **story_so_far短縮**: 直近5シーン → 3シーンに削減（入力トークン約40%削減）
- **danbooru_tags.md除去**: APIプロンプトから冗長なファイル読込を廃止（シーンあたり約2,500トークン節約）

#### エクスポート改善
- CSV/Excel列順を重要度順に並び替え（scene_id/title/description/bubbles/SD promptを先頭に）

---

## [2.6.0] - 2026-02-10

### Added (タグDB v13.2 NSFW本格拡充 + 設定スタイル自動検出)

#### タグDB v13.0→v13.2（14,000→16,820エントリー、168カテゴリ）
- **背景・場所タグ大幅拡充（v13.1）**: 14既存カテゴリ拡充 + 4新カテゴリ追加
  - locations 602→820 / city_background 76→140 / background_nature 68→140
  - 室内系9カテゴリ拡充: room_states→105 / background_details→100 / furniture_props→90 等
  - 新カテゴリ: transportation_interior(50) / shop_restaurant(50) / school_facility(45) / seasonal_scenery(53)
- **NSFWタグ本格拡充（v13.2）**: 02_全タグ.txt（66行リアルSDプロンプト集）参考に4エージェント並列で大幅拡充
  - NSFW合計: 3,812→5,239（+1,427タグ）、27→29カテゴリ
  - nsfw_positions 450→621(+171) / nsfw_acts 500→670(+170)
  - nsfw_body_details 170→257(+87) / nsfw_body_reactions 145→230(+85)
  - nsfw_fluids 40→102(+62) / nsfw_expression_sex 200→284(+84)
  - nsfw_clothing_states 112→202(+90) / nsfw_scenarios_detailed 141→232(+91)
  - nsfw_camera_angles 100→167(+67) / nsfw_clothing 92→157(+65)
  - nsfw_aftermath 95→161(+66) / nsfw_aftermath_detailed 65→115(+50)
  - nsfw_bdsm 265→335(+70) / nsfw_fetish 230→299(+69)
  - nsfw_foreplay 225→280(+55) / nsfw_toys_detailed 100→145(+45)
  - 新カテゴリ: nsfw_clothed_sex(50) / nsfw_nipple_play(50)

#### 設定スタイル自動検出（SETTING_STYLES）
- コンセプトのキーワードからSD背景タグの世界観を自動補正
- 3スタイル: traditional_japanese_rural / traditional_japanese_urban / fantasy_medieval
- `_detect_setting_style()`: コンセプト→スタイル自動判定
- `enhance_sd_prompts()`: タグ置換(bed→futon等) + 禁止タグ除去(concrete等) + 雰囲気タグ追加(tatami,shoji等)
- `generate_scene_draft()`: プロンプトに「背景スタイル必須」ヒント行追加
- 例: 「夜這い風習のある村」→ 和風田舎タグ自動適用、現代建材タグ自動除去

### Changed
- danbooru_tags.json: version 13.0→13.2

---

## [2.5.0] - 2026-02-10

### Added (プリセット200体到達 + タグDB v13.0)
- **プリセットキャラ100→200体（+100体）**: 12エージェント並列作成
  - ジャンプ+10 / ジャンプ++3 / マガジン+5 / ラノベ+10 / アニメ+15 / ソシャゲ+15
  - ゲーム+22（P5/FF7/ゼノブレイド/FE/DQ/DOA/崩壊/グラブル/ニーア）
  - サンデー+10（らんま/犬夜叉/コナン/マギ/ハヤテ/みなみけ/うる星やつら）
  - VTuber+10（にじさんじ5/ホロライブ5）
- **新GUIカテゴリ**: ゲーム(#6B8E23) / サンデー(#FF8C00)
- **タグDB v13.0（12,003→14,000タグ、+1,997）**: 158→162カテゴリ
  - 新カテゴリ4個: nsfw_fluids / sky_colors / building_architecture / room_furniture
  - 重点拡充: nsfw_expression_sex 125→200 / time_of_day 45→110 / locations 474→602

### Changed
- GUI: カテゴリ別キャラ数を動的表示

---

## [2.4.0] - 2026-02-09

### Added (プリセット100体到達)
- **プリセットキャラ57→100体（+43体）**
  - カテゴリ別: ジャンプ21 / ジャンプ+5 / マガジン7 / ラノベ15 / アニメ15 / ソシャゲ30 / VTuber7

---

## [2.3.0] - 2026-02-09

### Changed (Grokバックエンド削除 + タグDB v8.0)
- **Grok(xAI)バックエンド完全削除** → Claude API単一バックエンド
- **タグDB v8.0（3,392→5,146タグ、86→121カテゴリ）**: 35新カテゴリ追加

---

## [2.2.0] - 2026-02-09

### Added (プリセット拡張 + UI/UX大幅改善)
- **プリセットキャラ33→57体（+24体）**
- **プリセットタブ**: カテゴリチップフィルタ→作品ドロップダウン→キャラカードリスト
- **オリジナル作成タブ**: テンプレートクイックスタート、MaterialCardセクション分割、性格チップグリッド

---

## [2.1.0] - 2026-02-09

### Fixed (品質大幅改善)
- JSONテンプレートから文字数ヒント全除去（出力漏れ防止）
- `generate_outline`: intensity 5を最大2シーンに自動制限
- `auto_fix_script()`: 文字数マーカー除去/キャラ名統一/SDタグ括弧修正
- `extract_scene_summary`: 使用済みbubbles+SE追跡で重複防止強化
- SDプロンプト: quality括弧修正、外見タグ括弧外配置
- v2.1.1: クロスシーン重複除去、使用禁止リスト明示化、description品質指示強化

---

## [2.0.0] - 2026-02-09

### Added (品質検証 + SD最適化 + UX改善)
- `validate_script()`: FANZA基準ローカル自動検証
- `enhance_sd_prompts()`: SDプロンプト後処理最適化
- フェーズインジケーター5段階化
- CTkComboBox→CTkOptionMenu全面移行
- ウィンドウ閉じ保護 / ショートカット(Ctrl+Enter,Esc) / フォルダ開くボタン
- セリフスキル4種自動選択（nomal/ohogoe/jyunai/tundere）
- cg_visual_variety / nsfw_scene_composer / eromanga_serihu_sensei スキル追加

---

## [1.6.1] - 2026-02-09

### Fixed
- **JSONパースエラー時のリトライ機構**: コンテンツ拒否だけでなくJSONパースエラー時も最大2回リトライ
- **error_result フォーマット修正**: dialogue→bubbles+onomatopoeiaに統一
- **説明的な吹き出し禁止ルール追加**: thought吹き出しのNG例を具体的に明示
  - ❌「彼氏に...ごめん...」（反省文）→ ✅「彼より…」（感情断片）
  - ❌「彼のことなんて...忘れてしまった」（ナレーション）→ ✅「もう…戻れない」（状態暗示）
- **画像+吹き出しで状況伝達テクニック**: description不要で伝わるspeech例を追加

---

## [1.6.0] - 2026-02-08

### Changed (CG集フォーマット対応 - 根本改修)
- **dialogue → bubbles フォーマット変更**: 小説/脚本式セリフからFANZA CG集の吹き出し形式に全面移行
  - 旧: `dialogue: [{speaker, emotion, line, inner_thought}]` 4-6個 / 各15文字
  - 新: `bubbles: [{speaker, type, text}]` 1-4個 / 各1-10文字
  - type: `speech`（会話）/ `moan`（喘ぎ）/ `thought`（心の声）
- **onomatopoeia フィールド追加**: 画像上の効果音テキスト（0-4個）
  - intensity別目安: 1-2: なし〜1個, 3: 1-2個, 4-5: 2-4個
  - 例: ズブッ, ヌチュ, パンパン, ビクビクッ, ドクドクッ
- **システムプロンプト全面書き換え**
  - 「FANZA同人CG集とは」セクション追加（画像メイン・テキストサブの理解を促す）
  - 「吹き出しの書き方」鉄則（1-10文字、句読点不要、状況説明禁止）
  - 「良い例 vs 悪い例」を具体的に提示
  - intensity別の吹き出し・オノマトペ指針を刷新
- **エクスポート対応**
  - CSV: カラム名変更（bubble_no, speaker, type, text, onomatopoeia）
  - Excel: ヘッダー変更（吹き出しNo, 話者, 種類, テキスト, オノマトペ）
  - 旧dialogue形式のJSONも自動互換読み込み対応
- **関連関数の更新**
  - `generate_scene_draft`: プロンプト・出力形式を完全刷新
  - `generate_scene_batch`: 同上（バッチ版）
  - `polish_scene`: 清書ルールをCG集吹き出し形式に
  - `extract_scene_summary`: bubbles対応（旧dialogue互換あり）

---

## [1.5.0] - 2026-02-08

### Added (ストーリーファースト・パイプライン)
- **generate_synopsis**: コンセプトから400-600字の完全なストーリーあらすじを生成（Haiku 1回）
  - あらすじはファイル保存（context/synopsis_*.txt）
- **generate_outline API化**: あらすじを忠実にシーン分割（Haiku 1回、旧テンプレート→API化）
  - シーン配分: 導入20% / 展開 / 本番40% / 余韻10%
  - 各シーンにsituation, emotional_arc, beats, viewer_hookを追加
  - ルール7-8: 同パターン繰り返し禁止、連続同locationの禁止
- **generate_scene_draft**: synopsisパラメータ追加、あらすじ全文をプロンプトに注入
- **compact_context_local**: コンセプト80文字切り捨て制限を撤廃
- **コンテンツリフューズ対策**: Haiku拒否時にリトライ機構追加
- **あらすじ制約**: 「コンセプトにない極端な展開は絶対に追加しない」ルール追加

### Changed
- パイプライン: 2フェーズ→4フェーズ（圧縮→あらすじ→分割→シーン生成）
- コスト見積もりUI更新（prep_calls=2: あらすじ+分割）

---

## [1.4.2] - 2026-02-08

### Fixed (ストーリー連続性 - 根本修正)
- **バッチ生成を廃止**: Haiku max_tokens上限(4096)超過でシーン1-4が全滅していた致命的バグ
- **完全シーケンシャル生成に統一**: 全シーンを1つずつ順番に生成（確実性最優先）
- **ストーリー蓄積システム**: 各シーン生成後に要約を抽出→次シーンのプロンプトに「⚠️ ストーリーの連続性（最重要）」として注入
  - `extract_scene_summary()`: タイトル・描写・主要セリフ・心情・流れを1行要約（ローカル・API不要）
  - `story_so_far`: 直近5シーン分の蓄積要約をプロンプト冒頭に注入
  - 「前シーンの流れを必ず引き継ぐ」ルールをAPIに明示

---

## [1.4.0] - 2026-02-08

### Added (API大幅節約 + 新テーマ + UX改善)
- **compact_context ローカル化**: プリセット/カスタムキャラ使用時はAPIを呼ばずローカルでcontext構築（-1 API呼び出し/生成）
- **Low-Intensity バッチ生成**: intensity 1-3のシーンを2個ずつまとめてHaiku 1回で生成（約-3~4 API呼び出し/生成）
- **コスト事前見積もり**: 生成開始前にintensity分布・API回数・推定コストを表示
- **新テーマ6種追加**（計16テーマ）:
  - 催眠・洗脳: 暗示→無意識→覚醒しても体が覚えている
  - 異種姦・モンスター: 遭遇→捕獲→異種交配→快楽堕ち
  - 時間停止: 停止→観察→いたずら→解除の瞬間
  - ハーレム: 出会い→好意集中→争奪→全員で奉仕
  - 女性優位・痴女: 主導権掌握→翻弄→支配→ご褒美
  - 近親相姦: 家族の日常→意識→禁断→堕ちる
- **プリセットキャラ自動検索強化**: presets/characters/ も自動スキャン対象に

### Changed
- `generate_pipeline`: キャラプロファイル読み込みをcompact_contextより前に移動
- バッチ生成失敗時は自動で個別生成にフォールバック
- アウトラインの場所候補に新テーマ6種分を追加

### Performance
- 10シーン生成時の推定API呼び出し: 11回 → 約6-7回（約40%削減）
- compact_context API廃止（プリセット使用時）: Haiku 1回分削減
- バッチ生成: Haiku 3-4回分削減

---

## [1.3.0] - 2026-02-08

### Added (オリジナルキャラビルダー + UI刷新)
- **オリジナルキャラクター作成機能（API不要）**
  - 12種の性格アーキタイプ: ツンデレ、ヤンデレ、クーデレ、天然、小悪魔、お姉さん、妹系、真面目、ギャル、お嬢様、元気っ子、大和撫子
  - ドロップダウン選択: 年齢外見(8種)、関係性(22種)、一人称(7種)、口調(8種)、髪色(11色)、髪型(13種)、体型(8種)、胸サイズ(5段階)、服装(20種)、恥ずかしがり度(5段階)
  - 追加特性の自由入力対応
  - Danbooruタグ自動生成（外見選択から20タグ自動構築）
- **`char_builder.py`**: 選択肢定数 + アーキタイプテンプレート + ビルド関数
- **3タブ構成UIに刷新**: プリセット / オリジナル作成 / API生成
- **「その他の登場人物」テキストエリア**: 男主人公やサブキャラの設定欄を追加
- プロファイル保存/復元に「その他の登場人物」を追加

---

## [1.2.0] - 2026-02-08

### Added (プリセットキャラクター機能)
- **プリセットキャラ33体同梱（API呼び出し不要）**
  - ジャンプ: 鬼滅の刃（禰豆子、胡蝶しのぶ、甘露寺蜜璃）、ワンピース（ナミ、ハンコック）、呪術廻戦（釘崎野薔薇）、ヒロアカ（麗日お茶子）、チェンソーマン（マキマ、パワー）
  - ジャンプ+: SPY×FAMILY（ヨル）、推しの子（星野アイ）
  - マガジン: 五等分の花嫁（中野三玖）
  - ラノベ: このすば（めぐみん、アクア）、リゼロ（レム、エミリア）、無職転生（ロキシー）、SAO（アスナ）、陰実（アルファ）
  - アニメ: ぼざろ（後藤ひとり）、リコリコ（錦木千束）、ダンジョン飯（マルシル）、水星の魔女（スレッタ）、フリーレン
  - ソシャゲ: ブルアカ（アロナ、早瀬ユウカ）、原神（甘雨、雷電将軍）、FGO（マシュ、アルトリア）、ウマ娘（ライスシャワー、ゴールドシップ）
  - VTuber: ホロライブ（兎田ぺこら）
- **プリセット選択UI**: ドロップダウンから選択→即読み込み（APIキー不要）
- **バックエンド**: `get_preset_characters()`, `load_preset_character()` 追加
- **build_character()**: プリセット自動検出（API呼び出しスキップ）
- **presets/preset_index.json**: プリセット一覧管理（カテゴリ別ソート）

### Changed
- キャラ生成カードに「プリセットキャラ（API不要）」セクション追加
- 人気キャラ33体はAPI代ゼロで即使用可能に

---

## [1.1.0] - 2026-02-07

### Added (タグDB v5.0 + API大幅節約)
- **タグDB v5.0（765→1093エントリー、+43%）**
  - 18新カテゴリ追加: character_archetypes, age_appearance, relationship_types, scenario_tags, theme_specific_tags, variation_tags, special_views, camera_angles, visual_effects, text_effects, skin_details, background_details, era_setting, panty_types, foot_wear, makeup_details, scene_transitions, theme_tag_sets
  - 既存カテゴリ拡張: locations(+15), body_types(+9), hair_styles(+9), accessories(+7), nsfw_body_details(+8), quality_positive(+4)
  - 合計47カテゴリ

### Changed (API節約)
- **generate_outline**: API呼び出し廃止→ローカルテンプレート生成（THEME_GUIDES + 黄金比率シーン配分で代替）
- **polish_scene**: パイプラインから除去（intensity 4-5はSonnet生成済みで十分高品質）
- **char_guide**: intensity別圧縮（1-2: 基本のみ, 3: +感情, 4-5: フル）
- 推定削減: API呼び出し2-3回/生成 + トークン20-25%削減

---

## [1.0.0] - 2026-02-07

### Added (API節約・タグ充実・プロンプト統合)
- **Anthropic Prompt Caching対応** - systemプロンプトの共通部分をキャッシュ化（コスト最大60%削減）
  - `call_claude`がキャッシュ統計ログを出力
  - `generate_scene_draft`でjailbreak+skill+char_guideをキャッシュ対象に分離
- **sd_background廃止 → sd_promptに統合**
  - 背景タグをポジティブプロンプトに統合
  - 品質タグ`(masterpiece, best_quality:1.2)`を自動付与
  - `deduplicate_sd_tags()`で重複タグ自動排除
- **negative_prompt出力廃止** - 固定値のため生成不要
- **danbooru_tags.json v2.0（全258エントリー）**
  - 場所: 51種 / 表情: 26種 / ポーズ: 5段階×4カテゴリ
  - 衣装: 34種 / 脱衣: 10段階 / エフェクト: 16種
  - 髪型: 13種 / 髪色: 11色 / 目色: 8色 / 体型: 7種
  - アクセサリー: 14種 / 照明: 11種 / 天候: 8種
  - NSFW行為: 20種 / 射精: 6種 / 構図: 5段階
- **max_tokens最適化**: 3000→2500（出力効率向上）

### Changed
- `export_csv/excel`: sd_background+negative_prompt削除（SDプロンプト1列のみ）
- `polish_scene`: 保持フィールド簡素化

---

## [0.9.2] - 2026-02-06

### Changed (UX改善)
- **プロファイル管理をキャラ生成より上に配置**
- **入力欄の改善**
  - フォントサイズ14pxに拡大（読みやすさ）
  - 背景色を明るく（SURFACE_CONTAINER_LOWEST）
  - ラベルを太字+説明文追加
  - コンセプト120px、登場人物90pxに拡大
- 角丸を6-10dpに統一
- パディング/マージン微調整

---

## [0.9.1] - 2026-02-06

### Fixed (UX改善)
- **1カラムレイアウトに戻す** - 2カラムは使いづらかった
- **角丸を12dp以下に統一** - 28dpはダサかった
- **入力欄を大きく**
  - コンセプト: 100px
  - 登場人物: 80px
- ヘッダーをシンプルに（56px高さ）
- カード間のスペーシング調整

### UI/UX原則
- 使いやすさ > 見た目
- 十分な入力スペース確保
- 一貫した視覚階層

---

## [0.9.0] - 2026-02-06

### Added
- **Google風 UI 大幅刷新**
  - Top App Bar（Primary色ヘッダー）
  - Hero Section（プログレス+生成ボタン）
  - ~~2カラムレイアウト~~ (0.9.1で1カラムに戻す)
  - モダンなフェーズインジケーター（ピル型）
  - Secondary Container使用のキャラ生成カード

### Changed
- ウィンドウサイズ拡大（820x950）
- 生成ボタンを画面上部に移動（Hero Section）
- ~~カード角丸を28dp/16dpに統一~~ (0.9.1で12dp以下に)
- ~~入力フィールドのborder廃止~~ (0.9.1でborder復活)
- プログレスバーをHero内に配置
- ログをダークテーマ（Inverse Surface）に

### UI/UX
- より直感的なレイアウト
- 視認性の高いフェーズ表示
- コンパクトなフッター

---

## [0.8.0] - 2026-02-06

### Added
- **Material You / M3 UI リファクタリング**
  - M3 Dynamic Color System（Tonal Palette）
  - `MaterialFAB` コンポーネント（small/regular/large）
  - `MaterialChip` コンポーネント（filter/input/suggestion）
  - Supporting text機能追加（TextField）
  - Error state機能追加（TextField）

### Changed
- `MaterialColors`: M3準拠のTonal Palette実装
  - Primary/Secondary/Tertiary Container
  - Surface Container階層（5段階）
  - Inverse colors追加
- `MaterialButton`: M3ボタンバリアント追加
  - filled_tonal, elevated追加
  - corner_radius: 20dp（M3標準）
- `MaterialCard`: 3バリアント対応
  - elevated, filled, outlined
  - 12dp corner radius
- `MaterialTextField`: M3 filled/outlined対応
- `Snackbar`: M3準拠（4dp corners, action button）

### UI Guidelines Applied
- Google fonts（Segoe UI fallback）
- Touch targets ≥48dp
- Proper M3 color tokens

---

## [0.7.0] - 2026-02-06

### Added
- **テーマベース脚本生成システム**
  - 10種類のテーマガイド（NTR、凌辱、強制、純愛、和姦、堕ち、痴漢、上司OL、先生生徒、メイド）
  - テーマ別ストーリーアーク自動適用
  - テーマ別感情表現ガイド
  - テーマ別セリフトーン指示
- **Danbooruタグ強化**
  - `danbooru_nsfw_tags.skill.md` スキル追加
  - テーマ別SDタグ自動追加
  - テーマ別表情タグ自動追加
- **♡使用制御**
  - テーマ別 `use_heart` フラグ
  - NTR/凌辱系では♡を自動無効化

### Changed
- `generate_outline`: テーマパラメータ追加、テーマ別アーク適用
- `generate_scene_draft`: テーマ別セリフトーン・SDタグ適用
- `generate_pipeline`: テーマ情報のログ出力追加

### Fixed
- テーマが脚本生成に反映されない問題を修正

---

## [0.6.0] - 2026-02-06

### Added
- **UIデザインブラッシュアップ**
  - アクセントカラー（ピンク）追加
  - 生成ボタンを大型化・目立たせる（xlarge, accent）
  - プログレスバー強化（大きく、色変更）
  - ログ表示改善（ダーク背景、視認性向上）
  - カード折りたたみ機能（API設定、プロファイル管理）
  - バージョン表示追加

### Changed
- カラーパレット強化
  - PRIMARY: より鮮やかな紫 `#7C3AED`
  - ACCENT: ピンク `#EC4899`
  - SURFACE_VARIANT: 薄紫 `#F3E8FF`
- MaterialButton: size/variant拡張（accent, danger, success, xlarge）
- MaterialCard: collapsible/accent対応
- Snackbar: ダーク背景でモダンに
- アプリ名「Daihon Rakku」に変更

---

## [0.5.0] - 2026-02-06

### Added
- **ストーリー性強化**
  - シーン詳細説明（description）100字
  - 場所詳細（location_detail）
  - キャラ心情（character_feelings）
  - 心の声（inner_thought）各セリフに追加
  - ストーリーフロー（story_flow）次シーンへの繋がり
  - 視聴者興奮ポイント（viewer_hook）
- **背景SDプロンプト強化**
  - sd_background: 背景専用タグ（人物なし生成用）
  - 場所別タグテンプレート（教室、寝室、浴室等）
  - 時間帯別タグ（朝、放課後、夜等）
- **Excel出力機能**
  - openpyxl対応
  - 折り返し表示自動設定
  - 列幅最適化
  - ヘッダー固定

### Changed
- generate_outline: 4幕構成（導入→展開→本番→余韻）
- generate_scene_draft: 背景タグ自動生成
- export_csv: 新フィールド対応（16カラム）

### Fixed
- JSONパースエラー修正（モデルの前置きテキスト除去）

---

## [0.4.0] - 2026-02-06

### Added
- **キャラクター自動生成システム**
  - 作品名＋キャラ名入力でキャラバイブル自動生成
  - Sonnetによる高品質キャラ分析
  - エロシーン用設定（when_aroused, when_climax, moaning_light等）
  - Danbooruタグ20個自動生成
  - .skill.md自動生成
- **プロファイル管理機能**
  - 設定の保存/読込
  - プロファイルのコピー/削除
- **キャラ設定プレビュー**
  - キャラ選択時にログに詳細設定表示

### Changed
- analyze_character: Sonnet使用で高品質化
- generate_scene_draft: intensity別モデル選択（4+でSonnet）
- generate_scene_draft: キャラプロファイルフル活用
- 5段階エロ指示（intensity 1-5）

### Fixed
- キャラ名部分一致対応
- APIタイムアウト設定（120秒）
- 順次処理で安定化

---

## [0.3.0] - 2026-02-06

### Added
- Material Design 3 UIデザイン
  - カスタムコンポーネント: MaterialCard, MaterialButton, MaterialTextField
  - Snackbar通知システム
  - ダークテーマカラーパレット
- 「💾 設定を保存」ボタン追加
- material_design.skill.md スキル追加

### Changed
- UIデザイン全体をMaterial Design 3準拠に刷新
- ボタンスタイル: filled / outlined バリアント
- カード型レイアウトでセクション分割
- 角丸・スペーシングをMaterial Design仕様に統一

---

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
