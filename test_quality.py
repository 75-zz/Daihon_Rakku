#!/usr/bin/env python3
"""品質スコア計測スクリプト (CLI)

生成済みJSONを読み込み、validate_script / auto_fix_script / enhance_sd_prompts の
品質スコアを計測する。gui.pyのGUIを起動せずに関数のみインポートする。

使い方:
  python test_quality.py                       # exports/の最新JSONを計測
  python test_quality.py exports/script_XXX.json  # 指定ファイルを計測
  python test_quality.py --all                 # exports/の全JSONを計測
"""
import json
import sys
import os
import importlib
import importlib.util
from pathlib import Path

# Windows console encoding fix
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")


def _import_gui_functions():
    """gui.pyからGUIを起動せずに必要な関数のみインポート"""
    gui_path = Path(__file__).parent / "gui.py"
    if not gui_path.exists():
        print(f"ERROR: {gui_path} が見つかりません")
        sys.exit(1)

    # gui.pyのソースを読み込み、App()とmainloop()を無効化してインポート
    source = gui_path.read_text(encoding="utf-8")

    # 末尾のmainloop呼び出しを無効化（__name__ガード内なので通常は大丈夫だが安全策）
    # importlibで読み込むと __name__ != "__main__" になるので不要だが念のため

    spec = importlib.util.spec_from_file_location("gui_module", gui_path)
    gui_mod = importlib.util.module_from_spec(spec)

    # __name__を変えてmainガードをスキップ
    gui_mod.__name__ = "gui_module"

    try:
        spec.loader.exec_module(gui_mod)
    except SystemExit:
        pass  # anthropicがない場合など
    except Exception as e:
        print(f"WARNING: gui.pyインポート中のエラー: {e}")
        print("一部機能が使えない可能性があります")

    return gui_mod


def measure_quality(json_path: str, gui_mod, verbose: bool = True):
    """生成済みJSONを読み込んでvalidate_scriptのスコアを計測

    Returns:
        dict: {before_score, after_score, before_issues, after_issues, problems}
    """
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # scenesフィールドがあればそれを使用、なければリスト全体
    if isinstance(data, dict) and "scenes" in data:
        scenes = data["scenes"]
    elif isinstance(data, list):
        scenes = data
    else:
        scenes = data.get("scenes", [data])

    if not scenes:
        if verbose:
            print(f"  スキップ: シーンデータなし")
        return None

    # 修正前スコア
    result_before = gui_mod.validate_script(scenes)
    before_score = result_before["score"]
    before_issues = result_before["total_issues"]

    if verbose:
        print(f"  修正前スコア: {before_score}/100 (問題数: {before_issues})")

    # deep copy for fix
    import copy
    scenes_copy = copy.deepcopy(scenes)

    # auto_fix適用
    fixed = gui_mod.auto_fix_script(scenes_copy)

    # enhance_sd_prompts適用
    gui_mod.enhance_sd_prompts(fixed)

    # 修正後スコア
    result_after = gui_mod.validate_script(fixed)
    after_score = result_after["score"]
    after_issues = result_after["total_issues"]

    if verbose:
        print(f"  修正後スコア: {after_score}/100 (残存問題数: {after_issues})")

        if after_issues > 0:
            print(f"  --- 残存問題 ---")
            # scene_issues
            for sid, problems in result_after.get("scene_issues", {}).items():
                for p in problems:
                    print(f"    [Scene {sid}] {p}")
            # repeated_moans
            for text, sids in result_after.get("repeated_moans", {}).items():
                print(f"    [重複喘ぎ] \"{text}\" -> シーン {sids}")
            # repeated_onomatopoeia
            for pair in result_after.get("repeated_onomatopoeia", []):
                print(f"    [重複SE] シーン {pair[0]} == シーン {pair[1]}")

    return {
        "before_score": before_score,
        "after_score": after_score,
        "before_issues": before_issues,
        "after_issues": after_issues,
        "problems": result_after,
    }


def main():
    print("=" * 60)
    print("Daihon Rakku 品質スコア計測ツール")
    print("=" * 60)

    gui_mod = _import_gui_functions()

    # 引数解析
    args = sys.argv[1:]
    measure_all = "--all" in args
    args = [a for a in args if a != "--all"]

    exports_dir = Path(__file__).parent / "exports"

    if args:
        paths = [Path(a) for a in args]
    elif measure_all:
        paths = sorted(exports_dir.glob("script_*.json"))
    else:
        # 最新のJSONを探す
        jsons = sorted(exports_dir.glob("script_*.json"), reverse=True)
        paths = [jsons[0]] if jsons else []

    if not paths:
        print("テストデータが見つかりません (exports/script_*.json)")
        sys.exit(1)

    results_summary = []

    for p in paths:
        print(f"\n--- {p.name} ---")
        result = measure_quality(str(p), gui_mod)
        if result:
            results_summary.append({
                "file": p.name,
                **result,
            })

    # サマリー表示
    if len(results_summary) > 1:
        print(f"\n{'=' * 60}")
        print(f"{'サマリー':^56}")
        print(f"{'=' * 60}")
        print(f"{'ファイル':<40} {'修正前':>6} {'修正後':>6}")
        print(f"{'-' * 40} {'-' * 6} {'-' * 6}")
        for r in results_summary:
            print(f"{r['file']:<40} {r['before_score']:>5}/100 {r['after_score']:>5}/100")

        avg_before = sum(r["before_score"] for r in results_summary) / len(results_summary)
        avg_after = sum(r["after_score"] for r in results_summary) / len(results_summary)
        avg_improvement = avg_after - avg_before
        perfect = sum(1 for r in results_summary if r["after_score"] == 100)
        above_90 = sum(1 for r in results_summary if r["after_score"] >= 90)
        above_85 = sum(1 for r in results_summary if r["after_score"] >= 85)
        print(f"{'-' * 40} {'-' * 6} {'-' * 6}")
        print(f"{'平均':>40} {avg_before:>5.1f}    {avg_after:>5.1f}")
        print(f"{'改善幅':>40}        {avg_improvement:>+5.1f}")
        print(f"{'100点達成数':>40} {perfect}/{len(results_summary)}")
        print(f"{'90点以上':>40} {above_90}/{len(results_summary)}")
        print(f"{'85点以上':>40} {above_85}/{len(results_summary)}")

        # 問題カテゴリ別の集計
        _print_issue_breakdown(results_summary)


def _print_issue_breakdown(results_summary: list):
    """残存問題をカテゴリ別に集計して表示"""
    issue_categories = {}
    for r in results_summary:
        problems = r.get("problems", {})
        # scene_issues
        for sid, probs in problems.get("scene_issues", {}).items():
            for p in probs:
                # カテゴリ抽出（「」内の内容や先頭のキーワード）
                if "吹き出し" in p and "0個" in p:
                    cat = "吹き出し0個(旧フォーマット)"
                elif "吹き出し" in p:
                    cat = "吹き出し数超過"
                elif "抽象的" in p:
                    cat = "description抽象的"
                elif "同一アングル" in p:
                    cat = "連続同一アングル"
                elif "同一体位" in p:
                    cat = "連続同一体位"
                elif "連続同一location" in p:
                    cat = "3シーン連続同一location"
                elif "室内外矛盾" in p:
                    cat = "室内外タグ矛盾"
                elif "照明矛盾" in p:
                    cat = "照明-時間帯矛盾"
                elif "背景/場所タグが無い" in p:
                    cat = "背景タグ欠落"
                elif "日本語" in p:
                    cat = "sd_prompt日本語混入"
                elif "不自然表現" in p:
                    cat = "不自然表現残存"
                elif "体位偏り" in p:
                    cat = "体位分布偏り"
                elif "が空" in p:
                    cat = "必須フィールド空"
                elif "description短すぎ" in p:
                    cat = "description短すぎ"
                elif "description類似" in p:
                    cat = "description類似(prefix30)"
                elif "story_flow類似" in p:
                    cat = "story_flow類似"
                elif "speech重複" in p:
                    cat = "speech重複"
                elif "アングル偏り" in p:
                    cat = "アングル分布偏り"
                else:
                    cat = "その他"
                issue_categories[cat] = issue_categories.get(cat, 0) + 1
        # repeated_moans
        moan_count = len(problems.get("repeated_moans", {}))
        if moan_count > 0:
            issue_categories["喘ぎ重複(類似含む)"] = issue_categories.get("喘ぎ重複(類似含む)", 0) + moan_count
        # repeated_onomatopoeia
        onom_count = len(problems.get("repeated_onomatopoeia", []))
        if onom_count > 0:
            issue_categories["オノマトペ重複"] = issue_categories.get("オノマトペ重複", 0) + onom_count

    if issue_categories:
        print(f"\n{'問題カテゴリ別集計':^56}")
        print(f"{'-' * 56}")
        sorted_cats = sorted(issue_categories.items(), key=lambda x: -x[1])
        for cat, count in sorted_cats:
            bar = "#" * min(count, 30)
            print(f"  {cat:<28} {count:>3}件 {bar}")


if __name__ == "__main__":
    main()
