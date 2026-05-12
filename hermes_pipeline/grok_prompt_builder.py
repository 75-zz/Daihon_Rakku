"""Scene 構造化データ → Grok web 投入用テキスト

ユーザー提示の FANZA脚本テンプレートをベースに、Daihon の各シーン情報
(日本語desc / 英語自然言語 / 機械タグ / 擬音 / セリフ群) を組み立てる。
末尾に「日英両セクションで出力」指示を追加し、ComfyUI/Anima 投入用の
英語版と人間チェック用の日本語版の両方を Grok に書かせる。
"""

from __future__ import annotations

from .parser import Bubble, Scene


_TEMPLATE_HEADER = """あなたはFANZA同人エロ漫画専用の高精度脚本エンジニアです。

以下のシーンを、Animaで再現性が高く、情報量をしっかり保ち、直後感が明確に伝わる脚本に変換してください。

【必須ルール】
各キャラクターごとに【キャラクター名】セクションを作成
位置・姿勢・手・脚・膝・腰・視線・表情・服装状態・布の掛かり方をできるだけ詳細に記述
動作の直後感を最優先で明確に表現する（特に脱衣シーンでは「引き下ろした直後」「まだ手が残っている」「布がまだ肌に絡まっている」など動きの余韻を必ず入れる）
主要な位置関係・距離感・体重移動は必ず具体的に入れる（距離約50cm、やや手前、背中を壁にぴったり押しつけて、重心を後ろに預けるなど）
手の描写は自然で視覚的にわかりやすい範囲で詳細に書いてOK（最大3文以内を目安）
表情は眉・目・口・頬・涙・感情のニュアンスをしっかり入れて明確に
脚・膝・腰の状態も必ず詳細に
服装状態は特に厳密に記述（何がどうなっているかをすべて明記）
【構図】セクションは必ず作成
※【禁止事項】セクションは作らない（ネガティブプロンプトは下流で別途付与する）

【重要方針】
情報量を減らしすぎない（元の脚本の詳細さを最大限維持）
「直後感」の表現を最優先事項の一つとする（AIが動きの瞬間を捉えられるようにする）
服装の指定と位置関係の具体性も最優先
Animaが読みやすい自然言語を心がける
表情は感情のニュアンスを必ず含める
立ちシーン・セックスシーン・全裸シーンのすべてに対応

【キャラクタータグ生成は禁止】
あなたは**キャラクターの視覚特徴 (髪色・髪長・目色・体型・アクセサリ等)
を表す Danbooru タグを一切出力しないでください**。

- ❌ 禁止: `short_hair`, `long_hair`, `pink_hair`, `orange_hair`, `brown_hair`,
  `blue_eyes`, `large_breasts`, `medium_breasts`, `earrings`, `hair_ribbon`,
  `bangs`, `asymmetrical_sidelocks`, `hair_between_eyes`, `1girl`, `1boy`,
  `solo`, `nakano_ichika`, `go-toubun_no_hanayome` などキャラ識別タグ全般。

理由: キャラの正規 Danbooru タグは Daihon Rakku 側 (character.json) で確定済みで、
下流の prepare_prompt.py が **正しい** タグを強制挿入します。あなたが
キャラタグを生成すると、原作と矛盾するタグ (例: 一花の `orange_hair` は誤り、
正しくは `pink_hair`) が混入し、画像生成が破綻します。

あなたの担当は **構図・ポーズ・服装の状態・動作・表情・直後感・物理的距離・
照明・雰囲気** のみです。これらは自然言語で詳細に記述してください。

【男性キャラ（竿役）の扱い】
シーン内の男性キャラは**必ず顔が描かれない前提**で記述してください。
顔は影・フレームアウト・後頭部・俯瞰での顔切れ・腕や手だけが映る等。
キャラ識別タグ (`faceless_male`, `1boy`) は禁止ですが、自然言語で
「the male's face is out of frame」「shadowed face」「only his arm visible」など
顔なし状態を**必ず明示**してください。`handsome man face` のような
明示的に顔を描く記述は厳禁。

【セリフ・吹き出しタグ完全禁止】
English version 本文中に Danbooru タグとして **以下のタグを絶対に出力しないでください**:
  `speech_bubble`, `dialogue`, `speech`, `talking`, `comic`, `caption`,
  `onomatopoeia`, `sound_effect`, `text`, `subtitle`
理由: CG集台本は 1P1枚で吹き出しなし。AI が画面内テキストを描画してしまうため。
セリフ・心の声・擬音の情報は「日本語版」セクション内に書くか省略してください。
英語版では「Right after saying ..., she...」のように状況描写に統合する形は可。
ただし**タグ列挙はしない**。

【ロングヘアでないキャラのクローズアップ構図ガイダンス】
キャラの髪が短くても長くても、クローズアップ・vertical close-up 等で
画面が顔だけになると AnimaYume が学習時のクローズアップ画像に引きずられ
キャラ特徴 (髪色・髪長・サイドロックの非対称性等) が破綻しやすいです。
Composition では「**upper body shot**」「**bust shot**」「**medium shot**」など
**頭部全体と肩から胸まで**が画面内に収まるショットを優先指定してください。
`tight close-up`, `face close-up` を多用すると破綻のリスクが高まります。

【衣装ロック — ヒロイン (アイテム種類変更禁止 / 状態変化は許可)】

ヒロインの**ベース衣装 (アイテム種類)** は Daihon Rakku 側 (character.json) で固定済みです:
  - 白ブラウス (white_shirt / white_blouse) + 緑スカート (green_skirt)

あなたは自然言語で**別のアイテム種類**に変更してはいけません:
  ❌ 禁止: kimono, furisode, sweater, off-shoulder sweater, camisole, denim skirt,
          swimsuit, bikini, school sailor uniform (セーラー服), dress, T-shirt, hoodie
  → 「学校指定の白いブラウス」等の説明は OK ですが、別のアイテム名に置き換えてはいけません。

ただし**衣装の状態変化**は CG 集の見せ場として積極的に描写してください (むしろ必須):
  ✅ 推奨: half-undressed, partially_undressed, slipped off one shoulder, open_clothes,
         clothes_lifted, unbuttoned (third button / all buttons), bra_visible, bra_strap,
         panties_visible, panties_aside, panties_around_one_leg, skirt_lifted,
         hiked_up_skirt, bare_shoulders, exposed_collarbone, exposed_midriff,
         breasts_out, nipples_visible, torn_pantyhose, stockings_pull_aside,
         disheveled_clothes, wrinkled
  → 「ブラウスのボタンが3つ外れて胸元が大きくはだけ、白いレースブラが露出」のように
     ベース衣装名 (ブラウス / スカート) は維持しつつ状態を細かく描写してください。

【衣装ロック — 男性 (アイテム種類変更禁止 / 状態変化は許可)】

男性キャラのベース衣装も Daihon Rakku 側で固定:
  - 黒Tシャツ (black_shirt / t-shirt / short_sleeves) + 黒パンツ (black_pants) + 筋肉質 (muscular)

❌ 禁止: white shirt, suit, jacket, hoodie, dress shirt, blazer, school uniform, kimono
✅ 状態変化 OK: rolled up sleeves (袖まくり), open shirt, unbuttoned shirt, shirtless,
              bare chest, exposed abs, unbuckled belt, pants pulled down,
              pants around thighs, veiny arms

【Clothing state セクション省略禁止 (重要)】

English version の Faceless Male セクションと Nakano Ichika セクションでは
**必ず "Clothing state:" 行を出力**してください。省略禁止。
シーンの進行段階 (fully dressed → unbuttoned → half-undressed → exposed) を毎シーン明記。
これを省略すると、AI が前シーンの context を誤って継承し服色が変わる事故が起きます。

【Composition セクションのライティング明示】

[Composition] セクション内に**ライティング指定を必ず1文以上**含めてください:
  例: "Dim room with soft evening light", "Bright daylight from window",
     "Warm sunset glow through curtains", "Cool moonlight from above"
未指定だとモデルがデフォルトのフラット照明を選び絵柄がブレます。

【Grok に積極的に描いてほしいエロ表現リスト (期待リスト)】

本プロジェクトでは Grok のエロ描写力が最大の資産です。以下は**禁止リストではなく期待リスト**:

ヒロイン側:
  - ずらし系: パンティずらし、片足パンティ、パンティ脇からはみ出し、スカートまくり上げ
  - 半脱ぎ系: ボタンずらし、肩出し、胸チラ、ブラずれ、ストッキング破れ
  - 露出: 乳首見え、おっぱい全出し、おマンコ見え (角度に応じて)
  - 体液: 汗、涎、涙、潤み目、唾液、愛液
  - 表情: ahegao 寄りトランス、虚ろ目、口半開き、頬染め最大

男性側:
  - 勃起描写: erection, large_penis, glans, throbbing
  - 体液: precum, semen, ejaculation (シーン進行に応じて)
  - 行為: 触手、フィンガリング、口淫、挿入、騎乗、後背位 (シーンに応じて)

CG集として読者を性的興奮させることが第一目的。シーン進行に応じて遠慮せず描写してください。
ただし**キャラ視覚特徴と衣装アイテム種類は変更禁止** (上記ロックルール) です。

【出力フォーマット】
以下の2セクションを必ず両方出力してください。

# 日本語版（人間チェック用）
{各キャラクター名}
位置・姿勢:
手・脚・膝・腰:
視線・表情:
服装状態:
直後感:
（必要に応じて他キャラも同様に）

【構図】

# English version (ComfyUI / Anima 投入用)
（このセクションの冒頭にキャラタグ行は不要です — Daihon Rakku 側で正規タグが
強制挿入されます。あなたは下記のキャラ別の自然言語記述から始めてください。）

{Character name in romaji or English}
Position & posture:
Hands / legs / knees / hips:
Gaze & expression:
Clothing state:
Immediate aftermath / momentary cue:
(repeat for other characters if any)

[Composition]

英語版は Anima (Cosmos-Predict2 / Qwen3 TE) が読みやすい自然言語で書き、
タグ列ではなく文章ベースにしてください（冒頭のキャラ・作品名タグを除き、
本文中の Danbooru系タグの単語混在は可）。
"""


def _format_bubbles(bubbles: list[Bubble]) -> str:
    if not bubbles:
        return "（セリフ・思考なし）"
    lines = []
    for b in bubbles:
        is_thought = b.text.startswith("（") and b.text.endswith("）")
        kind = "心の声" if is_thought else "セリフ"
        lines.append(f"  - [{b.bubble_no}] {b.speaker}（{kind}）: {b.text}")
    return "\n".join(lines)


def build_scene_section(scene: Scene) -> str:
    """1シーン分の「シーン情報」セクションを組み立てる。"""
    title = f"Scene {scene.scene_id}"
    if scene.sd_title:
        title += f" — {scene.sd_title}"

    parts = [
        f"━━━━━ シーン情報 ━━━━━",
        f"■ シーン番号: {title}",
        "",
        "■ 日本語シーン描写（Daihon原典）:",
        scene.description or "（記載なし）",
        "",
        "■ 英語自然言語シーン描写（Daihon SD出力）:",
        scene.sd_natural_en or "(none)",
        "",
        "■ 機械タグ参照（Danbooru系、LoRA除去済）:",
        scene.sd_prompt or "（記載なし）",
    ]
    if scene.onomatopoeia:
        parts += ["", "■ 擬音:", scene.onomatopoeia]
    parts += [
        "",
        "■ セリフ・心の声（表情・テンションの手がかり）:",
        _format_bubbles(scene.bubbles),
        "━━━━━━━━━━━━━━━━━━━━━━",
    ]
    return "\n".join(parts)


def build_grok_input(scene: Scene) -> str:
    """Grok web チャット欄にコピペできる単一テキストを返す。"""
    scene_section = build_scene_section(scene)
    return f"{_TEMPLATE_HEADER}\nシーン情報：\n\n{scene_section}\n"
