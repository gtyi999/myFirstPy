# Please install OpenAI SDK first: `pip3 install openai`
import json
from openai import OpenAI


client = OpenAI(api_key="sk-bb493c6f434043d68ccb2a2c686cc5a1", base_url="https://api.deepseek.com")

response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {"role": "system", "content": "You are a helpful assistant"},
        {"role": "user", "content": "假如你深圳市行政服务大厅的工作人员，请你详细说明一下如何注销个体工商户的营业执照，需要提供哪些资料？并说明如何在线办理注销手续？"},
        {"role": "user", "content": "如果我不想注销营业执照，我可以转让给别人吗？需要什么手续？"},
    ],
    stream=False
)

print(response.choices[0].message.content)
# 按 json 格式输出
print(json.dumps(response.model_dump(), indent=2))