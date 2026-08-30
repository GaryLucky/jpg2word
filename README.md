# jpg2word

把桌面目录中的 JPG 手写谈话记录按文件名编号排序，分批调用视觉模型识别，先合并成 `final_book.md`，再导出为与源目录同名的 `.docx`。

## 使用方法

在 PowerShell 中执行：

```powershell
cd C:\Users\Gary\Desktop\jpg2word
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe .\main.py
```

在项目根目录的 `.env` 文件中配置 API Key：

```dotenv
OPENAI_API_KEY=你的_Ark_API_Key
```

也兼容 `ARK_API_KEY`；如果系统环境变量已设置，它会优先于 `.env` 中的值。

默认源目录：

```text
C:\Users\Gary\Desktop\9、访问何长工同志谈话记录87
```

默认输出：

```text
C:\Users\Gary\Desktop\jpg2word\jpg_files\final_book.md
C:\Users\Gary\Desktop\jpg2word\jpg_files\源目录名称.docx
```

## 断点续跑

每 5 页会保存一个分块文件：

```text
C:\Users\Gary\Desktop\jpg2word\output\chunks
```

如果中途失败，重新运行同一条命令即可，脚本会跳过已经完成的分块。

合并前脚本会检查每个分块里的 `---` 数量是否等于该批图片数量；不一致时会删除这个分块并自动重新 OCR 一次。重跑后仍不可用时，该批每页写入 `内容涉及敏感内容或字迹太难辨别`，并继续生成后续文件。

## 批量处理目录

`main.py` 会先检查 `--source-dir` 下是否存在包含 JPG/JPEG 图片的子目录：

- 如果有子目录：逐个处理每个子目录，并在每个子目录下生成 `output`
- 如果没有子目录：扫描当前 `--source-dir`，并在当前目录下生成 `output`

## 常用命令

只合并已有分块，不调用模型：

```powershell
.\.venv\Scripts\python.exe .\main.py --merge-only
```

重新生成所有分块：

```powershell
.\.venv\Scripts\python.exe .\main.py --force
```

正式调用 API 前检查排序和分批：

```powershell
.\.venv\Scripts\python.exe .\main.py --dry-run
```

调整每批页数：

```powershell
.\.venv\Scripts\python.exe .\main.py --batch-size 3
```

如果某批文字特别多，可以提高每批输出上限：

```powershell
.\.venv\Scripts\python.exe .\main.py --max-tokens 12000
```

只处理前 15 页做测试：

```powershell
.\.venv\Scripts\python.exe .\main.py --limit 15 --output-dir .\output_test_15
```

只把已有 Markdown 转成 Word，并手动指定 Word 文件名：

```powershell
.\.venv\Scripts\python.exe .\md2word.py --md .\jpg_files\final_book.md --docx .\jpg_files\final_book.docx
```
