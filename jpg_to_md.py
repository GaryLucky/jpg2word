import argparse
import base64
import os
import re
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

DEFAULT_SOURCE_DIR = r"C:\Users\Gary\Desktop\9、访问何长工同志谈话记录87"
DEFAULT_OUTPUT_DIR = r"C:\Users\Gary\Desktop\jpg2word\output"
DEFAULT_MODEL = "doubao-seed-2-1-pro-260628"
DEFAULT_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"


def natural_key(path: Path):
    parts = re.split(r"(\d+)", path.name)
    return [int(part) if part.isdigit() else part.lower() for part in parts]


def page_number(path: Path, fallback: int) -> str:
    numbers = re.findall(r"\d+", path.stem)
    return numbers[-1] if numbers else str(fallback)


def image_to_data_url(path: Path) -> str:
    mime = "image/jpeg"
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{data}"


def find_images(source_dir: Path) -> list[Path]:
    images = [
        path
        for path in source_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg"}
    ]
    return sorted(images, key=natural_key)


def chunked(items: list[Path], size: int):
    for index in range(0, len(items), size):
        yield index // size + 1, items[index : index + size]


def build_prompt(batch: list[Path], start_index: int) -> str:
    page_lines = []
    for offset, path in enumerate(batch):
        page_lines.append(f"- 第 {start_index + offset} 页：文件名 {path.name}")

    return (
        "你是一名严谨的中文手写史料 OCR 整理员。请按图片顺序逐页识别手写内容，输出 Markdown。\n\n"
        "要求：\n"
        "1. 必须逐页输出，每页以二级标题开头：## 第N页（文件名）\n"
        "2. 尽量忠实转写原文，保留原有段落、换行、标点、人物名、日期和数字。\n"
        "3. 不要改写、总结或润色原文。\n"
        "4. 难以辨认的字用 [?] 标记；推测但不确定的字词用 （疑为：...）标记。\n"
        "5. 页面之间用单独一行 --- 分隔。\n"
        "6. 只输出 Markdown 正文，不要输出解释。\n\n"
        "本批页面：\n"
        + "\n".join(page_lines)
    )


def log(message: str) -> None:
    print(message, flush=True)


def call_ocr(
    client,
    model: str,
    batch: list[Path],
    start_index: int,
    max_retries: int,
    timeout: int,
    max_tokens: int,
) -> str:
    content = [{"type": "text", "text": build_prompt(batch, start_index)}]
    for path in batch:
        content.append({"type": "image_url", "image_url": {"url": image_to_data_url(path)}})

    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": content}],
                timeout=timeout,
                max_tokens=max_tokens,
            )
            text = response.choices[0].message.content
            if text:
                return text.strip()
            return str(response)
        except Exception as exc:
            last_error = exc
            if attempt == max_retries:
                break
            sleep_seconds = min(60, 2**attempt)
            log(f"调用失败，第 {attempt}/{max_retries} 次重试前等待 {sleep_seconds}s：{exc}")
            time.sleep(sleep_seconds)
    raise RuntimeError(f"OCR 调用失败：{last_error}") from last_error


def write_manifest(output_dir: Path, images: list[Path]) -> None:
    manifest_path = output_dir / "manifest.md"
    lines = ["# JPG OCR 文件清单", ""]
    for index, path in enumerate(images, start=1):
        lines.append(f"{index}. `{path.name}` -> `{path}`")
    manifest_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def merge_chunks(chunks_dir: Path, final_path: Path) -> None:
    chunk_files = sorted(chunks_dir.glob("batch_*.md"))
    merged_parts = []
    for chunk_file in chunk_files:
        text = chunk_file.read_text(encoding="utf-8").strip()
        if text:
            merged_parts.append(text)
    final_path.write_text("\n\n---\n\n".join(merged_parts).strip() + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="按文件名编号批量识别 JPG 手写页，并合并为 Markdown。")
    parser.add_argument("--source-dir", default=DEFAULT_SOURCE_DIR, help="JPG 源目录，默认读取桌面谈话记录目录。")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help="输出目录。")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="视觉模型名称。")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Ark OpenAI 兼容 API 地址。")
    parser.add_argument("--batch-size", type=int, default=5, help="每次喂给模型的页数，默认 5。")
    parser.add_argument("--max-retries", type=int, default=3, help="每批失败后的最大重试次数。")
    parser.add_argument("--timeout", type=int, default=300, help="每次模型调用超时时间，单位秒，默认 300。")
    parser.add_argument("--max-tokens", type=int, default=8192, help="每批最大输出 token 数，默认 8192。")
    parser.add_argument("--limit", type=int, default=0, help="只处理前 N 张图片，默认 0 表示处理全部。")
    parser.add_argument("--force", action="store_true", help="重新生成已存在的 batch_*.md。")
    parser.add_argument("--merge-only", action="store_true", help="只合并现有 chunks，不调用模型。")
    parser.add_argument("--dry-run", action="store_true", help="只检查图片排序和分批，不调用模型。")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    load_dotenv(Path(__file__).resolve().with_name(".env"))

    source_dir = Path(args.source_dir)
    output_dir = Path(args.output_dir)
    chunks_dir = output_dir / "chunks"
    final_path = output_dir / "final_book.md"

    if not source_dir.exists():
        print(f"源目录不存在：{source_dir}", file=sys.stderr)
        return 1

    output_dir.mkdir(parents=True, exist_ok=True)
    chunks_dir.mkdir(parents=True, exist_ok=True)

    images = find_images(source_dir)
    if not images:
        print(f"没有找到 JPG/JPEG 文件：{source_dir}", file=sys.stderr)
        return 1
    if args.limit:
        images = images[: args.limit]

    write_manifest(output_dir, images)
    log(f"找到 {len(images)} 张图片。")
    log(f"输出目录：{output_dir}")

    if args.dry_run:
        total_batches = (len(images) + args.batch_size - 1) // args.batch_size
        log(f"每批 {args.batch_size} 张，共 {total_batches} 批。")
        for batch_no, batch in chunked(images, args.batch_size):
            start_index = (batch_no - 1) * args.batch_size + 1
            end_index = start_index + len(batch) - 1
            names = ", ".join(path.name for path in batch)
            log(f"[{batch_no}/{total_batches}] 第 {start_index}-{end_index} 页：{names}")
        return 0

    if args.merge_only:
        merge_chunks(chunks_dir, final_path)
        log(f"已合并：{final_path}")
        return 0

    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("ARK_API_KEY")
    if not api_key:
        print("缺少 API Key。请在 .env 中设置 OPENAI_API_KEY 或 ARK_API_KEY。", file=sys.stderr)
        return 1

    try:
        from openai import OpenAI
    except ImportError:
        print("缺少 openai SDK。请先执行：pip install -r requirements.txt", file=sys.stderr)
        return 1

    client = OpenAI(base_url=args.base_url, api_key=api_key)

    total_batches = (len(images) + args.batch_size - 1) // args.batch_size
    for batch_no, batch in chunked(images, args.batch_size):
        start_index = (batch_no - 1) * args.batch_size + 1
        end_index = start_index + len(batch) - 1
        first_num = page_number(batch[0], start_index)
        last_num = page_number(batch[-1], end_index)
        chunk_path = chunks_dir / f"batch_{batch_no:03d}_pages_{first_num}-{last_num}.md"

        if chunk_path.exists() and not args.force:
            log(f"[{batch_no}/{total_batches}] 跳过已存在：{chunk_path.name}")
            continue

        names = ", ".join(path.name for path in batch)
        log(f"[{batch_no}/{total_batches}] OCR 第 {start_index}-{end_index} 页：{names}")
        text = call_ocr(
            client,
            args.model,
            batch,
            start_index,
            args.max_retries,
            args.timeout,
            args.max_tokens,
        )
        chunk_path.write_text(text.strip() + "\n", encoding="utf-8")
        log(f"已保存：{chunk_path.name}")

        merge_chunks(chunks_dir, final_path)
        log(f"已更新合并文件：{final_path}")

    merge_chunks(chunks_dir, final_path)
    log(f"全部完成：{final_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
