# jpg2word

`jpg2word` 用来把一批 JPG/JPEG 扫描图片按文件名编号排序，调用豆包视觉模型识别手写文字，先生成 Markdown，再合并导出 Word 文档。

适合处理一整本扫描谈话记录、回忆录、档案手稿等图片资料。

## 模型说明

项目通过火山引擎 Ark 的 OpenAI 兼容接口调用豆包视觉模型：

```text
https://ark.cn-beijing.volces.com/api/v3
```

当前脚本默认模型是：

```text
doubao-seed-2-1-pro-260628
```

如果你在 Ark 控制台开通的是 doubaospeed 或其他豆包视觉模型，请在运行时用 `--model` 指定你的模型名称：

```powershell
.\.venv\Scripts\python.exe .\main.py --model doubaospeed视觉模型名称
```

脚本默认使用 `--reasoning-effort minimal`，也就是让视觉大模型尽量不要深度思考，只做识别和转写。

## 安装准备

在 PowerShell 中进入项目目录：

```powershell
cd C:\Users\Gary\Desktop\jpg2word
```

创建虚拟环境并安装依赖：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

在项目根目录新建或编辑 `.env` 文件，写入你的 Ark API Key：

```dotenv
OPENAI_API_KEY=你的_Ark_API_Key
```

也可以写成：

```dotenv
ARK_API_KEY=你的_Ark_API_Key
```

不要把真实 API Key 发给别人，也不要提交到 Git。

## 最常用运行方式

处理一个图片目录：

```powershell
.\.venv\Scripts\python.exe .\main.py --source-dir "C:\Users\Gary\Desktop\jpg2word\jpg_files\某个扫描目录"
```

如果这个目录下面没有图片子目录，程序会直接扫描当前目录中的 JPG/JPEG 图片，并在当前目录下生成 `output`。

如果这个目录下面有多个包含 JPG/JPEG 图片的子目录，程序会自动逐个处理这些子目录，并在每个子目录下生成各自的 `output`。

## 输出结果

每个被处理的图片目录都会生成一个 `output` 文件夹，例如：

```text
图片目录
└─ output
   ├─ chunks
   │  ├─ batch_001_pages_001-003.md
   │  ├─ batch_002_pages_004-006.md
   │  └─ ...
   ├─ manifest.md
   ├─ final_book.md
   └─ 图片目录名.docx
```

文件含义：

- `chunks`：每批图片识别后的 Markdown 分块。
- `manifest.md`：图片顺序清单，记录第几页对应哪个图片文件名。
- `final_book.md`：所有分块合并后的整本文档。
- `图片目录名.docx`：最终 Word 文档，文件名和源图片目录名称相同。

Word 文档会按 Markdown 中的 `---` 分页。每一页的页脚会根据 `manifest.md` 写入对应的源图片文件名，方便回查原图。

## 整个项目运行流程

1. 准备图片  
   把 JPG/JPEG 图片放进一个目录，文件名中最好带有页码或编号，例如 `001.jpg`、`002.jpg`、`第10页.jpg`。程序会按文件名中的数字自然排序。

2. 配置 API Key  
   在 `.env` 里配置 `OPENAI_API_KEY` 或 `ARK_API_KEY`。

3. 运行 `main.py`  
   `main.py` 是总入口，负责判断目录结构、调用 OCR、合并 Markdown、导出 Word。

4. 分批识别图片  
   `jpg_to_md.py` 会每批读取若干张图片，把本地图片转成 base64 data URL 后发给豆包视觉模型。

5. 保存分块 Markdown  
   每一批都会保存为一个 `batch_*.md` 文件。每张图片识别内容后面必须有一个单独成行的 `---`。

6. 检查分隔符  
   程序会检查每个批次里的 `---` 数量是否等于本批图片数量。如果不一致，会删除这个批次并自动重新跑一次。

7. 失败占位  
   如果重试后仍然不可用，程序会给该批每一页写入：

   ```text
   内容涉及敏感内容或字迹太难辨别
   ---
   ```

   这样整本书仍然可以继续生成，不会卡死在某一批。

8. 合并整本 Markdown  
   所有批次合并成 `output\final_book.md`，页与页之间用 `---` 分隔。

9. 导出 Word  
   `md2word.py` 会把 `final_book.md` 转成 `.docx`，并根据源目录名称生成最终 Word 文件名。

## 程序流程

### `main.py`

总入口脚本，负责完整流水线。

主要流程：

1. 读取命令行参数。
2. 调用 `get_processing_directories()` 判断源目录下是否有包含图片的子目录。
3. 如果有图片子目录，就逐个子目录处理。
4. 如果没有图片子目录，就处理当前源目录。
5. 为每个处理目录创建 `output`。
6. 调用 `jpg_to_md.main()` 生成 Markdown。
7. 调用 `markdown_to_docx()` 导出 Word。

### `jpg_to_md.py`

OCR 和 Markdown 合并脚本。

主要流程：

1. 扫描源目录下所有 `.jpg` 和 `.jpeg` 文件。
2. 使用自然排序按文件名编号从小到大排列。
3. 写出 `manifest.md`。
4. 按 `--batch-size` 分批。
5. 每批图片转成 base64 data URL。
6. 调用豆包视觉模型识别。
7. 保存 `output\chunks\batch_*.md`。
8. 检查每批 `---` 数量。
9. 合并所有分块到 `output\final_book.md`。

### `md2word.py`

Markdown 转 Word 脚本。

主要流程：

1. 读取 `final_book.md`。
2. 按单独成行的 `---` 拆分页。
3. 读取 `manifest.md` 中的图片文件名。
4. 为 Word 每一页设置页脚，页脚内容就是对应图片名。
5. 写入正文、标题和简单表格。
6. 保存为 `源目录名.docx`。

## 常用命令

先检查图片排序和分批，不调用模型：

```powershell
.\.venv\Scripts\python.exe .\main.py --source-dir "图片目录" --dry-run
```

只测试前 15 页：

```powershell
.\.venv\Scripts\python.exe .\main.py --source-dir "图片目录" --limit 15
```

每批 3 页，适合手写内容比较密或模型容易漏分隔符时使用：

```powershell
.\.venv\Scripts\python.exe .\main.py --source-dir "图片目录" --batch-size 3
```

强制重新识别所有批次：

```powershell
.\.venv\Scripts\python.exe .\main.py --source-dir "图片目录" --force
```

只合并已有分块并导出 Word，不重新调用模型：

```powershell
.\.venv\Scripts\python.exe .\main.py --source-dir "图片目录" --merge-only
```

提高每批输出长度：

```powershell
.\.venv\Scripts\python.exe .\main.py --source-dir "图片目录" --max-tokens 12000
```

指定豆包视觉模型：

```powershell
.\.venv\Scripts\python.exe .\main.py --source-dir "图片目录" --model doubaospeed视觉模型名称
```

只把 Markdown 转成 Word：

```powershell
.\.venv\Scripts\python.exe .\md2word.py --md "图片目录\output\final_book.md" --docx "图片目录\output\图片目录名.docx" --manifest "图片目录\output\manifest.md"
```

## 参数说明

- `--source-dir`：图片源目录。
- `--output-dir`：输出目录。单目录处理时可指定；多子目录处理时固定使用每个子目录自己的 `output`。
- `--model`：豆包视觉模型名称。
- `--base-url`：Ark OpenAI 兼容接口地址。
- `--batch-size`：每批送入模型的图片数量。`main.py` 默认是 3。
- `--limit`：只处理前 N 张图片，测试时很有用。
- `--force`：忽略已有分块，全部重新识别。
- `--merge-only`：只合并已有分块并导出 Word。
- `--dry-run`：只打印排序和分批，不调用模型。
- `--timeout`：每次模型调用超时时间，单位秒。
- `--max-retries`：每批调用失败时的最大重试次数。
- `--max-tokens`：每批允许模型输出的最大 token 数。
- `--reasoning-effort`：推理深度，默认 `minimal`。
- `--docx`：手动指定 Word 输出路径。只适合单目录处理。

## 注意事项

- 本地 JPG 可以直接发送给模型，脚本会自动转成 base64 data URL，不需要你手动上传图片到公网 URL。
- 图片越清晰、文件名编号越规范，最终结果越稳定。
- 每批页数太多时，模型可能输出不完整；建议手写密集材料使用 `--batch-size 3`。
- 如果模型触发内容过滤或无法识别，程序会用“内容涉及敏感内容或字迹太难辨别”占位，方便后续人工补录。
- `final_book.md` 是中间成果，可以手动修改后再运行 `--merge-only` 或单独运行 `md2word.py` 重新生成 Word。
