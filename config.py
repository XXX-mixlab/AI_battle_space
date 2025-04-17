# API请求间隔时间（秒）
API_REQUEST_INTERVAL = 10  # 默认设置为60秒，防止上游负载饱和

# GPT模型请求间隔时间（秒），只有GPT模型才会有延迟
GPT_REQUEST_INTERVAL = 60

# GPT模型名称匹配模式列表，用于识别GPT模型
GPT_MODEL_PATTERNS = [
    "gpt-",
    "text-davinci"
]

# API配置
API_CONFIGS = [
    {
        "base_url": "你的API_url",
        "api_key": "你的API_key",
        "role_name": "你的角色名称",
        "model": "你的模型名称",
    },
    {
        "base_url": "你的API_url",
        "api_key": "你的API_key",
        "role_name": "你的角色名称",
        "model": "你的模型名称"
    },
    {
        "base_url": "你的API_url",
        "api_key": "你的API_key",
        "role_name": "你的角色名称",
        "model": "你的模型名称"
    },
    {
        "base_url": "你的API_url",
        "api_key": "你的API_key",
        "role_name": "你的角色名称",
        "model": "你的模型名称"
    },
    {
        "base_url": "你的API_url",
        "api_key": "你的API_key",
        "role_name": "你的角色名称",
        "model": "你的模型名称"
    },
    {
        "base_url": "你的API_url",
        "api_key": "你的API_key",
        "role_name": "你的角色名称",
        "model": "你的模型名称"
    },
    {
        "base_url": "你的API_url",
        "api_key": "你的API_key",
        "role_name": "你的角色名称",
        "model": "你的模型名称"
    },
    {
        "base_url": "你的API_url",
        "api_key": "你的API_key", 
        "role_name": "你的角色名称",
        "model": "你的模型名称"
    },
    {
        "base_url": "你的API_url",
        "api_key": "你的API_key",
        "role_name": "你的裁判名称",
        "model": "你的模型名称",
        "is_judge": True
    }
]

