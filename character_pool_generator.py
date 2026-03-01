"""
character_pool_generator.py
ローカルでキャラ固有セリフプールを生成（API不要・即座）
"""

import re
import random
from typing import Optional

from ero_dialogue_pool import (
    MOAN_POOL,
    SPEECH_FEMALE_POOL,
    THOUGHT_POOL,
    SCENE_PHASE_SPEECH_MAP,
)

# ============================================================================
# 性格タイプ検出（gui.py _detect_personality_type と同等ロジック）
# ============================================================================

_PERSONALITY_KEYWORDS = {
    "tsundere": ["ツンデレ", "ツン", "tsundere"],
    "submissive": ["ドm", "どm", "masochist", "従順", "submissive", "奴隷", "ペット", "服従", "受け身"],
    "sadistic": ["ドs", "どs", "sadist", "サキュバス", "succubus", "小悪魔", "女王", "支配", "強気"],
    "ojou": ["お嬢様", "令嬢", "高貴", "ojou", "noble", "上品", "princess", "姫"],
    "gal": ["ギャル", "gal", "黒ギャル", "パリピ", "チャラい"],
    "seiso": ["清楚", "純粋", "清純", "天然", "innocent", "文学少女"],
    "genki": ["元気", "活発", "体育会", "ボーイッシュ", "energetic", "スポーツ"],
    "kuudere": ["クーデレ", "kuudere", "無表情", "無口", "クール", "cool"],
    "inkya": ["陰キャ", "オタク", "otaku", "引っ込み", "内向", "根暗", "introvert"],
}


def detect_personality_type(bible: dict) -> str:
    """bibleから性格タイプを判定"""
    personality = bible.get("personality_core", {})
    desc = personality.get("brief_description", "")
    traits = personality.get("main_traits", [])
    archetype = bible.get("archetype", "")
    all_text = f"{desc} {' '.join(traits)} {archetype}".lower()

    for ptype, keywords in _PERSONALITY_KEYWORDS.items():
        if any(k.lower() in all_text for k in keywords):
            return ptype
    return ""


# ============================================================================
# フェーズ別カテゴリマッピング（性格×フェーズ → SPEECH_FEMALE_POOL カテゴリ）
# ============================================================================

# 各フェーズでの基本カテゴリ（性格に関わらず使用）
_PHASE_BASE_CATEGORIES = {
    "intro": ["embarrassed"],
    "approach": ["denial", "embarrassed"],
    "foreplay": ["plea", "embarrassed", "insertion"],
    "penetration": ["insertion", "plea", "acceptance"],
    "climax": ["ecstasy", "beg", "receiving_climax"],
    "afterglow": ["afterglow", "post"],
}

# 性格タイプ別のカテゴリブースト（追加カテゴリ + ウェイト倍率）
_PERSONALITY_SPEECH_BOOST = {
    "tsundere": {
        "intro": [("denial", 2.0)],
        "approach": [("denial", 2.0), ("anger", 1.5)],
        "foreplay": [("denial", 1.5)],
        "penetration": [("acceptance", 0.5)],
        "climax": [("ecstasy", 1.5)],
        "afterglow": [("teasing", 1.5)],
    },
    "submissive": {
        "intro": [("embarrassed", 1.5)],
        "approach": [("embarrassed", 2.0)],
        "foreplay": [("plea", 2.0), ("submissive", 1.5)],
        "penetration": [("submissive", 2.0), ("beg", 1.5)],
        "climax": [("beg", 2.0)],
        "afterglow": [("post", 1.5)],
    },
    "sadistic": {
        "intro": [("teasing", 2.0), ("provoke", 1.5)],
        "approach": [("teasing", 2.0), ("provoke", 1.5)],
        "foreplay": [("provoke", 1.5)],
        "penetration": [("provoke", 1.0)],
        "climax": [("ecstasy", 1.5)],
        "afterglow": [("teasing", 2.0)],
    },
    "ojou": {
        "intro": [("ojou_formal", 2.0)],
        "approach": [("ojou_formal", 1.5), ("embarrassed", 1.5)],
        "foreplay": [("embarrassed", 2.0)],
        "penetration": [("plea", 1.5)],
        "climax": [("ecstasy", 1.5)],
        "afterglow": [("ojou_formal", 1.5)],
    },
    "gal": {
        "intro": [("teasing", 1.5)],
        "approach": [("teasing", 1.5)],
        "foreplay": [("provoke", 1.0)],
        "penetration": [("acceptance", 2.0)],
        "climax": [("ecstasy", 2.0)],
        "afterglow": [("teasing", 1.5)],
    },
    "seiso": {
        "intro": [("embarrassed", 2.0)],
        "approach": [("embarrassed", 2.0), ("denial", 1.5)],
        "foreplay": [("embarrassed", 2.0), ("plea", 1.0)],
        "penetration": [("plea", 1.5)],
        "climax": [("ecstasy", 1.0)],
        "afterglow": [("embarrassed", 1.5)],
    },
    "genki": {
        "intro": [("teasing", 1.0)],
        "approach": [("embarrassed", 1.0)],
        "foreplay": [("acceptance", 1.5)],
        "penetration": [("acceptance", 2.0), ("beg", 1.5)],
        "climax": [("ecstasy", 2.0)],
        "afterglow": [("teasing", 1.0)],
    },
    "kuudere": {
        "intro": [("embarrassed", 0.5)],
        "approach": [("denial", 1.0)],
        "foreplay": [("embarrassed", 1.0)],
        "penetration": [("acceptance", 1.0)],
        "climax": [("ecstasy", 1.5)],
        "afterglow": [("post", 1.5)],
    },
    "inkya": {
        "intro": [("embarrassed", 2.0)],
        "approach": [("embarrassed", 2.0), ("denial", 1.5)],
        "foreplay": [("embarrassed", 2.0), ("plea", 1.0)],
        "penetration": [("plea", 2.0)],
        "climax": [("ecstasy", 1.5)],
        "afterglow": [("embarrassed", 2.0)],
    },
}

# 性格タイプ別のTHOUGHTカテゴリブースト
_PERSONALITY_THOUGHT_BOOST = {
    "tsundere": [("contradiction", 2.0)],
    "submissive": [("submission", 2.0)],
    "sadistic": [("self_surprise", 1.5)],
    "ojou": [("confusion", 2.0)],
    "gal": [("awakening", 1.5)],
    "seiso": [("confusion", 2.0), ("guilt", 1.0)],
    "genki": [("self_surprise", 1.5), ("body_awareness", 1.5)],
    "kuudere": [("self_surprise", 2.0)],
    "inkya": [("confusion", 2.0), ("guilt", 1.5)],
}

# フェーズ別のTHOUGHTベースカテゴリ
_PHASE_THOUGHT_CATEGORIES = {
    "intro": ["general"],
    "approach": ["general", "confusion"],
    "foreplay": ["body_awareness", "awakening", "self_surprise"],
    "penetration": ["body_awareness", "awakening"],
    "climax": ["general", "body_awareness"],
    "afterglow": ["general"],
}


# ============================================================================
# ヘルパー関数
# ============================================================================

def _extract_hiragana_fragments(text: str) -> list[str]:
    """テキストからひらがな断片を抽出"""
    return re.findall(r"[ぁ-ん]{2,}", text)


def _get_shyness(bible: dict) -> int:
    """bibleからshyness_levelを取得（デフォルト3）"""
    return int(bible.get("erotic_speech_guide", {}).get("shyness_level", 3))


def _get_first_person(bible: dict) -> str:
    """一人称を取得"""
    return bible.get("speech_pattern", {}).get("first_person", "私")


def _get_sentence_endings(bible: dict) -> list[str]:
    """語尾リストを取得"""
    endings = bible.get("speech_pattern", {}).get("sentence_endings", [])
    # 〜を除去して実際の語尾部分だけ取得
    return [e.lstrip("〜~") for e in endings if e.lstrip("〜~")]


def _replace_first_person(text: str, first_person: str) -> str:
    """一人称を置換（私→キャラの一人称）"""
    if first_person == "私":
        return text
    # 「私」だけ置換（「私たち」等は除外）
    return re.sub(r"私(?![たの]ち)", first_person, text)


def _adapt_ending(text: str, endings: list[str], probability: float = 0.3) -> str:
    """語尾適応: 確率で「…」の前にキャラ語尾を挿入"""
    if not endings or random.random() > probability:
        return text
    ending = random.choice(endings)
    # 「…」で終わるセリフの場合、語尾を挿入
    if text.endswith("…"):
        # 短すぎるものは変更しない
        if len(text) <= 3:
            return text
        return text[:-1] + ending + "…"
    return text


def _score_moan(moan: str, char_fragments: list[str], char_fillers: list[str],
                shyness: int, intensity: int) -> float:
    """喘ぎ声のキャラ適合度スコアリング"""
    score = 0.0

    # キャラの音断片と先頭一致
    moan_clean = re.sub(r"[…♡♥っッ]", "", moan)
    for frag in char_fragments:
        if moan_clean.startswith(frag[:2]):
            score += 2.0
            break
        if frag[:1] and moan_clean.startswith(frag[:1]):
            score += 1.0
            break

    # フィラーの音を含む
    for filler in char_fillers:
        filler_clean = re.sub(r"[…♡♥っッ]", "", filler)
        if filler_clean and filler_clean[:2] in moan_clean:
            score += 1.0
            break

    # shyness補正
    if shyness >= 4 and intensity <= 2:
        score += 1.5  # 恥ずかしがりは低intensityで高スコア
    elif shyness <= 2 and intensity >= 3:
        score += 1.5  # 大胆は高intensityで高スコア

    # ランダム要素で多様性確保
    score += random.random() * 0.5

    return score


def _postprocess_moan(moan: str, shyness: int, intensity: int) -> str:
    """shynessに応じた喘ぎ後処理"""
    if shyness >= 4 and intensity <= 2:
        # 恥ずかしがり×低intensity → ♡除去、…追加
        moan = moan.replace("♡", "").replace("♥", "")
        if not moan.endswith("…"):
            moan = moan.rstrip("っ") + "…"
    elif shyness <= 2 and intensity >= 3:
        # 大胆×高intensity → ♡確保
        if "♡" not in moan and intensity >= 4:
            moan = moan.rstrip("…") + "♡"
    return moan


# ============================================================================
# メイン生成関数
# ============================================================================

def generate_moan_pool(bible: dict) -> dict[str, list[str]]:
    """MOAN_POOLからキャラに最適な喘ぎを選出"""
    shyness = _get_shyness(bible)

    # キャラの音断片を収集
    dialogue = bible.get("dialogue_examples", {})
    moaning_text = f"{dialogue.get('moaning_light', '')} {dialogue.get('moaning_intense', '')}"
    char_fragments = _extract_hiragana_fragments(moaning_text)

    # フィラーからひらがなのみ抽出
    fillers = bible.get("speech_pattern", {}).get("fillers", [])
    char_fillers = [f for f in fillers if re.fullmatch(r"[ぁ-んー…っッ♡♥]+", f)]

    result = {}
    for intensity in range(1, 6):
        pool = MOAN_POOL.get(intensity, [])
        scored = [(m, _score_moan(m, char_fragments, char_fillers, shyness, intensity)) for m in pool]
        scored.sort(key=lambda x: x[1], reverse=True)
        selected = [_postprocess_moan(m, shyness, intensity) for m, _ in scored[:8]]
        result[str(intensity)] = selected

    return result


def generate_speech_pool(bible: dict) -> dict[str, list[str]]:
    """SPEECH_FEMALE_POOL + SCENE_PHASE_SPEECH_MAPからキャラに最適なセリフを選出"""
    personality = detect_personality_type(bible)
    shyness = _get_shyness(bible)
    first_person = _get_first_person(bible)
    endings = _get_sentence_endings(bible)

    phases = ["intro", "approach", "foreplay", "penetration", "climax", "afterglow"]
    result = {}

    for phase in phases:
        candidates = []
        weights = []

        # 1. ベースカテゴリから候補収集
        base_cats = _PHASE_BASE_CATEGORIES.get(phase, ["embarrassed"])
        for cat in base_cats:
            entries = SPEECH_FEMALE_POOL.get(cat, [])
            for e in entries:
                candidates.append(e)
                weights.append(1.0)

        # 2. 性格ブーストを適用
        if personality and personality in _PERSONALITY_SPEECH_BOOST:
            boosts = _PERSONALITY_SPEECH_BOOST[personality].get(phase, [])
            for cat, multiplier in boosts:
                entries = SPEECH_FEMALE_POOL.get(cat, [])
                for e in entries:
                    if e in candidates:
                        idx = candidates.index(e)
                        weights[idx] *= multiplier
                    else:
                        candidates.append(e)
                        weights.append(multiplier)

        # 3. SCENE_PHASE_SPEECH_MAPから混合
        phase_data = SCENE_PHASE_SPEECH_MAP.get(phase, {})
        phase_speeches = phase_data.get("speech", [])
        for e in phase_speeches:
            if e not in candidates:
                candidates.append(e)
                weights.append(0.8)  # やや低めの重みで混合

        # 4. shynessでウェイト調整
        if shyness >= 4:
            # 恥ずかしがり → denial/embarrassed系ブースト
            for i, c in enumerate(candidates):
                if c in SPEECH_FEMALE_POOL.get("embarrassed", []):
                    weights[i] *= 1.5
                elif c in SPEECH_FEMALE_POOL.get("denial", []):
                    weights[i] *= 1.3
        elif shyness <= 2:
            # 大胆 → acceptance/provoke/teasing系ブースト
            for i, c in enumerate(candidates):
                if c in SPEECH_FEMALE_POOL.get("acceptance", []):
                    weights[i] *= 1.5
                elif c in SPEECH_FEMALE_POOL.get("provoke", []):
                    weights[i] *= 1.3
                elif c in SPEECH_FEMALE_POOL.get("teasing", []):
                    weights[i] *= 1.3

        # 5. 上位5個をサンプリング（重み付き）
        if not candidates:
            result[phase] = []
            continue

        # 重複除去
        seen = set()
        unique_candidates = []
        unique_weights = []
        for c, w in zip(candidates, weights):
            if c not in seen:
                seen.add(c)
                unique_candidates.append(c)
                unique_weights.append(w)

        n_select = min(12, len(unique_candidates))
        selected_indices = []
        remaining = list(range(len(unique_candidates)))
        remaining_weights = list(unique_weights)

        for _ in range(n_select):
            if not remaining:
                break
            total = sum(remaining_weights)
            if total <= 0:
                break
            r = random.random() * total
            cumulative = 0
            chosen_idx = remaining[0]
            for j, idx in enumerate(remaining):
                cumulative += remaining_weights[j]
                if cumulative >= r:
                    chosen_idx = idx
                    remaining.pop(j)
                    remaining_weights.pop(j)
                    break
            selected_indices.append(chosen_idx)

        selected = [unique_candidates[i] for i in selected_indices]

        # 6. 一人称置換 + 語尾適応
        selected = [_replace_first_person(s, first_person) for s in selected]
        selected = [_adapt_ending(s, endings) for s in selected]

        result[phase] = selected

    return result


def generate_thought_pool(bible: dict) -> dict[str, list[str]]:
    """THOUGHT_POOLからキャラに最適な心の声を選出"""
    personality = detect_personality_type(bible)
    first_person = _get_first_person(bible)

    phases = ["intro", "approach", "foreplay", "penetration", "climax", "afterglow"]
    result = {}

    for phase in phases:
        candidates = []
        weights = []

        # 1. ベースカテゴリから候補収集
        base_cats = _PHASE_THOUGHT_CATEGORIES.get(phase, ["general"])
        for cat in base_cats:
            entries = THOUGHT_POOL.get(cat, [])
            for e in entries:
                candidates.append(e)
                weights.append(1.0)

        # 2. 性格ブーストを適用
        if personality and personality in _PERSONALITY_THOUGHT_BOOST:
            for cat, multiplier in _PERSONALITY_THOUGHT_BOOST[personality]:
                entries = THOUGHT_POOL.get(cat, [])
                for e in entries:
                    if e in candidates:
                        idx = candidates.index(e)
                        weights[idx] *= multiplier
                    else:
                        candidates.append(e)
                        weights.append(multiplier)

        # 3. SCENE_PHASE_SPEECH_MAPのthoughtから混合
        phase_data = SCENE_PHASE_SPEECH_MAP.get(phase, {})
        phase_thoughts = phase_data.get("thought", [])
        for e in phase_thoughts:
            if e not in candidates:
                candidates.append(e)
                weights.append(0.8)

        # 4. 重複除去 + サンプリング
        seen = set()
        unique_candidates = []
        unique_weights = []
        for c, w in zip(candidates, weights):
            if c not in seen:
                seen.add(c)
                unique_candidates.append(c)
                unique_weights.append(w)

        n_select = min(12, len(unique_candidates))
        selected_indices = []
        remaining = list(range(len(unique_candidates)))
        remaining_weights = list(unique_weights)

        for _ in range(n_select):
            if not remaining:
                break
            total = sum(remaining_weights)
            if total <= 0:
                break
            r = random.random() * total
            cumulative = 0
            chosen_idx = remaining[0]
            for j, idx in enumerate(remaining):
                cumulative += remaining_weights[j]
                if cumulative >= r:
                    chosen_idx = idx
                    remaining.pop(j)
                    remaining_weights.pop(j)
                    break
            selected_indices.append(chosen_idx)

        selected = [unique_candidates[i] for i in selected_indices]

        # 5. 一人称置換のみ（語尾適応なし）
        selected = [_replace_first_person(s, first_person) for s in selected]

        result[phase] = selected

    return result


def generate_character_pool_local(bible: dict) -> dict:
    """ローカルでキャラ固有プールを生成（API不要・即座）

    Args:
        bible: キャラバイブルdict

    Returns:
        プールdict（moan: {1-5: [8個]}, speech: {6phase: [5個]}, thought: {6phase: [5個]}）
    """
    char_name = bible.get("character_name", "ヒロイン")
    char_id = bible.get("char_id", "")

    pool = {
        "character_name": char_name,
        "char_id": char_id,
        "source": "local",
        "moan": generate_moan_pool(bible),
        "speech": generate_speech_pool(bible),
        "thought": generate_thought_pool(bible),
    }

    return pool


def get_pool_stats(pool: dict) -> dict:
    """プールの統計情報を取得"""
    moan_count = sum(len(v) for v in pool.get("moan", {}).values() if isinstance(v, list))
    speech_count = sum(len(v) for v in pool.get("speech", {}).values() if isinstance(v, list))
    thought_count = sum(len(v) for v in pool.get("thought", {}).values() if isinstance(v, list))
    return {
        "moan": moan_count,
        "speech": speech_count,
        "thought": thought_count,
        "total": moan_count + speech_count + thought_count,
    }
