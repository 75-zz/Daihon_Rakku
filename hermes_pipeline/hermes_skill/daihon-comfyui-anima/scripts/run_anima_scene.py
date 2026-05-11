"""Daihon ComfyUI Anima — Step 2: run_anima_scene

anima_prompts/scene_NNN_prompt.json と workflows/anima_base.api.json を読み、
workflow に prompt / negative / seed / filename_prefix / 解像度 を patch して
ComfyUI API に投入し、生成画像を images/scene_NNN.png に保存する。

ComfyUI API は HTTP のみで:
  POST /prompt          → prompt_id
  GET  /history/<id>    → 完了監視 (polling)
  GET  /view            → 画像 DL

依存: 標準ライブラリ urllib のみ（追加 pip install 不要）。

使い方:
    python3 run_anima_scene.py run <work_dir> [--scene-id N] [--limit N]
                                              [--server URL] [--resolution WxH]
                                              [--timeout S] [--force]
    python3 run_anima_scene.py status <work_dir>
"""

from __future__ import annotations

import argparse
import copy
import json
import random
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path


# ─── ノード ID 定数 (anima_base.api.json 解析結果) ───
NODE_POSITIVE_PROMPT = "70"   # Power Prompt (rgthree) — inputs.prompt
NODE_NEGATIVE_PROMPT = "7"    # CLIPTextEncode          — inputs.text
NODE_KSAMPLER        = "107"  # KSampler                — inputs.seed
NODE_SAVE_IMAGE      = "106"  # SaveImage               — inputs.filename_prefix
NODE_LATENT_USED     = "104"  # EmptyLatentImage (KSampler 入力) — inputs.width/height


_PROMPT_NAME_RE = re.compile(r"^scene_(\d+)_prompt\.json$")
_RESOLUTION_RE = re.compile(r"^(\d+)x(\d+)$")
_ERROR_NAME_RE = re.compile(r"^scene_(\d+)\.error\.txt$")

DEFAULT_SERVER = "http://127.0.0.1:8188"
DEFAULT_TIMEOUT = 300
DEFAULT_POLL_INTERVAL = 2


# ─── HTTP ヘルパ ─────────────────────────────────
def _http_post_json(url: str, payload: dict, timeout: int = 30) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _http_get_json(url: str, timeout: int = 30) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _http_get_bytes(url: str, timeout: int = 60) -> bytes:
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return resp.read()


# ─── workflow パッチ ────────────────────────────
def patch_workflow(
    workflow: dict,
    positive: str,
    negative: str,
    seed: int,
    filename_prefix: str,
    width: int = 1024,
    height: int = 1024,
) -> dict:
    """workflow JSON のディープコピーに対し、各ノードのフィールドを差し替える。"""
    wf = copy.deepcopy(workflow)
    if NODE_POSITIVE_PROMPT in wf:
        wf[NODE_POSITIVE_PROMPT]["inputs"]["prompt"] = positive
    if NODE_NEGATIVE_PROMPT in wf:
        wf[NODE_NEGATIVE_PROMPT]["inputs"]["text"] = negative
    if NODE_KSAMPLER in wf:
        wf[NODE_KSAMPLER]["inputs"]["seed"] = seed
    if NODE_SAVE_IMAGE in wf:
        wf[NODE_SAVE_IMAGE]["inputs"]["filename_prefix"] = filename_prefix
    if NODE_LATENT_USED in wf:
        wf[NODE_LATENT_USED]["inputs"]["width"] = width
        wf[NODE_LATENT_USED]["inputs"]["height"] = height
    return wf


# ─── ComfyUI API 呼び出し ──────────────────────
def submit_workflow(server: str, workflow: dict) -> str:
    resp = _http_post_json(f"{server}/prompt", {"prompt": workflow}, timeout=30)
    prompt_id = resp.get("prompt_id")
    if not prompt_id:
        raise RuntimeError(f"submit failed: {resp}")
    return prompt_id


def wait_for_completion(
    server: str,
    prompt_id: str,
    timeout: int = DEFAULT_TIMEOUT,
    poll_interval: int = DEFAULT_POLL_INTERVAL,
) -> dict:
    deadline = time.time() + timeout
    last_err: Exception | None = None
    while time.time() < deadline:
        try:
            history = _http_get_json(f"{server}/history/{prompt_id}", timeout=10)
            if prompt_id in history:
                entry = history[prompt_id]
                # status.completed か outputs 存在で完了判定
                status = entry.get("status", {})
                if status.get("completed") or "outputs" in entry:
                    return entry
        except Exception as e:
            last_err = e
        time.sleep(poll_interval)
    msg = f"workflow {prompt_id} did not complete within {timeout}s"
    if last_err is not None:
        msg += f" (last_err={last_err!r})"
    raise TimeoutError(msg)


def extract_image_info(history_entry: dict) -> list[dict]:
    """history entry の outputs から画像メタを抽出。"""
    outputs = history_entry.get("outputs", {})
    images: list[dict] = []
    for nid, node_out in outputs.items():
        for img in node_out.get("images", []):
            images.append({
                "filename": img.get("filename"),
                "subfolder": img.get("subfolder", ""),
                "type": img.get("type", "output"),
                "node_id": nid,
            })
    return images


def download_image(server: str, image_info: dict) -> bytes:
    params = urllib.parse.urlencode({
        "filename": image_info["filename"],
        "subfolder": image_info["subfolder"],
        "type": image_info["type"],
    })
    return _http_get_bytes(f"{server}/view?{params}")


# ─── シーン単位処理 ─────────────────────────────
def process_scene(
    workflow_template: dict,
    prompt_path: Path,
    image_out_path: Path,
    server: str,
    seed: int | None = None,
    width: int = 1024,
    height: int = 1024,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict:
    prompt_data = json.loads(prompt_path.read_text(encoding="utf-8"))
    positive: str = prompt_data["positive"]
    negative: str = prompt_data["negative"]
    scene_id: int = prompt_data["scene_id"]

    if seed is None:
        seed = random.randint(1, 2**63 - 1)

    filename_prefix = f"daihon_scene_{scene_id:03d}"
    patched = patch_workflow(
        workflow_template, positive, negative, seed, filename_prefix, width, height
    )

    t0 = time.time()
    prompt_id = submit_workflow(server, patched)
    entry = wait_for_completion(server, prompt_id, timeout=timeout)
    images = extract_image_info(entry)
    if not images:
        raise RuntimeError(f"no images in history for {prompt_id}")

    img_bytes = download_image(server, images[0])
    image_out_path.write_bytes(img_bytes)
    elapsed = round(time.time() - t0, 1)

    return {
        "scene_id": scene_id,
        "ok": True,
        "prompt_id": prompt_id,
        "seed": seed,
        "resolution": f"{width}x{height}",
        "filename_prefix": filename_prefix,
        "output": str(image_out_path),
        "comfyui_filename": images[0]["filename"],
        "image_bytes": len(img_bytes),
        "elapsed_s": elapsed,
    }


# ─── 列挙 ────────────────────────────────────
def _list_prompt_scene_ids(work_dir: Path) -> list[int]:
    pd = work_dir / "anima_prompts"
    if not pd.exists():
        return []
    ids = []
    for f in pd.iterdir():
        m = _PROMPT_NAME_RE.match(f.name)
        if m:
            ids.append(int(m.group(1)))
    return sorted(ids)


def _is_image_done(work_dir: Path, scene_id: int) -> bool:
    return (work_dir / "images" / f"scene_{scene_id:03d}.png").exists()


# ─── CLI コマンド ───────────────────────────────
def cmd_run(args) -> int:
    work_dir = Path(args.work_dir)
    workflow_path = Path(args.workflow) if args.workflow else (
        Path(__file__).resolve().parent.parent / "workflows" / "anima_base.api.json"
    )
    if not workflow_path.exists():
        print(f"[ERROR] workflow JSON not found: {workflow_path}", file=sys.stderr)
        return 2

    image_dir = work_dir / "images"
    image_dir.mkdir(parents=True, exist_ok=True)

    workflow_template = json.loads(workflow_path.read_text(encoding="utf-8"))

    if args.scene_id is not None:
        targets = [args.scene_id]
    else:
        targets = _list_prompt_scene_ids(work_dir)
        if not args.force:
            targets = [i for i in targets if not _is_image_done(work_dir, i)]
        if args.limit is not None and args.limit > 0:
            targets = targets[:args.limit]

    width, height = 1024, 1024
    m = _RESOLUTION_RE.match(args.resolution)
    if m:
        width, height = int(m.group(1)), int(m.group(2))

    if not targets:
        print(json.dumps({"summary": "no pending scenes", "ok_count": 0}, ensure_ascii=False))
        return 0

    print(json.dumps({
        "info": "start",
        "targets": targets,
        "server": args.server,
        "workflow": str(workflow_path),
        "resolution": f"{width}x{height}",
    }, ensure_ascii=False), flush=True)

    results: list[dict] = []
    consecutive_fails = 0
    for sid in targets:
        prompt_path = work_dir / "anima_prompts" / f"scene_{sid:03d}_prompt.json"
        if not prompt_path.exists():
            err = {"scene_id": sid, "ok": False, "error": "prompt_json_not_found"}
            results.append(err)
            consecutive_fails += 1
            print(json.dumps(err, ensure_ascii=False), flush=True)
            if consecutive_fails >= 3:
                print(json.dumps({"halt": "consecutive_failures"}, ensure_ascii=False))
                break
            continue

        image_out = image_dir / f"scene_{sid:03d}.png"
        try:
            r = process_scene(
                workflow_template, prompt_path, image_out, args.server,
                seed=None, width=width, height=height, timeout=args.timeout,
            )
            results.append(r)
            consecutive_fails = 0
            print(json.dumps(r, ensure_ascii=False), flush=True)
        except Exception as e:
            err = {"scene_id": sid, "ok": False, "error": str(e)}
            results.append(err)
            consecutive_fails += 1
            (image_dir / f"scene_{sid:03d}.error.txt").write_text(str(e), encoding="utf-8")
            print(json.dumps(err, ensure_ascii=False), flush=True)
            if consecutive_fails >= 3:
                print(json.dumps(
                    {"halt": "consecutive_failures", "count": consecutive_fails},
                    ensure_ascii=False,
                ))
                break

    summary = {
        "total_targets": len(targets),
        "processed": len(results),
        "ok_count": sum(1 for r in results if r.get("ok")),
        "error_count": sum(1 for r in results if not r.get("ok")),
    }
    print(json.dumps({"summary": summary}, ensure_ascii=False, indent=2))
    return 0 if summary["error_count"] == 0 else 1


def cmd_status(args) -> int:
    work_dir = Path(args.work_dir)
    prompt_ids = _list_prompt_scene_ids(work_dir)
    done = [i for i in prompt_ids if _is_image_done(work_dir, i)]
    pending = [i for i in prompt_ids if i not in done]
    errors: list[int] = []
    img_dir = work_dir / "images"
    if img_dir.exists():
        for f in img_dir.glob("scene_*.error.txt"):
            m = _ERROR_NAME_RE.match(f.name)
            if m:
                errors.append(int(m.group(1)))
    errors = sorted(errors)
    payload = {
        "prompt_count": len(prompt_ids),
        "image_done_count": len(done),
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

    p_run = sub.add_parser("run", help="anima_prompts から workflow 投入＋画像保存")
    p_run.add_argument("work_dir")
    p_run.add_argument("--scene-id", type=int, default=None)
    p_run.add_argument("--limit", type=int, default=None)
    p_run.add_argument("--server", default=DEFAULT_SERVER)
    p_run.add_argument("--workflow", default=None,
                       help="workflow JSON path (default: ../workflows/anima_base.api.json)")
    p_run.add_argument("--resolution", default="1024x1024")
    p_run.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    p_run.add_argument("--force", action="store_true",
                       help="既存画像があってもスキップせず再生成")
    p_run.set_defaults(func=cmd_run)

    p_st = sub.add_parser("status", help="画像生成進捗 JSON")
    p_st.add_argument("work_dir")
    p_st.set_defaults(func=cmd_status)

    args = parser.parse_args(argv)
    work_dir = Path(args.work_dir)
    if not work_dir.exists():
        print(f"[ERROR] work_dir not found: {work_dir}", file=sys.stderr)
        return 2
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
