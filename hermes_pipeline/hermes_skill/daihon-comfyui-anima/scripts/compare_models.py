"""Daihon ComfyUI Anima — Model/LoRA 比較スクリプト

Scene 1 を以下 4 構成で生成して比較:
  A: anima-preview3-base + 2 LoRA + @style triggers
  B: AnimaYume v0.4 (純 fine-tune、LoRA なし)
  C: Animax v0.5 (純 fine-tune、LoRA なし)
  D: AnimaYume v0.4 + 2 LoRA + @style triggers

rgthree カスタムノード (Power Lora Loader / Power Prompt) を回避し、
ComfyUI 標準ノード (LoraLoaderModelOnly + CLIPTextEncode) でクリーンに構築する。
LoRA は CG ガイド §07 推奨通り UNet のみに適用（CLIP には乗せない）。

公平比較のため全 variant で同一 seed を使用。
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

# 既存スクリプトと同じ HTTP ヘルパ・ノード送信ロジックを再利用
sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_anima_scene import (  # noqa: E402
    submit_workflow,
    wait_for_completion,
    extract_image_info,
    download_image,
    DEFAULT_SERVER,
)


# ─── 共通設定 ─────────────────────────────────
CLIP_NAME = "qwen_3_06b_base.safetensors"
VAE_NAME = "qwen_image_vae.safetensors"
SAMPLER = "er_sde"
SCHEDULER = "simple"
STEPS = 30
CFG = 4.0

# LoRA 構成 (Anima ベースモデル用)
LORA_SET = [
    ("anima-preview-3-masterpieces-v5.safetensors", 0.8),
    ("mixed_styles_anima_preview3_v4.safetensors", 0.7),
]

# Mixed Styles LoRA トリガー (@style_name)
STYLE_TRIGGERS = "very aesthetic, @aimpressionism, @sweetonedollar, @aruhshura,"


def build_workflow(
    unet_name: str,
    positive: str,
    negative: str,
    seed: int,
    filename_prefix: str,
    loras: list[tuple[str, float]] | None = None,
    width: int = 1024,
    height: int = 1024,
    steps: int = STEPS,
    cfg: float = CFG,
    sampler: str = SAMPLER,
    scheduler: str = SCHEDULER,
) -> dict:
    """rgthree 依存なしのクリーンな workflow JSON を構築。"""
    wf: dict = {
        "UNET": {
            "inputs": {"unet_name": unet_name, "weight_dtype": "default"},
            "class_type": "UNETLoader",
        },
        "CLIP": {
            "inputs": {"clip_name": CLIP_NAME, "type": "stable_diffusion", "device": "default"},
            "class_type": "CLIPLoader",
        },
        "VAE": {
            "inputs": {"vae_name": VAE_NAME},
            "class_type": "VAELoader",
        },
        "LATENT": {
            "inputs": {"width": width, "height": height, "batch_size": 1},
            "class_type": "EmptyLatentImage",
        },
        "POS": {
            "inputs": {"text": positive, "clip": ["CLIP", 0]},
            "class_type": "CLIPTextEncode",
        },
        "NEG": {
            "inputs": {"text": negative, "clip": ["CLIP", 0]},
            "class_type": "CLIPTextEncode",
        },
    }

    # LoRA を UNet にチェーン (CG ガイド §07: Anima は UNet only 推奨)
    model_ref: list = ["UNET", 0]
    if loras:
        for i, (name, strength) in enumerate(loras, start=1):
            node_id = f"LORA_{i}"
            wf[node_id] = {
                "inputs": {
                    "lora_name": name,
                    "strength_model": float(strength),
                    "model": model_ref,
                },
                "class_type": "LoraLoaderModelOnly",
            }
            model_ref = [node_id, 0]

    wf["KSAMPLER"] = {
        "inputs": {
            "seed": seed,
            "steps": steps,
            "cfg": cfg,
            "sampler_name": sampler,
            "scheduler": scheduler,
            "denoise": 1,
            "model": model_ref,
            "positive": ["POS", 0],
            "negative": ["NEG", 0],
            "latent_image": ["LATENT", 0],
        },
        "class_type": "KSampler",
    }
    wf["DECODE"] = {
        "inputs": {"samples": ["KSAMPLER", 0], "vae": ["VAE", 0]},
        "class_type": "VAEDecode",
    }
    wf["SAVE"] = {
        "inputs": {"filename_prefix": filename_prefix, "images": ["DECODE", 0]},
        "class_type": "SaveImage",
    }
    return wf


def get_variants() -> list[dict]:
    return [
        {
            "name": "A_anima_lora",
            "unet": "anima-preview3-base.safetensors",
            "loras": LORA_SET,
            "use_style_triggers": True,
        },
        {
            "name": "B_yume_nolora",
            "unet": "animayume_v04.safetensors",
            "loras": [],
            "use_style_triggers": False,
        },
        {
            "name": "C_animax_nolora",
            "unet": "animaxAnimaFinetune_v05.safetensors",
            "loras": [],
            "use_style_triggers": False,
        },
        {
            "name": "D_yume_lora",
            "unet": "animayume_v04.safetensors",
            "loras": LORA_SET,
            "use_style_triggers": True,
        },
    ]


def _parse_scenes(spec: str) -> list[int]:
    """`"1-5"` or `"1,3,5"` or `"1"` 形式を [int] に展開。"""
    out: list[int] = []
    for token in spec.split(","):
        token = token.strip()
        if "-" in token:
            a, b = token.split("-", 1)
            out.extend(range(int(a), int(b) + 1))
        elif token:
            out.append(int(token))
    return sorted(set(out))


def _filter_variants(letters: str) -> list[dict]:
    """`"A,D"` のような letter 列で variants をフィルタ。"""
    if not letters:
        return get_variants()
    wanted = {c.strip().upper() for c in letters.split(",") if c.strip()}
    return [v for v in get_variants() if v["name"][0].upper() in wanted]


def _generate_one(
    work_dir: Path, scene_id: int, variant: dict,
    server: str, seed: int, timeout: int, force: bool,
) -> dict:
    """1 (scene, variant) を生成して結果 dict を返す。既存ファイルがあれば skip。"""
    prompt_path = work_dir / "anima_prompts" / f"scene_{scene_id:03d}_prompt.json"
    if not prompt_path.exists():
        return {"scene_id": scene_id, "variant": variant["name"], "ok": False,
                "error": "prompt_json_not_found"}

    comparison_dir = work_dir / "images" / "comparison"
    comparison_dir.mkdir(parents=True, exist_ok=True)
    out_path = comparison_dir / f"scene_{scene_id:03d}_{variant['name']}.png"
    if out_path.exists() and not force:
        return {"scene_id": scene_id, "variant": variant["name"], "ok": True,
                "skipped": True, "output": str(out_path),
                "image_bytes": out_path.stat().st_size}

    prompt_data = json.loads(prompt_path.read_text(encoding="utf-8"))
    positive: str = prompt_data["positive"]
    negative: str = prompt_data["negative"]
    if variant["use_style_triggers"]:
        positive = STYLE_TRIGGERS + "\n" + positive

    filename_prefix = f"compare_scene_{scene_id:03d}_{variant['name']}"

    import time
    t0 = time.time()
    try:
        wf = build_workflow(
            unet_name=variant["unet"], positive=positive, negative=negative,
            seed=seed, filename_prefix=filename_prefix,
            loras=variant["loras"] or None,
        )
        prompt_id = submit_workflow(server, wf)
        entry = wait_for_completion(server, prompt_id, timeout=timeout)
        elapsed = round(time.time() - t0, 1)
        images = extract_image_info(entry)
        if not images:
            raise RuntimeError("no images in history entry")
        img_bytes = download_image(server, images[0])
        out_path.write_bytes(img_bytes)
        return {
            "scene_id": scene_id, "variant": variant["name"], "ok": True,
            "unet": variant["unet"],
            "loras": [n for n, _ in variant["loras"]],
            "style_triggers": variant["use_style_triggers"],
            "prompt_id": prompt_id, "elapsed_s": elapsed,
            "seed": seed,
            "output": str(out_path), "image_bytes": len(img_bytes),
        }
    except Exception as e:
        return {"scene_id": scene_id, "variant": variant["name"], "ok": False,
                "error": str(e), "unet": variant["unet"]}


def run(args) -> int:
    work_dir = Path(args.work_dir)
    if not work_dir.exists():
        print(f"[ERROR] work_dir not found: {work_dir}", file=sys.stderr)
        return 2

    variants = _filter_variants(args.variants)
    if not variants:
        print(f"[ERROR] no variants matched: {args.variants}", file=sys.stderr)
        return 2

    scene_ids = _parse_scenes(args.scenes) if args.scenes else [args.scene_id]

    # 同 scene 内では variants 間で同一 seed (公平比較), scene 間は異なる seed
    rng = random.Random(args.seed) if args.seed is not None else random.Random()
    scene_seeds: dict[int, int] = {
        sid: (args.seed if args.seed is not None and len(scene_ids) == 1
              else rng.randint(1, 2**63 - 1))
        for sid in scene_ids
    }

    print(json.dumps({
        "info": "compare start",
        "scene_ids": scene_ids,
        "variants": [v["name"] for v in variants],
        "scene_seeds": scene_seeds,
        "server": args.server,
    }, ensure_ascii=False), flush=True)

    results: list[dict] = []
    for sid in scene_ids:
        seed = scene_seeds[sid]
        for v in variants:
            r = _generate_one(work_dir, sid, v, args.server, seed, args.timeout, args.force)
            results.append(r)
            print(json.dumps(r, ensure_ascii=False), flush=True)

    summary = {
        "scene_count": len(scene_ids),
        "variant_count": len(variants),
        "total_jobs": len(results),
        "ok": sum(1 for r in results if r.get("ok")),
        "skipped": sum(1 for r in results if r.get("skipped")),
        "error": sum(1 for r in results if not r.get("ok")),
        "output_dir": str(work_dir / "images" / "comparison"),
    }
    print(json.dumps({"summary": summary}, ensure_ascii=False, indent=2))
    return 0 if summary["error"] == 0 else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("work_dir")
    parser.add_argument("--scene-id", type=int, default=1,
                        help="単一 scene 指定 (--scenes と排他)")
    parser.add_argument("--scenes", default=None,
                        help='複数指定 "1-5" or "1,2,3"')
    parser.add_argument("--variants", default=None,
                        help='対象 variants letters "A,D" (省略で全 4)')
    parser.add_argument("--server", default=DEFAULT_SERVER)
    parser.add_argument("--seed", type=int, default=None,
                        help="単一 scene なら共通 seed、複数なら RNG の初期 seed")
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--force", action="store_true",
                        help="既存 png があっても上書き生成")
    args = parser.parse_args(argv)
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
