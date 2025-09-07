# Please install OpenAI SDK first: `pip3 install openai`
import json
from openai import OpenAI


Q1 = '小米有6个气球，她又买了3袋，每袋有10个气球，请问她现在总共有多少个气球？'
A1 = '现在小米总共有36个气球。'
Q2 = '小明总共有10个苹果，吃了3个苹果，然后又买了5个苹果，请问现在小明总共有多少个苹果？'
A2 = '现在小明总共有12个苹果。'


client = OpenAI(api_key="sk-bb493c6f434043d68ccb2a2c686cc5a1", base_url="https://api.deepseek.com")
response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {"role": "user", "content": Q1},
        {"role": "assistant", "content": A1},
        {"role": "user", "content": Q2}
    ]
)

print(response.choices[0].message.content)


# print(response.choices[0].message.content)
# 按 json 格式输出
#print(json.dumps(response.model_dump(), indent=2))