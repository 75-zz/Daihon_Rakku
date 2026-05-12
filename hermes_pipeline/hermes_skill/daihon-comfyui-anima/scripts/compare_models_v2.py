"""Daihon ComfyUI Anima - Model/LoRA/Tag 包括比較スクリプト (v2)

CIVITAI リサーチを踏まえ、現行 A/D 構成の「なんか変」問題切り分け用に
モデル x LoRA x タグプロファイル x サンプラー の 15 構成で総当たり比較する。

主な変更点 (v1=compare_models.py 比):
- Tag profile を 4 種類用意 (MIN_OFFICIAL / AESTHETIC / AESTHETIC_STYLED / CURRENT_VERBOSE)
- Negative profile を 2 種類 (MIN / CURRENT)
- Mixed Styles LoRA は強度 0.7 -> 0.3 に下げた variant を含む
- Score_X + masterpiece 併用は公式 OK だが、量を絞る (score_9, score_8_up のみ)
- "anime style/cel shading/..." 等の非 Danbooru タグは MIN/AESTHETIC では除外
- AnimaYume / Animax の単体運用 variant を追加 (LoRA なし)
- Sampler は euler_a / dpmpp_2m_sde_gpu も比較対象に追加

scene_NNN_prompt.json の Grok 本体部分のみを取り出し、各 variant でプロファイルを
動的注入する。出力は images/comparison_v2/scene_NNN_<variant_name>.png。
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_anima_scene import (  # noqa: E402
    submit_workflow,
    wait_for_completion,
    extract_image_info,
    download_image,
    DEFAULT_SERVER,
)


CLIP_NAME = "qwen_3_06b_base.safetensors"
VAE_NAME = "qwen_image_vae.safetensors"

LORA_MASTERPIECES = "anima-preview-3-masterpieces-v5.safetensors"
LORA_MIXED_STYLES = "mixed_styles_anima_preview3_v4.safetensors"


# ─── Tag profiles ─────────────────────────────────
# Anima base 公式: [quality/meta/year/safety] [1girl/1boy] [character] [series] [artist] [general]
# Negative 公式推奨: "worst quality, low quality, score_1, score_2, score_3, artist name"

TAG_PROFILES: dict[str, dict] = {
    "min": {
        "prefix": (
            "masterpiece, best quality, score_9, score_8_up, very aesthetic,\n"
            "year 2025, newest, safe, highres,\n"
        ),
        "suffix": "",
    },
    "aesthetic": {
        "prefix": (
            "masterpiece, best quality, very aesthetic, score_9, score_8_up,\n"
            "year 2025, newest, safe, highres,\n"
            "1girl, solo,\n"
        ),
        "suffix": "",
    },
    "aesthetic_styled": {
        "prefix": (
            "masterpiece, best quality, very aesthetic, score_9, score_8_up,\n"
            "year 2025, newest, safe, highres,\n"
            "1girl, solo, @aimpressionism, @sweetonedollar,\n"
        ),
        "suffix": "",
    },
    "current_verbose": {
        # baseline: prepare_prompt.py 現行の prefix と同等
        "prefix": (
            "score_9, score_8_up, score_7_up, masterpiece, best quality, highres, "
            "year 2025, newest, sensitive,\n"
            "anime style, anime illustration, 2d anime art, cel shading, "
            "japanese anime aesthetic, soft lighting,\n"
            "very aesthetic, @aimpressionism, @sweetonedollar, @aruhshura,\n"
        ),
        "suffix": "",
    },
}

NEGATIVE_PROFILES: dict[str, str] = {
    "min": (
        "worst quality, low quality, score_1, score_2, score_3, artist name, "
        "text, watermark, signature"
    ),
    "current": (
        "text, speech bubble, dialogue, subtitle, watermark, signature, "
        "english text, letters, caption, words, logo, font, "
        "3d, realistic, photorealistic, photo, semi-realistic, "
        "american comic, western, marvel style, dc style, comic book, "
        "worst quality, low quality, bad anatomy, bad hands, "
        "deformed, blurry, jpeg artifacts, extra digit, missing fingers"
    ),
}


# ─── Variant matrix ───────────────────────────────
# loras: list of (name, strength) で UNet only に積む (CG ガイド §07: Anima は UNet only)
VARIANTS: list[dict] = [
    # Anima base
    {"name": "V01_base_none_min", "unet": "anima-preview3-base.safetensors",
     "loras": [], "tag": "min", "neg": "min",
     "sampler": "er_sde", "scheduler": "simple", "steps": 30, "cfg": 4.0},
    {"name": "V02_base_mast06_min", "unet": "anima-preview3-base.safetensors",
     "loras": [(LORA_MASTERPIECES, 0.6)], "tag": "min", "neg": "min",
     "sampler": "er_sde", "scheduler": "simple", "steps": 30, "cfg": 4.0},
    {"name": "V03_base_mast06_aesth", "unet": "anima-preview3-base.safetensors",
     "loras": [(LORA_MASTERPIECES, 0.6)], "tag": "aesthetic", "neg": "min",
     "sampler": "er_sde", "scheduler": "simple", "steps": 30, "cfg": 4.0},
    {"name": "V04_base_mast05_mix03_styled", "unet": "anima-preview3-base.safetensors",
     "loras": [(LORA_MASTERPIECES, 0.5), (LORA_MIXED_STYLES, 0.3)],
     "tag": "aesthetic_styled", "neg": "min",
     "sampler": "er_sde", "scheduler": "simple", "steps": 30, "cfg": 4.0},
    {"name": "V05_base_mast08_mix07_verbose", "unet": "anima-preview3-base.safetensors",
     "loras": [(LORA_MASTERPIECES, 0.8), (LORA_MIXED_STYLES, 0.7)],
     "tag": "current_verbose", "neg": "current",
     "sampler": "er_sde", "scheduler": "simple", "steps": 30, "cfg": 4.0},

    # AnimaYume
    {"name": "V06_yume_none_min", "unet": "animayume_v04.safetensors",
     "loras": [], "tag": "min", "neg": "min",
     "sampler": "er_sde", "scheduler": "simple", "steps": 30, "cfg": 4.0},
    {"name": "V07_yume_none_aesth", "unet": "animayume_v04.safetensors",
     "loras": [], "tag": "aesthetic", "neg": "min",
     "sampler": "er_sde", "scheduler": "simple", "steps": 30, "cfg": 4.0},
    {"name": "V08_yume_mast05_aesth", "unet": "animayume_v04.safetensors",
     "loras": [(LORA_MASTERPIECES, 0.5)], "tag": "aesthetic", "neg": "min",
     "sampler": "er_sde", "scheduler": "simple", "steps": 30, "cfg": 4.0},
    {"name": "V09_yume_mast05_mix03_styled", "unet": "animayume_v04.safetensors",
     "loras": [(LORA_MASTERPIECES, 0.5), (LORA_MIXED_STYLES, 0.3)],
     "tag": "aesthetic_styled", "neg": "min",
     "sampler": "er_sde", "scheduler": "simple", "steps": 30, "cfg": 4.0},

    # Animax
    {"name": "V10_animax_none_min", "unet": "animaxAnimaFinetune_v05.safetensors",
     "loras": [], "tag": "min", "neg": "min",
     "sampler": "er_sde", "scheduler": "simple", "steps": 30, "cfg": 4.0},
    {"name": "V11_animax_none_aesth", "unet": "animaxAnimaFinetune_v05.safetensors",
     "loras": [], "tag": "aesthetic", "neg": "min",
     "sampler": "er_sde", "scheduler": "simple", "steps": 30, "cfg": 4.0},
    {"name": "V12_animax_mast05_aesth", "unet": "animaxAnimaFinetune_v05.safetensors",
     "loras": [(LORA_MASTERPIECES, 0.5)], "tag": "aesthetic", "neg": "min",
     "sampler": "er_sde", "scheduler": "simple", "steps": 30, "cfg": 4.0},

    # Sampler 比較 (Anima base + masterpieces 0.6 + aesthetic 固定)
    {"name": "V13_base_mast06_aesth_eulera", "unet": "anima-preview3-base.safetensors",
     "loras": [(LORA_MASTERPIECES, 0.6)], "tag": "aesthetic", "neg": "min",
     "sampler": "euler_ancestral", "scheduler": "normal", "steps": 30, "cfg": 5.0},
    {"name": "V14_base_mast06_aesth_dpmpp", "unet": "anima-preview3-base.safetensors",
     "loras": [(LORA_MASTERPIECES, 0.6)], "tag": "aesthetic", "neg": "min",
     "sampler": "dpmpp_2m_sde_gpu", "scheduler": "karras", "steps": 30, "cfg": 4.0},
    {"name": "V15_yume_mast05_aesth_eulera", "unet": "animayume_v04.safetensors",
     "loras": [(LORA_MASTERPIECES, 0.5)], "tag": "aesthetic", "neg": "min",
     "sampler": "euler_ancestral", "scheduler": "normal", "steps": 30, "cfg": 5.0},

    # ─── V16-V25: AnimaYume sweet-spot 探索 (workflow-designer Task #4) ────────────
    # V16-V20: masterpieces strength sweep (全 AESTHETIC tag / er_sde 固定)
    {"name": "V16_yume_mast03_aesth", "unet": "animayume_v04.safetensors",
     "loras": [(LORA_MASTERPIECES, 0.3)], "tag": "aesthetic", "neg": "min",
     "sampler": "er_sde", "scheduler": "simple", "steps": 30, "cfg": 4.0},
    {"name": "V17_yume_mast04_aesth", "unet": "animayume_v04.safetensors",
     "loras": [(LORA_MASTERPIECES, 0.4)], "tag": "aesthetic", "neg": "min",
     "sampler": "er_sde", "scheduler": "simple", "steps": 30, "cfg": 4.0},
    # V18 = V08 の再録 (新 anima_prompts でのベースライン確認用)
    {"name": "V18_yume_mast05_aesth_baseline", "unet": "animayume_v04.safetensors",
     "loras": [(LORA_MASTERPIECES, 0.5)], "tag": "aesthetic", "neg": "min",
     "sampler": "er_sde", "scheduler": "simple", "steps": 30, "cfg": 4.0},
    {"name": "V19_yume_mast06_aesth", "unet": "animayume_v04.safetensors",
     "loras": [(LORA_MASTERPIECES, 0.6)], "tag": "aesthetic", "neg": "min",
     "sampler": "er_sde", "scheduler": "simple", "steps": 30, "cfg": 4.0},
    {"name": "V20_yume_mast07_aesth", "unet": "animayume_v04.safetensors",
     "loras": [(LORA_MASTERPIECES, 0.7)], "tag": "aesthetic", "neg": "min",
     "sampler": "er_sde", "scheduler": "simple", "steps": 30, "cfg": 4.0},

    # V21: 縦長 1024x1536 (AnimaYume 公式推奨縦長)
    {"name": "V21_yume_mast05_aesth_portrait", "unet": "animayume_v04.safetensors",
     "loras": [(LORA_MASTERPIECES, 0.5)], "tag": "aesthetic", "neg": "min",
     "sampler": "er_sde", "scheduler": "simple", "steps": 30, "cfg": 4.0,
     "width": 1024, "height": 1536},

    # V22: 横長 1152x896 (Anima 公式推奨横長)
    {"name": "V22_yume_mast05_aesth_landscape", "unet": "animayume_v04.safetensors",
     "loras": [(LORA_MASTERPIECES, 0.5)], "tag": "aesthetic", "neg": "min",
     "sampler": "er_sde", "scheduler": "simple", "steps": 30, "cfg": 4.0,
     "width": 1152, "height": 896},

    # V23: 高品質設定 steps=50 / CFG=5.0
    {"name": "V23_yume_mast05_aesth_hq50", "unet": "animayume_v04.safetensors",
     "loras": [(LORA_MASTERPIECES, 0.5)], "tag": "aesthetic", "neg": "min",
     "sampler": "er_sde", "scheduler": "simple", "steps": 50, "cfg": 5.0},

    # V24: 最小プロンプト (min tag) で Grok 本体をそのまま活かす
    {"name": "V24_yume_mast05_min_clean", "unet": "animayume_v04.safetensors",
     "loras": [(LORA_MASTERPIECES, 0.5)], "tag": "min", "neg": "min",
     "sampler": "er_sde", "scheduler": "simple", "steps": 30, "cfg": 4.0},

    # V25: 追加 LoRA スロット
    # CIVITAI 調査では中野一花用 Anima 互換 LoRA は不在 / Anima Turbo は CFG=1/steps=8-12 と特殊
    # → 通常運用と切り離して別途試行する想定。ここでは masterpieces のみで V18 の seed 違いを兼ねる
    {"name": "V25_yume_mast05_aesth_seed7", "unet": "animayume_v04.safetensors",
     "loras": [(LORA_MASTERPIECES, 0.5)], "tag": "aesthetic", "neg": "min",
     "sampler": "er_sde", "scheduler": "simple", "steps": 30, "cfg": 4.0,
     "seed_override": 7},
]


# ─── Grok 本体抽出 ─────────────────────────────────
# 現行 prepare_prompt.py の _ANIMA_QUALITY_PREFIX は 2 行で構成される:
#   "score_9, score_8_up, score_7_up, masterpiece, best quality, highres, year 2025, newest, sensitive,\n"
#   "anime style, anime illustration, 2d anime art, cel shading, japanese anime aesthetic, soft lighting,\n"
# その後ろが Grok 生成本体 (character/series タグ + 自然言語記述)。
def extract_grok_body(positive: str) -> str:
    """既存の anima_prompts/scene_NNN_prompt.json の positive から
    Grok 生成本体部分のみ取り出す。

    現行 prefix の判別キーワードを含む冒頭行を順次スキップし、
    最初に該当しない行 (キャラタグ等) 以降を本体として返す。
    """
    quality_keywords = (
        "score_", "masterpiece", "best quality", "very aesthetic",
        "year 2025", "newest", "safe", "sensitive", "highres",
        "anime style", "anime illustration", "2d anime art", "cel shading",
        "japanese anime", "soft lighting",
        "@aimpressionism", "@sweetonedollar", "@aruhshura",
        "1girl, solo", "1girl,solo",
    )
    lines = positive.split("\n")
    body_start = 0
    for i, line in enumerate(lines):
        stripped = line.strip().lower()
        if not stripped:
            continue
        # 行に含まれるトークンが quality_keywords 由来のみなら quality prefix と判定
        is_quality = any(kw in stripped for kw in quality_keywords)
        if not is_quality:
            body_start = i
            break
    else:
        # ループ完走 = 全行が quality prefix だった (異常) → 本体なしと判定
        return ""
    return "\n".join(lines[body_start:]).strip()


def build_positive(profile: dict, grok_body: str) -> str:
    return profile["prefix"] + grok_body + (profile.get("suffix") or "")


# ─── Workflow ─────────────────────────────────────
def build_workflow(
    unet_name: str, positive: str, negative: str, seed: int,
    filename_prefix: str, loras: list[tuple[str, float]] | None = None,
    width: int = 1024, height: int = 1024,
    steps: int = 30, cfg: float = 4.0,
    sampler: str = "er_sde", scheduler: str = "simple",
) -> dict:
    wf: dict = {
        "UNET": {"inputs": {"unet_name": unet_name, "weight_dtype": "default"},
                 "class_type": "UNETLoader"},
        "CLIP": {"inputs": {"clip_name": CLIP_NAME, "type": "stable_diffusion",
                            "device": "default"},
                 "class_type": "CLIPLoader"},
        "VAE":  {"inputs": {"vae_name": VAE_NAME}, "class_type": "VAELoader"},
        "LATENT": {"inputs": {"width": width, "height": height, "batch_size": 1},
                   "class_type": "EmptyLatentImage"},
        "POS": {"inputs": {"text": positive, "clip": ["CLIP", 0]},
                "class_type": "CLIPTextEncode"},
        "NEG": {"inputs": {"text": negative, "clip": ["CLIP", 0]},
                "class_type": "CLIPTextEncode"},
    }
    model_ref: list = ["UNET", 0]
    if loras:
        for i, (name, strength) in enumerate(loras, start=1):
            node_id = f"LORA_{i}"
            wf[node_id] = {
                "inputs": {"lora_name": name, "strength_model": float(strength),
                           "model": model_ref},
                "class_type": "LoraLoaderModelOnly",
            }
            model_ref = [node_id, 0]
    wf["KSAMPLER"] = {
        "inputs": {"seed": seed, "steps": steps, "cfg": cfg,
                   "sampler_name": sampler, "scheduler": scheduler,
                   "denoise": 1, "model": model_ref,
                   "positive": ["POS", 0], "negative": ["NEG", 0],
                   "latent_image": ["LATENT", 0]},
        "class_type": "KSampler",
    }
    wf["DECODE"] = {"inputs": {"samples": ["KSAMPLER", 0], "vae": ["VAE", 0]},
                    "class_type": "VAEDecode"}
    wf["SAVE"]  = {"inputs": {"filename_prefix": filename_prefix,
                              "images": ["DECODE", 0]},
                    "class_type": "SaveImage"}
    return wf


# ─── 1 (scene, variant) 実行 ──────────────────────
def generate_one(
    work_dir: Path, scene_id: int, variant: dict,
    server: str, seed: int, timeout: int, force: bool,
    output_subdir: str = "comparison_v2",
    seed_label: str | None = None,
) -> dict:
    prompt_path = work_dir / "anima_prompts" / f"scene_{scene_id:03d}_prompt.json"
    if not prompt_path.exists():
        return {"scene_id": scene_id, "variant": variant["name"], "ok": False,
                "error": "prompt_json_not_found"}

    out_dir = work_dir / "images" / output_subdir
    out_dir.mkdir(parents=True, exist_ok=True)
    # seed_label が指定された場合は ファイル名に _seed{label} を付加 (複数seed比較用)
    suffix = f"_seed{seed_label}" if seed_label else ""
    out_path = out_dir / f"scene_{scene_id:03d}_{variant['name']}{suffix}.png"
    if out_path.exists() and not force:
        return {"scene_id": scene_id, "variant": variant["name"], "ok": True,
                "skipped": True, "output": str(out_path),
                "image_bytes": out_path.stat().st_size}

    prompt_data = json.loads(prompt_path.read_text(encoding="utf-8"))
    original_positive: str = prompt_data["positive"]

    # character.json 駆動の新JSON (character_source あり) は prepare_prompt.py 側で
    # 既に quality prefix + char_block + Grok body が確定しているため、ここでは
    # TAG_PROFILES の上書きをスキップして positive/negative をそのまま使う。
    char_source = (prompt_data.get("character_source") or "none")
    if char_source != "none":
        positive = original_positive
        negative = prompt_data["negative"]
    else:
        grok_body = extract_grok_body(original_positive)
        if not grok_body:
            return {"scene_id": scene_id, "variant": variant["name"], "ok": False,
                    "error": "grok_body_empty_after_extraction"}
        tag_profile = TAG_PROFILES[variant["tag"]]
        negative = NEGATIVE_PROFILES[variant["neg"]]
        positive = build_positive(tag_profile, grok_body)

    filename_prefix = f"compare_v2_scene_{scene_id:03d}_{variant['name']}{suffix}"

    # variant.seed_override で固定 seed を強制可能 (再現性テスト用)
    effective_seed = variant.get("seed_override", seed)

    import time
    t0 = time.time()
    try:
        wf = build_workflow(
            unet_name=variant["unet"], positive=positive, negative=negative,
            seed=effective_seed, filename_prefix=filename_prefix,
            loras=variant["loras"] or None,
            steps=variant.get("steps", 30), cfg=variant.get("cfg", 4.0),
            sampler=variant.get("sampler", "er_sde"),
            scheduler=variant.get("scheduler", "simple"),
            width=variant.get("width", 1024),
            height=variant.get("height", 1024),
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
            "tag": variant["tag"], "neg": variant["neg"],
            "sampler": variant["sampler"], "cfg": variant["cfg"],
            "width": variant.get("width", 1024),
            "height": variant.get("height", 1024),
            "prompt_id": prompt_id, "elapsed_s": elapsed, "seed": effective_seed,
            "output": str(out_path), "image_bytes": len(img_bytes),
        }
    except Exception as e:
        return {"scene_id": scene_id, "variant": variant["name"], "ok": False,
                "error": str(e), "unet": variant["unet"]}


def _parse_scenes(spec: str) -> list[int]:
    out: list[int] = []
    for token in spec.split(","):
        token = token.strip()
        if "-" in token:
            a, b = token.split("-", 1)
            out.extend(range(int(a), int(b) + 1))
        elif token:
            out.append(int(token))
    return sorted(set(out))


def _filter_variants(spec: str | None) -> list[dict]:
    if not spec:
        return list(VARIANTS)
    wanted = {tok.strip().upper() for tok in spec.split(",") if tok.strip()}
    out = []
    for v in VARIANTS:
        # V01, V02, ... の prefix を許容
        prefix = v["name"].split("_", 1)[0].upper()
        if prefix in wanted or v["name"].upper() in wanted:
            out.append(v)
    return out


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

    # --seeds が指定されたら複数seed生成モード (各シーン×各seed×各variant)
    multi_seeds: list[int] | None = None
    if args.seeds:
        multi_seeds = []
        for tok in args.seeds.split(","):
            tok = tok.strip()
            if tok:
                multi_seeds.append(int(tok))

    rng = random.Random(args.seed) if args.seed is not None else random.Random()
    if multi_seeds:
        # 各シーンで全 seed を使用 (シーン横断で同 seed = 同 noise なので注意だが、
        # 構図ガチャ用なので問題なし)
        scene_seeds = {sid: list(multi_seeds) for sid in scene_ids}
    elif args.seed is not None and len(scene_ids) == 1:
        scene_seeds = {scene_ids[0]: [args.seed]}
    else:
        scene_seeds = {sid: [rng.randint(1, 2**63 - 1)] for sid in scene_ids}

    print(json.dumps({
        "info": "compare_v2 start",
        "scene_ids": scene_ids,
        "variant_count": len(variants),
        "variants": [v["name"] for v in variants],
        "scene_seeds": scene_seeds,
        "multi_seeds": multi_seeds,
        "server": args.server,
    }, ensure_ascii=False), flush=True)

    results: list[dict] = []
    for sid in scene_ids:
        seeds_for_scene = scene_seeds[sid]
        for v in variants:
            for seed in seeds_for_scene:
                label = str(seed) if multi_seeds else None
                r = generate_one(work_dir, sid, v, args.server, seed,
                                 args.timeout, args.force,
                                 output_subdir=args.output_subdir,
                                 seed_label=label)
                results.append(r)
                print(json.dumps(r, ensure_ascii=False), flush=True)

    summary = {
        "scene_count": len(scene_ids),
        "variant_count": len(variants),
        "total_jobs": len(results),
        "ok": sum(1 for r in results if r.get("ok")),
        "skipped": sum(1 for r in results if r.get("skipped")),
        "error": sum(1 for r in results if not r.get("ok")),
        "output_dir": str(work_dir / "images" / args.output_subdir),
    }
    print(json.dumps({"summary": summary}, ensure_ascii=False, indent=2))
    return 0 if summary["error"] == 0 else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("work_dir")
    parser.add_argument("--scene-id", type=int, default=1)
    parser.add_argument("--scenes", default=None,
                        help='例: "1-5" or "1,3,5"')
    parser.add_argument("--variants", default=None,
                        help='例: "V01,V03,V05" (省略で全15)')
    parser.add_argument("--server", default=DEFAULT_SERVER)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--seeds", default=None,
                        help='複数 seed カンマ区切り (例: "42,7,123"). '
                             '指定時は各シーン×各seedを生成し、ファイル名に _seedX を付加。'
                             '--seed と排他 (--seeds 優先)')
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--output-subdir", default="comparison_v2",
                        help="images/<subdir>/ 配下に出力 (例: comparison_v3)")
    args = parser.parse_args(argv)
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
