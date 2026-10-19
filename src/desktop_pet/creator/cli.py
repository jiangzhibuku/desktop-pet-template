"""Command line interface for the character creator.

Examples
--------
    python -m desktop_pet.creator --name 雪球 --prompt "白色小猫，戴红围巾"
    python -m desktop_pet.creator --name 雪球 --image .\\cat.png
    python -m desktop_pet.creator --name 旧角色 --frames D:\\old\\桌面宠物图片 --link
    python -m desktop_pet.creator --list
    python -m desktop_pet.creator --use 雪球
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ..config import load_config
from ..paths import build_paths
from .pack import list_packs, open_path, use_pack
from .pipeline import create_from_image, create_from_prompt, import_frames


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python create_pet.py",
        description="把一张图或一句话变成桌面宠物角色包。",
    )
    parser.add_argument("--name", help="角色名；文字模式可省略，会从描述里提取")
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--prompt", help="文字描述，例如：白色小猫，戴红围巾")
    actions.add_argument("--image", help="单张角色图（推荐透明 PNG）")
    actions.add_argument("--frames", help="已有的动画帧文件夹")
    actions.add_argument("--list", action="store_true", help="列出已安装角色")
    actions.add_argument("--use", metavar="NAME", help="切换当前角色")
    actions.add_argument("--preview", metavar="NAME", help="打开角色预览图")

    parser.add_argument("--ai-spec", action="store_true", help="用大模型解析文字描述（可选）")
    parser.add_argument("--ai-image", action="store_true", help="用图片模型生成角色图（可选）")
    parser.add_argument("--link", action="store_true", help="配合 --frames：只引用原文件夹，不复制")
    parser.add_argument(
        "--cutout",
        choices=["auto", "rembg", "none"],
        default=None,
        help="抠图方式：auto 自动 / rembg 本地智能 / none 保留背景",
    )
    parser.add_argument(
        "--cutout-model",
        default=None,
        help="rembg 模型，默认 isnet-anime",
    )
    parser.add_argument("--keep-bg", action="store_true", help="保留原图背景，等同于 --cutout none")
    parser.add_argument("--tolerance", type=int, default=32, help="去背景容差，默认 32")
    parser.add_argument("--author", default="unknown", help="作者署名")
    parser.add_argument("--license", default="unverified", help="素材授权说明")
    parser.add_argument("--overwrite", action="store_true", help="覆盖同名角色")
    parser.add_argument("--no-use", action="store_true", help="生成后不切换为当前角色")
    parser.add_argument("--open", action="store_true", help="生成后打开预览图")
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    args = build_parser().parse_args(argv)
    paths = build_paths()
    config = load_config(paths)
    make_default = not args.no_use
    cutout = "none" if args.keep_bg else (args.cutout or config.creator.cutout)
    cutout_model = args.cutout_model or config.creator.cutout_model

    try:
        if args.list:
            packs = list_packs(paths)
            if not packs:
                print("还没有自定义角色，当前使用内置的 mochi。")
                return 0
            print(f"{'名字':<18} {'物种':<8} 路径")
            for pack in packs:
                print(f"{pack['key']:<18} {pack['species']:<8} {pack['directory']}")
            return 0

        if args.use:
            use_pack(paths, args.use)
            print(f"已切换当前角色：{args.use}")
            return 0

        if args.preview:
            for pack in list_packs(paths):
                if pack["key"] == args.preview:
                    preview = Path(pack["directory"]) / "preview.png"
                    if preview.is_file():
                        open_path(preview)
                        print(f"已打开：{preview}")
                        return 0
            print(f"没找到角色：{args.preview}")
            return 1

        if args.image:
            cutout_notices: list[str] = []
            result = create_from_image(
                args.image,
                args.name or Path(args.image).stem,
                paths,
                author=args.author,
                license=args.license,
                tolerance=max(0, min(120, args.tolerance)),
                cutout=cutout,
                cutout_model=cutout_model,
                notices=cutout_notices,
                overwrite=args.overwrite,
                make_default=make_default,
            )
            notices: list[str] = ["角色图：用户提供的图片", *cutout_notices]
        elif args.frames:
            result = import_frames(
                args.frames,
                args.name,
                paths,
                link=args.link,
                author=args.author,
                license=args.license,
                overwrite=args.overwrite,
                make_default=make_default,
            )
            notices = ["角色帧：导入已有文件夹" + ("（仅引用，不复制）" if args.link else "")]
        else:
            result, notices = create_from_prompt(
                args.prompt or "",
                args.name,
                paths,
                config=config,
                use_ai_spec=args.ai_spec,
                use_ai_image=args.ai_image,
                cutout=cutout,
                cutout_model=cutout_model,
                author=args.author,
                license=args.license,
                overwrite=args.overwrite,
                make_default=make_default,
            )

        print(f"已生成角色包：{result.key}")
        print(f"目录：{result.directory}")
        print(f"预览：{result.preview}")
        for notice in notices:
            print(f"  - {notice}")
        if make_default:
            print("已设为当前角色，下次启动生效；应用运行中可用「创建角色」即时切换。")
        if args.open and result.preview.is_file():
            open_path(result.preview)
        return 0
    except Exception as exc:
        print(f"失败：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
