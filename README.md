# 代码审查 Agent

## 简介
基于 LLM 的代码审查 Agent，可读取代码文件、执行 Python 代码、分析潜在 Bug 并给出改进建议。

## 功能
- 读取本地代码文件
- 执行 Python 代码
- 代码审查：Bug、严重程度、位置、原因、修复建议
- 上下文记忆
- 错误重试与最大循环限制

## 环境要求
- Python 3.10+
- DeepSeek / OpenAI 兼容 API Key

## 安装依赖
```bash
pip install -r requirements.txt
```

## 配置
复制 `.env.example` 为 `.env`，填入你的 API Key：

```env
OPENAI_API_KEY=你的key
OPENAI_BASE_URL=https://api.deepseek.com
MODEL=deepseek-chat
```

## 运行
```bash
python app.py
```

输入示例：
```text
请审查 example.py
```

退出：
```text
exit
```

## 项目结构
```text
code-review-agent/
├── app.py               # 主程序
├── example.py           # 测试代码
├── requirements.txt     # 依赖包
├── README.md            # 说明文档
└── .env.example         # 环境变量模板
```

