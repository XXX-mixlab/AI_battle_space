import os
from openai import OpenAI

# 豆包大模型API调用示例
# 此文件展示了如何使用OpenAI兼容接口调用豆包大模型

# 初始化OpenAI客户端
# 您可以将API Key存储在环境变量中，或直接在代码中提供
client = OpenAI(
    # 豆包API的基础URL
    base_url="https://ark.cn-beijing.volces.com/api/v3",
    # API密钥
    api_key="61c3c616-8fb3-4596-9dc5-0f15f33d22f2",  # 建议使用环境变量: os.environ.get("ARK_API_KEY")
)

# 非流式请求示例
print("----- 标准请求示例 -----")
completion = client.chat.completions.create(
    # 豆包模型ID
    model="doubao-1-5-pro-32k-250115",
    messages=[
        {"role": "system", "content": "你是人工智能助手"},
        {"role": "user", "content": "常见的十字花科植物有哪些？"},
    ],
)
print(completion.choices[0].message.content)

# 流式请求示例
print("\n----- 流式请求示例 -----")
stream = client.chat.completions.create(
    # 豆包模型ID
    model="doubao-1-5-pro-32k-250115",
    messages=[
        {"role": "system", "content": "你是人工智能助手"},
        {"role": "user", "content": "常见的十字花科植物有哪些？"},
    ],
    # 启用流式响应
    stream=True,
)

# 处理流式响应
for chunk in stream:
    if not chunk.choices:
        continue
    print(chunk.choices[0].delta.content or "", end="")
print()

# 在AI鱿鱼游戏中的使用方法
print("\n在AI鱿鱼游戏中，豆包模型已配置在config.py中，并通过llm_client.py进行调用")
print("您可以通过修改config.py中的API_CONFIGS来调整豆包模型的配置")