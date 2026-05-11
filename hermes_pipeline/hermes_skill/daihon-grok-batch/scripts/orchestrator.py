"""Daihon → Grok Batch Orchestrator (helper for Hermes Agent)

Hermes Agent の SKILL.md から呼ばれるヘルパー。ブラウザ操作そのものは
Hermes Agent の組込みツール (browser_navigate, browser_type 等) が担当し、
本スクリプトは「処理対象シーンの列挙」「入力テキスト読み出し」
「応答テキスト保存」「エラーログ保存」「進捗JSON更新」のみを担う。

使い方:
    python orchestrator.py list <work_dir> [--limit N] [--start-from M]
    python orchestrator.py read <work_dir> <scene_id>
    python orchestrator.py save-response <work_dir> <scene_id> < stdin
    python orchestrator.py save-error <work_dir> <scene_id> <error_msg>
    python orchestrator.py status <work_dir>

`<work_dir>` は Phase 1 が出力した
`outputs/hermes_pipeline/<basename>/` ディレクトリで、
`grok_inputs/scene_NNN.txt` を読み、`grok_responses/scene_NNN_response.txt` を書く。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

_INPUT_RE = re.compile(r"^scene_(\d+)\.txt$")


def _input_dir(work_dir: Path) -> Path:
    return work_dir / "grok_inputs"


def _response_dir(work_dir: Path) -> Path:
    d = work_dir / "grok_responses"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _progress_file(work_dir: Path) -> Path:
    return work_dir / "grok_progress.json"


def _list_input_scene_ids(work_dir: Path) -> list[int]:
    in_dir = _input_dir(work_dir)
    if not in_dir.exists():
        return []
    ids: list[int] = []
    for f in in_dir.iterdir():
        m = _INPUT_RE.match(f.name)
        if m:
            ids.append(int(m.group(1)))
    return sorted(ids)


def _is_done(work_dir: Path, scene_id: int) -> bool:
    return (_response_dir(work_dir) / f"scene_{scene_id:03d}_response.txt").exists()


def cmd_list(work_dir: Path, limit: int | None, start_from: int | None) -> int:
    ids = _list_input_scene_ids(work_dir)
    if start_from is not None:
        ids = [i for i in ids if i >= start_from]
    pending = [i for i in ids if not _is_done(work_dir, i)]
    if limit is not None and limit > 0:
        pending = pending[:limit]
    payload = {
        "work_dir": str(work_dir),
        "total_inputs": len(_list_input_scene_ids(work_dir)),
        "pending": pending,
        "pending_count": len(pending),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def cmd_read(work_dir: Path, scene_id: int) -> int:
    p = _input_dir(work_dir) / f"scene_{scene_id:03d}.txt"
    if not p.exists():
        print(f"[ERROR] input not found: {p}", file=sys.stderr)
        return 2
    sys.stdout.write(p.read_text(encoding="utf-8"))
    return 0


def cmd_save_response(work_dir: Path, scene_id: int, response_text: str) -> int:
    out = _response_dir(work_dir) / f"scene_{scene_id:03d}_response.txt"
    out.write_text(response_text, encoding="utf-8")
    _record_progress(work_dir, scene_id, "success", len(response_text))
    print(json.dumps({"saved": str(out), "bytes": len(response_text.encode("utf-8"))}, ensure_ascii=False))
    return 0


def cmd_save_error(work_dir: Path, scene_id: int, error_msg: str) -> int:
    out = _response_dir(work_dir) / f"scene_{scene_id:03d}.error.txt"
    out.write_text(error_msg, encoding="utf-8")
    _record_progress(work_dir, scene_id, "error", len(error_msg))
    print(json.dumps({"error_saved": str(out)}, ensure_ascii=False))
    return 0


def _record_progress(work_dir: Path, scene_id: int, status: str, payload_size: int) -> None:
    pf = _progress_file(work_dir)
    data: dict = {}
    if pf.exists():
        try:
            data = json.loads(pf.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {}
    history = data.setdefault("history", [])
    history.append(
        {
            "scene_id": scene_id,
            "status": status,
            "ts": datetime.now().isoformat(timespec="seconds"),
            "bytes": payload_size,
        }
    )
    pf.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def cmd_status(work_dir: Path) -> int:
    inputs = _list_input_scene_ids(work_dir)
    done = [i for i in inputs if _is_done(work_dir, i)]
    pending = [i for i in inputs if i not in done]
    errors = sorted(
        int(_INPUT_RE.sub(r"\1", f.name.replace(".error.txt", ".txt")))
        for f in _response_dir(work_dir).glob("scene_*.error.txt")
    )
    payload = {
        "total_inputs": len(inputs),
        "done_count": len(done),
        "pending_count": len(pending),
        "error_count": len(errors),
        "done": done,
        "pending": pending,
        "errors": errors,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list", help="未処理シーンID列を JSON で返す")
    p_list.add_argument("work_dir")
    p_list.add_argument("--limit", type=int, default=None)
    p_list.add_argument("--start-from", type=int, default=None)

    p_read = sub.add_parser("read", help="指定シーンのGrok投入テキストを標準出力に")
    p_read.add_argument("work_dir")
    p_read.add_argument("scene_id", type=int)

    p_sr = sub.add_parser("save-response", help="標準入力から応答テキストを受け取り保存")
    p_sr.add_argument("work_dir")
    p_sr.add_argument("scene_id", type=int)

    p_se = sub.add_parser("save-error", help="エラー文字列を保存")
    p_se.add_argument("work_dir")
    p_se.add_argument("scene_id", type=int)
    p_se.add_argument("error_msg")

    p_st = sub.add_parser("status", help="進捗サマリ JSON")
    p_st.add_argument("work_dir")

    args = parser.parse_args(argv)
    work_dir = Path(args.work_dir)
    if not work_dir.exists():
        print(f"[ERROR] work_dir not found: {work_dir}", file=sys.stderr)
        return 2

    if args.cmd == "list":
        return cmd_list(work_dir, args.limit, args.start_from)
    if args.cmd == "read":
        return cmd_read(work_dir, args.scene_id)
    if args.cmd == "save-response":
        response = sys.stdin.read()
        return cmd_save_response(work_dir, args.scene_id, response)
    if args.cmd == "save-error":
        return cmd_save_error(work_dir, args.scene_id, args.error_msg)
    if args.cmd == "status":
        return cmd_status(work_dir)
    return 1


if __name__ == "__main__":
    sys.exit(main())
