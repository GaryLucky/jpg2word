# jpg2word

把桌面目录中的 JPG 手写谈话记录按文件名编号排序，分批调用视觉模型识别，并合并成一本 Markdown。

## 使用方法

在 PowerShell 中执行：

```powershell
cd C:\Users\Gary\Desktop\jpg2word
pip install -r requirements.txt
python .\jpg_to_md.py
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
C:\Users\Gary\Desktop\jpg2word\output\final_book.md
```

## 断点续跑

每 5 页会保存一个分块文件：

```text
C:\Users\Gary\Desktop\jpg2word\output\chunks
```

如果中途失败，重新运行同一条命令即可，脚本会跳过已经完成的分块。

## 常用命令

只合并已有分块，不调用模型：

```powershell
python .\jpg_to_md.py --merge-only
```

重新生成所有分块：

```powershell
python .\jpg_to_md.py --force
```

正式调用 API 前检查排序和分批：

```powershell
python .\jpg_to_md.py --dry-run
```

调整每批页数：

```powershell
python .\jpg_to_md.py --batch-size 3
```

如果某批文字特别多，可以提高每批输出上限：

```powershell
python .\jpg_to_md.py --max-tokens 12000
```

只处理前 15 页做测试：

```powershell
python .\jpg_to_md.py --limit 15 --output-dir .\output_test_15
```
