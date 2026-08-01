#!/usr/bin/env python3
"""Create and publish PelicanBench Hugging Face dataset and Spaces."""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGETS = (
    ("dataset", "edithatogo/pelican-bench", ROOT / "hf/dataset"),
    ("space", "edithatogo/pelican-bench-explorer", ROOT / "hf/space"),
    ("space", "edithatogo/pelican-bench-openenv", ROOT / "hf/openenv"),
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--private", action="store_true")
    args = parser.parse_args()
    for repo_type, repo_id, folder in TARGETS:
        print(f"{repo_type}: {repo_id} <- {folder.relative_to(ROOT)}")
    if not args.apply:
        print("Dry run only. Use --apply with an authenticated HF_TOKEN or hf auth login.")
        return 0
    try:
        from huggingface_hub import HfApi
    except ImportError as exc:
        raise SystemExit("Install the hub extra: uv sync --extra hub") from exc
    api = HfApi()
    identity = api.whoami()
    print(f"Authenticated as {identity.get('name') or identity.get('fullname')}")
    for repo_type, repo_id, folder in TARGETS:
        kwargs = {"repo_id": repo_id, "repo_type": repo_type, "exist_ok": True, "private": args.private}
        if repo_type == "space":
            kwargs["space_sdk"] = "gradio"
        api.create_repo(**kwargs)
        api.upload_folder(repo_id=repo_id, repo_type=repo_type, folder_path=folder, commit_message="chore: publish PelicanBench scaffold")
    print("Hugging Face repositories synchronized.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
