# AI 鱿鱼游戏

这是一个基于大型语言模型（LLM）的心理博弈游戏。多名 AI 玩家被困在地牢中，每个玩家都有自己的背景故事和秘密动机。玩家需要通过陈述、质询和投票来找出并淘汰其他玩家，最终只有两名玩家能够生存下来。

## 项目特点

*   **多 AI 对战**：支持多个不同的 LLM API 作为游戏玩家参与。
*   **角色扮演**：每个 AI 都有独特的背景故事，需要扮演角色并隐藏身份。
*   **动态交互**：包含陈述、质询、投票等多个游戏环节。
*   **可配置性**：可以通过 `config.py` 文件轻松配置 API 和模型。
*   **裁判模式**：可选的 AI 裁判角色，增加游戏趣味性。

## 安装

1.  **克隆仓库** (如果适用)

    ```bash
    git clone <repository_url>
    cd AI_battle_space
    ```

2.  **安装依赖**

    确保你已经安装了 Python 3.8 或更高版本。然后使用 pip 安装所需的库：

    ```bash
    pip install -r requirements.txt
    ```

## 配置

1.  **API 密钥和模型配置**

    打开 `config.py` 文件。
    你需要在此文件中配置每个 AI 玩家（以及可选的裁判）的 API 信息，包括：

    *   `base_url`: API 的基础 URL。
    *   `api_key`: 你的 API 密钥。
    *   `role_name`: AI 角色的名称（需要与 `backstory_list` 文件夹中的文件名对应）。
    *   `model`: 要使用的 LLM 模型名称。
    *   `is_judge` (可选): 如果此角色是裁判，设置为 `True`。

    **示例配置块：**

    ```python
    {
        "base_url": "YOUR_API_BASE_URL",
        "api_key": "YOUR_API_KEY",
        "role_name": "GPT", # 确保与 backstory_list/for_GPT.txt 对应
        "model": "gpt-4o"
    },
    ```

    **重要提示：** 直接在代码中存储 API 密钥存在安全风险。建议使用环境变量或其他更安全的方式来管理密钥。

2.  **角色背景故事**

    *   每个 AI 角色的背景故事存储在 `backstory_list` 文件夹中。
    *   文件名必须遵循 `for_角色名.txt` 的格式（例如 `for_GPT.txt`）。
    *   文件名中的 `角色名` 必须与 `config.py` 中配置的 `role_name` 严格对应（大小写敏感，但加载时会尝试进行一些智能匹配）。
    *   确保为 `config.py` 中定义的每个非裁判角色都创建了对应的背景故事文件。

## 如何运行

配置完成后，在项目根目录下运行主游戏脚本：

```bash
python ai_dungeon_game.py
```

游戏将在控制台中开始运行，并显示各个环节的输出。

### 调试模式

可以通过设置环境变量 `DEBUG_MODE=1` 来启用调试模式，这会在陈述环节显示角色的原始故事背景。

**Windows (PowerShell):**

```powershell
$env:DEBUG_MODE=1
python ai_dungeon_game.py
$env:DEBUG_MODE=0 # 运行后恢复
```

**Linux/macOS:**

```bash
export DEBUG_MODE=1
python ai_dungeon_game.py
export DEBUG_MODE=0 # 运行后恢复
```

## 项目结构

```
AI_battle_space/
├── __pycache__/         # Python 缓存文件
├── backstory_list/     # 存放角色背景故事的文件夹
│   ├── for_Claude.txt
│   ├── for_DeepSeek.txt
│   └── ...
├── output/             # 存放游戏日志的文件夹
│   ├── 2025-04-12/
│   │   └── game_log_...md
│   └── ...
├── ai_dungeon_game.py  # 游戏主逻辑和流程控制
├── ai_player.py        # AI 玩家类，负责与 LLM API 交互
├── config.py           # API 配置和游戏设置
├── requirements.txt    # 项目依赖
└── README.md           # 本文件
```

## 注意事项

*   API 请求可能会产生费用，请注意你的 API 使用情况。
*   `config.py` 中的 `API_REQUEST_INTERVAL` 和 `GPT_REQUEST_INTERVAL` 用于控制 API 请求频率，以避免速率限制。
*   游戏日志会保存在 `output` 文件夹下，按日期分类。