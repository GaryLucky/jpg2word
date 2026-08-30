import argparse
from pathlib import Path

import jpg_to_md
from md2word import markdown_to_docx



DEFAULT_SOURCE_DIR = r"C:\Users\Gary\Desktop\jpg2word\jpg_files\扫描4\176、#何长工回忆：马日事变和进军井冈山"



DEFAULT_OUTPUT_DIR = ""


def default_docx_path(source_dir: str, output_dir: str) -> Path:
    source_name = Path(source_dir).name.strip() or "final_book"
    return Path(output_dir) / f"{source_name}.docx"


def get_subdirectories(directory: str | Path) -> list[Path]:
    root = Path(directory)
    if not root.exists():
        raise FileNotFoundError(f"目录不存在：{root}")
    if not root.is_dir():
        raise NotADirectoryError(f"不是目录：{root}")

    return sorted((path for path in root.iterdir() if path.is_dir()), key=lambda path: path.name)


def has_jpg_images(directory: str | Path) -> bool:
    root = Path(directory)
    return any(
        path.is_file() and path.suffix.lower() in {".jpg", ".jpeg"}
        for path in root.rglob("*")
    )


def get_processing_directories(source_dir: str | Path) -> list[Path]:
    root = Path(source_dir)
    subdirectories = [
        path
        for path in get_subdirectories(root)
        if path.name.lower() not in {"output", "chunks", "__pycache__"} and has_jpg_images(path)
    ]
    return subdirectories if subdirectories else [root]


def get_output_dir(source_dir: Path, output_dir: str, total_jobs: int) -> Path:
    if total_jobs == 1 and output_dir:
        return Path(output_dir)
    return source_dir / "output"


def build_jpg_args(args: argparse.Namespace, source_dir: Path, output_dir: Path) -> list[str]:
    jpg_args = [
        "--source-dir",
        str(source_dir),
        "--output-dir",
        str(output_dir),
        "--model",
        args.model,
        "--base-url",
        args.base_url,
        "--batch-size",
        str(args.batch_size),
        "--limit",
        str(args.limit),
        "--timeout",
        str(args.timeout),
        "--max-retries",
        str(args.max_retries),
        "--max-tokens",
        str(args.max_tokens),
        "--reasoning-effort",
        args.reasoning_effort,
    ]
    if args.force:
        jpg_args.append("--force")
    if args.merge_only:
        jpg_args.append("--merge-only")
    if args.dry_run:
        jpg_args.append("--dry-run")
    return jpg_args


def run_one_source(args: argparse.Namespace, source_dir: Path, output_dir: Path, total_jobs: int) -> int:
    print(f"开始处理目录：{source_dir}", flush=True)
    print(f"输出目录：{output_dir}", flush=True)

    code = jpg_to_md.main(build_jpg_args(args, source_dir, output_dir))
    if code != 0 or args.dry_run:
        return code

    md_path = output_dir / "final_book.md"
    manifest_path = output_dir / "manifest.md"
    docx_path = Path(args.docx) if args.docx else default_docx_path(str(source_dir), str(output_dir))
    markdown_to_docx(md_path, docx_path, manifest_path)
    print(f"已生成 Word：{docx_path}", flush=True)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="一键执行 JPG OCR，并把 final_book.md 转换成 Word。")
    parser.add_argument("--source-dir", default=DEFAULT_SOURCE_DIR, help="JPG 源目录。")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help="输出目录。源目录没有子目录时可指定；有子目录时固定使用每个子目录下的 output。")
    parser.add_argument("--model", default=jpg_to_md.DEFAULT_MODEL, help="视觉模型名称。")
    parser.add_argument("--base-url", default=jpg_to_md.DEFAULT_BASE_URL, help="Ark OpenAI 兼容 API 地址。")
    parser.add_argument("--batch-size", type=int, default=3, help="每批 OCR 图片数量，默认 5。")
    parser.add_argument("--limit", type=int, default=0, help="只处理前 N 张图片，默认 0 表示处理全部。")
    parser.add_argument("--force", action="store_true", help="重新生成已存在的 OCR 分块。")
    parser.add_argument("--merge-only", action="store_true", help="只合并已有 OCR 分块并导出 Word。")
    parser.add_argument("--dry-run", action="store_true", help="只检查图片排序和分批，不调用模型，不导出 Word。")
    parser.add_argument("--timeout", type=int, default=300, help="每次模型调用超时时间，单位秒。")
    parser.add_argument("--max-retries", type=int, default=3, help="每批失败后的最大重试次数。")
    parser.add_argument("--max-tokens", type=int, default=8192, help="每批最大输出 token 数。")
    parser.add_argument(
        "--reasoning-effort",
        default="minimal",
        choices=["minimal", "low", "medium", "high"],
        help="推理深度，默认 minimal，表示尽量不深度思考。",
    )
    parser.add_argument("--docx", default="", help="Word 输出路径，默认使用源目录名称。")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    source_dirs = get_processing_directories(args.source_dir)
    total_jobs = len(source_dirs)
    if total_jobs > 1 and args.docx:
        print("处理多个子目录时不能使用 --docx 指定单个 Word 输出路径。", flush=True)
        return 1

    if total_jobs > 1:
        print(f"发现 {total_jobs} 个子目录，将逐个在子目录下生成 output。", flush=True)
    else:
        print("未发现子目录，将扫描当前源目录并在当前目录下生成 output。", flush=True)

    for index, source_dir in enumerate(source_dirs, start=1):
        print(f"\n[{index}/{total_jobs}]", flush=True)
        output_dir = get_output_dir(source_dir, args.output_dir, total_jobs)
        code = run_one_source(args, source_dir, output_dir, total_jobs)
        if code != 0:
            return code

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
