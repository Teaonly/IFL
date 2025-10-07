# IFL – 命令行编码助手

本地 CLI + LLM，半自动读、改、写文件，每一步可确认。

## 安装

```bash
git clone https://github.com/teaonly/IFL.git && cd IFL
python -m venv .venv && source .venv/bin/activate
pip install -e .
```

## 使用

```bash
export SF_API_KEY=xxx               # SiliconFlow
# 或
export BIGMODEL_API_KEY=xxx         # GLM

ifl -t "任务描述" -i 文件1 -i 文件2   # 非交互
ifl                                  # 交互模式
```

## 参数

- `-t` 任务描述（省略则交互输入）
- `-i` 预读文件，可多次
- `-m` 指定模型提供商 SiFlow/GLM
- `-y` 默认全部确认

## 配置

`IFL/config.yaml` 可调模型、轮数、提示词等。

## 安全

写盘前询问；建议在 Git 仓库内使用。

MIT