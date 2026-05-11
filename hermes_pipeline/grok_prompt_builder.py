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

【英語版の冒頭タグについて】
English version の最初の行に、シーン情報「機械タグ参照」に含まれる
キャラクター名タグ（例: nakano_ichika）と作品名タグ（例: go-toubun_no_hanayome）を
アンダースコア表記のまま列挙してください（例: `nakano_ichika, go-toubun_no_hanayome,`）。
これは Anima (Danbooru 学習) のキャラ認識精度を担保するためです。

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
{danbooru-style character & series tags here, e.g. `nakano_ichika, go-toubun_no_hanayome,`}

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
