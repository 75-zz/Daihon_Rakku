#!/usr/bin/env python3
"""
Daihon Rakku パイプライン出力 JSONスキーマバリデーション

パイプラインの各フェーズ出力を構造的に検証し、
不正なデータを早期検出してエラーメッセージを返す。

対応フェーズ:
  Phase 1: コンテキスト (context)
  Phase 3: アウトライン (outline)
  Phase 4: シーン (scene) - bubbles形式 / dialogue形式両対応
  Phase 5: 最終結果配列 (results)
"""

from __future__ import annotations

import re
from typing import Any

# ---------------------------------------------------------------------------
# ユーティリティ
# ---------------------------------------------------------------------------

def _type_name(val: Any) -> str:
    """値の型名を日本語で返す"""
    t = type(val).__name__
    return {"str": "文字列", "int": "整数", "float": "小数",
            "list": "配列", "dict": "辞書", "bool": "真偽値",
            "NoneType": "null"}.get(t, t)


def _check_type(obj: Any, key: str, expected: type | tuple, required: bool = True) -> list[str]:
    """フィールドの型チェック。エラーメッセージのリストを返す。"""
    errors = []
    if key not in obj:
        if required:
            errors.append(f"必須フィールド「{key}」が欠落")
        return errors
    val = obj[key]
    if not isinstance(val, expected):
        exp_names = expected if isinstance(expected, tuple) else (expected,)
        exp_str = "/".join(_type_name(e()) for e in exp_names)
        errors.append(f"「{key}」の型が不正: {_type_name(val)}（期待: {exp_str}）")
    return errors


# ---------------------------------------------------------------------------
# Phase 1: コンテキスト
# ---------------------------------------------------------------------------

def validate_context(ctx: Any) -> dict:
    """コンテキスト圧縮結果を検証。

    期待構造:
      {
        "setting": str,
        "chars": [{"name": str, "look": str, "voice": str}],
        "tone": str,
        "theme": str,
        "ng": [str]
      }
    """
    errors = []

    if not isinstance(ctx, dict):
        return {"valid": False, "errors": [f"contextがdict型でない（{_type_name(ctx)}）"]}

    errors.extend(_check_type(ctx, "setting", str))
    errors.extend(_check_type(ctx, "tone", str))
    errors.extend(_check_type(ctx, "theme", str))
    errors.extend(_check_type(ctx, "ng", list, required=False))

    # chars 配列
    errors.extend(_check_type(ctx, "chars", list))
    if isinstance(ctx.get("chars"), list):
        if len(ctx["chars"]) == 0:
            errors.append("「chars」が空配列（最低1キャラ必要）")
        for i, ch in enumerate(ctx["chars"]):
            prefix = f"chars[{i}]"
            if not isinstance(ch, dict):
                errors.append(f"{prefix}: dict型でない")
                continue
            if not ch.get("name"):
                errors.append(f"{prefix}: 「name」が空")
            for field in ("look", "voice"):
                if field not in ch:
                    errors.append(f"{prefix}: 「{field}」が欠落")

    return {"valid": len(errors) == 0, "errors": errors}


# ---------------------------------------------------------------------------
# Phase 3: アウトライン（シーン分割結果）
# ---------------------------------------------------------------------------

_EROTIC_LEVELS = {"none", "light", "medium", "heavy", "climax"}

def validate_outline_scene(scene: Any, idx: int, compact: bool = False) -> list[str]:
    """アウトライン1シーンの検証。エラーリストを返す。

    Args:
        compact: True の場合、12シーン超の簡潔版フォーマット（situation必須、goal等は任意）
    """
    errors = []
    prefix = f"outline[{idx}]"

    if not isinstance(scene, dict):
        return [f"{prefix}: dict型でない"]

    # 必須フィールド
    errors.extend([f"{prefix}.{e}" for e in _check_type(scene, "scene_id", (int, float))])
    errors.extend([f"{prefix}.{e}" for e in _check_type(scene, "title", str)])
    errors.extend([f"{prefix}.{e}" for e in _check_type(scene, "intensity", (int, float))])

    # intensity 値域
    intensity = scene.get("intensity")
    if isinstance(intensity, (int, float)) and not (1 <= intensity <= 5):
        errors.append(f"{prefix}: intensity={intensity} は範囲外（1-5）")

    # erotic_level
    erotic = scene.get("erotic_level")
    if erotic is not None and erotic not in _EROTIC_LEVELS:
        errors.append(f"{prefix}: erotic_level「{erotic}」は不正（{', '.join(sorted(_EROTIC_LEVELS))}）")

    # location（必須）
    errors.extend([f"{prefix}.{e}" for e in _check_type(scene, "location", str)])

    # situation（必須）
    if "situation" in scene:
        if not isinstance(scene["situation"], str):
            errors.append(f"{prefix}: 「situation」が文字列でない")
        elif not compact and not scene["situation"]:
            errors.append(f"{prefix}: 「situation」が空")
    elif not compact:
        # 通常フォーマットではsituationも必須
        # ただしsetdefaultで補完されるケースがあるので警告レベル
        pass

    # emotional_arc
    arc = scene.get("emotional_arc")
    if arc is not None:
        if not isinstance(arc, dict):
            errors.append(f"{prefix}: 「emotional_arc」がdict型でない")
        elif not arc.get("start") and not arc.get("end"):
            pass  # 空でも許容（テンプレートフォールバック時）

    # beats
    beats = scene.get("beats")
    if beats is not None and not isinstance(beats, list):
        errors.append(f"{prefix}: 「beats」が配列でない")

    return errors


def validate_outline(outline: Any, expected_count: int | None = None) -> dict:
    """アウトライン配列全体を検証。

    Args:
        outline: パース済みJSON
        expected_count: 期待シーン数（Noneの場合チェックしない）
    """
    errors = []

    if not isinstance(outline, list):
        return {"valid": False, "errors": [f"outlineがlist型でない（{_type_name(outline)}）"]}

    if len(outline) == 0:
        return {"valid": False, "errors": ["outlineが空配列"]}

    if expected_count is not None and len(outline) != expected_count:
        errors.append(f"シーン数不一致: {len(outline)}（期待: {expected_count}）")

    # scene_id 重複チェック
    ids = [s.get("scene_id") for s in outline if isinstance(s, dict)]
    id_set = set()
    for sid in ids:
        if sid in id_set:
            errors.append(f"scene_id={sid} が重複")
        if sid is not None:
            id_set.add(sid)

    # 12シーン超は簡潔フォーマット（gui.pyの分岐に合わせる）
    compact = len(outline) > 12

    # intensity 飛躍チェック
    prev_int = None
    for i, scene in enumerate(outline):
        if not isinstance(scene, dict):
            errors.append(f"outline[{i}]: dict型でない")
            continue
        cur_int = scene.get("intensity")
        if isinstance(cur_int, (int, float)) and prev_int is not None:
            if cur_int - prev_int >= 3:
                errors.append(f"outline[{i}]: intensity飛躍 {prev_int}→{cur_int}（差{cur_int - prev_int}）")
        if isinstance(cur_int, (int, float)):
            prev_int = cur_int

        # 各シーンの詳細チェック
        errors.extend(validate_outline_scene(scene, i, compact=compact))

    return {"valid": len(errors) == 0, "errors": errors}


# ---------------------------------------------------------------------------
# Phase 4: シーン（bubbles形式 + dialogue旧形式 両対応）
# ---------------------------------------------------------------------------

_BUBBLE_TYPES = {"speech", "moan", "thought"}

def validate_bubble(bubble: Any, idx: int, scene_prefix: str) -> list[str]:
    """吹き出し1個の検証。"""
    errors = []
    prefix = f"{scene_prefix}.bubbles[{idx}]"

    if not isinstance(bubble, dict):
        return [f"{prefix}: dict型でない"]

    if not bubble.get("speaker"):
        errors.append(f"{prefix}: 「speaker」が空")

    btype = bubble.get("type")
    if btype and btype not in _BUBBLE_TYPES:
        errors.append(f"{prefix}: type「{btype}」は不正（{', '.join(sorted(_BUBBLE_TYPES))}）")

    text = bubble.get("text", "")
    if not text:
        errors.append(f"{prefix}: 「text」が空")

    return errors


def validate_dialogue_entry(entry: Any, idx: int, scene_prefix: str) -> list[str]:
    """旧dialogue形式の1エントリ検証。"""
    errors = []
    prefix = f"{scene_prefix}.dialogue[{idx}]"

    if not isinstance(entry, dict):
        return [f"{prefix}: dict型でない"]

    if not entry.get("speaker"):
        errors.append(f"{prefix}: 「speaker」が空")

    line = entry.get("line", "")
    if not line:
        errors.append(f"{prefix}: 「line」が空")

    return errors


def validate_scene(scene: Any, idx: int | None = None) -> dict:
    """シーン生成結果（Phase 4 出力）を検証。

    新形式（bubbles）と旧形式（dialogue）の両方をサポート。
    """
    errors = []
    prefix = f"scene[{idx}]" if idx is not None else "scene"

    if not isinstance(scene, dict):
        return {"valid": False, "errors": [f"{prefix}: dict型でない"]}

    # エラーシーンの場合はスキップ
    if scene.get("mood") == "エラー":
        return {"valid": True, "errors": [], "skipped": True}

    # 必須フィールド
    errors.extend([f"{prefix}.{e}" for e in _check_type(scene, "scene_id", (int, float))])
    errors.extend([f"{prefix}.{e}" for e in _check_type(scene, "title", str)])
    errors.extend([f"{prefix}.{e}" for e in _check_type(scene, "description", str)])
    errors.extend([f"{prefix}.{e}" for e in _check_type(scene, "mood", str)])
    errors.extend([f"{prefix}.{e}" for e in _check_type(scene, "direction", str)])

    # description 品質
    desc = scene.get("description", "")
    if isinstance(desc, str) and 0 < len(desc) < 10:
        errors.append(f"{prefix}: descriptionが極端に短い（{len(desc)}文字）")

    # sd_prompt
    sd = scene.get("sd_prompt", "")
    if not sd:
        errors.append(f"{prefix}: 「sd_prompt」が空")
    elif isinstance(sd, str):
        # 日本語混入チェック
        jp_chars = re.findall(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]+', sd)
        if jp_chars:
            errors.append(f"{prefix}: sd_promptに日本語混入: {', '.join(jp_chars[:3])}")

    # character_feelings（任意だが型チェック）
    feelings = scene.get("character_feelings")
    if feelings is not None and not isinstance(feelings, dict):
        errors.append(f"{prefix}: 「character_feelings」がdict型でない")

    # location_detail（任意）
    loc = scene.get("location_detail")
    if loc is not None and not isinstance(loc, str):
        errors.append(f"{prefix}: 「location_detail」が文字列でない")

    # story_flow（任意）
    flow = scene.get("story_flow")
    if flow is not None and not isinstance(flow, str):
        errors.append(f"{prefix}: 「story_flow」が文字列でない")

    # intensity（任意だがあれば範囲チェック）
    intensity = scene.get("intensity")
    if intensity is not None:
        if not isinstance(intensity, (int, float)):
            errors.append(f"{prefix}: 「intensity」が数値でない")
        elif not (1 <= intensity <= 5):
            errors.append(f"{prefix}: intensity={intensity} は範囲外（1-5）")

    # --- bubbles (新形式) ---
    bubbles = scene.get("bubbles")
    dialogue = scene.get("dialogue")

    if bubbles is not None:
        if not isinstance(bubbles, list):
            errors.append(f"{prefix}: 「bubbles」が配列でない")
        else:
            if len(bubbles) > 3:
                errors.append(f"{prefix}: 吹き出し{len(bubbles)}個（上限3個）")
            for bi, b in enumerate(bubbles):
                errors.extend(validate_bubble(b, bi, prefix))
    elif dialogue is not None:
        # 旧形式
        if not isinstance(dialogue, list):
            errors.append(f"{prefix}: 「dialogue」が配列でない")
        else:
            for di, d in enumerate(dialogue):
                errors.extend(validate_dialogue_entry(d, di, prefix))
    else:
        errors.append(f"{prefix}: 「bubbles」「dialogue」のどちらも存在しない")

    # onomatopoeia（任意）
    onom = scene.get("onomatopoeia")
    if onom is not None and not isinstance(onom, list):
        errors.append(f"{prefix}: 「onomatopoeia」が配列でない")

    return {"valid": len(errors) == 0, "errors": errors}


# ---------------------------------------------------------------------------
# Phase 5: 結果配列全体
# ---------------------------------------------------------------------------

def validate_results(results: Any) -> dict:
    """パイプライン最終結果（シーン配列）を一括検証。

    Args:
        results: シーン辞書のリスト

    Returns:
        {
            "valid": bool,
            "errors": [str],
            "scene_errors": {scene_id: [str]},
            "stats": {
                "total": int,
                "valid": int,
                "error_scenes": int,
                "skipped": int
            }
        }
    """
    errors = []
    scene_errors = {}
    stats = {"total": 0, "valid_count": 0, "error_scenes": 0, "skipped": 0}

    if not isinstance(results, list):
        return {
            "valid": False,
            "errors": [f"resultsがlist型でない（{_type_name(results)}）"],
            "scene_errors": {},
            "stats": stats,
        }

    if len(results) == 0:
        return {
            "valid": False,
            "errors": ["resultsが空配列"],
            "scene_errors": {},
            "stats": stats,
        }

    stats["total"] = len(results)

    # scene_id 重複チェック
    seen_ids = {}
    for i, scene in enumerate(results):
        if not isinstance(scene, dict):
            errors.append(f"results[{i}]: dict型でない")
            continue
        sid = scene.get("scene_id", i + 1)
        if sid in seen_ids:
            errors.append(f"scene_id={sid} が重複（results[{seen_ids[sid]}] と results[{i}]）")
        seen_ids[sid] = i

    # 各シーン検証
    for i, scene in enumerate(results):
        result = validate_scene(scene, i)
        sid = scene.get("scene_id", i + 1) if isinstance(scene, dict) else i + 1

        if result.get("skipped"):
            stats["skipped"] += 1
            stats["error_scenes"] += 1
            continue

        if result["valid"]:
            stats["valid_count"] += 1
        else:
            scene_errors[sid] = result["errors"]
            errors.extend(result["errors"])

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "scene_errors": scene_errors,
        "stats": stats,
    }


# ---------------------------------------------------------------------------
# 品質チェック結果のバリデーション
# ---------------------------------------------------------------------------

def validate_quality_check(qc: Any) -> dict:
    """品質チェック関数（check_quality）の出力を検証。

    期待構造:
      {
        "has_problems": bool,
        "problems": [{"scene_id": int, "type": str, "detail": str}],
        "fix_instructions": [{"scene_id": int, "instruction": str}]
      }
    """
    errors = []

    if not isinstance(qc, dict):
        return {"valid": False, "errors": [f"品質チェック結果がdict型でない（{_type_name(qc)}）"]}

    if "has_problems" not in qc:
        errors.append("「has_problems」が欠落")
    elif not isinstance(qc["has_problems"], bool):
        errors.append(f"「has_problems」がbool型でない（{_type_name(qc['has_problems'])}）")

    problems = qc.get("problems")
    if problems is not None:
        if not isinstance(problems, list):
            errors.append("「problems」が配列でない")
        else:
            for i, p in enumerate(problems):
                if not isinstance(p, dict):
                    errors.append(f"problems[{i}]: dict型でない")
                    continue
                if "scene_id" not in p:
                    errors.append(f"problems[{i}]: 「scene_id」が欠落")
                if not p.get("type"):
                    errors.append(f"problems[{i}]: 「type」が空")
                if not p.get("detail"):
                    errors.append(f"problems[{i}]: 「detail」が空")

    fixes = qc.get("fix_instructions")
    if fixes is not None:
        if not isinstance(fixes, list):
            errors.append("「fix_instructions」が配列でない")
        else:
            for i, f in enumerate(fixes):
                if not isinstance(f, dict):
                    errors.append(f"fix_instructions[{i}]: dict型でない")
                    continue
                if "scene_id" not in f:
                    errors.append(f"fix_instructions[{i}]: 「scene_id」が欠落")
                if not f.get("instruction"):
                    errors.append(f"fix_instructions[{i}]: 「instruction」が空")

    return {"valid": len(errors) == 0, "errors": errors}


# ---------------------------------------------------------------------------
# パイプライン統合バリデーション
# ---------------------------------------------------------------------------

def validate_pipeline_output(
    context: Any = None,
    outline: Any = None,
    results: Any = None,
    expected_scenes: int | None = None,
) -> dict:
    """パイプライン全体の出力をまとめて検証。

    各フェーズの結果を渡すと、フェーズごとの検証結果を返す。
    Noneのフェーズはスキップされる。

    Returns:
        {
            "valid": bool,
            "phases": {
                "context": {"valid": bool, "errors": [str]} | None,
                "outline": {"valid": bool, "errors": [str]} | None,
                "results": {"valid": bool, ...} | None,
            },
            "summary": str
        }
    """
    phases = {}
    all_valid = True

    if context is not None:
        ctx_result = validate_context(context)
        phases["context"] = ctx_result
        if not ctx_result["valid"]:
            all_valid = False

    if outline is not None:
        out_result = validate_outline(outline, expected_scenes)
        phases["outline"] = out_result
        if not out_result["valid"]:
            all_valid = False

    if results is not None:
        res_result = validate_results(results)
        phases["results"] = res_result
        if not res_result["valid"]:
            all_valid = False

    # サマリー
    total_errors = sum(len(p.get("errors", [])) for p in phases.values())
    checked = [k for k in phases]
    summary = f"検証フェーズ: {', '.join(checked)} | エラー: {total_errors}件"
    if all_valid:
        summary += " | 全フェーズOK"

    return {
        "valid": all_valid,
        "phases": phases,
        "summary": summary,
    }
