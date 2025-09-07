# Please install OpenAI SDK first: `pip3 install openai`
import json
from openai import OpenAI


system_prompt = """
The user will provide some exam text. Please parse the "question" and "answer" and output them in JSON format. 

EXAMPLE INPUT: 
Which is the highest mountain in the world? Mount Everest.

EXAMPLE JSON OUTPUT:
{
    "question": "Which is the highest mountain in the world?",
    "answer": "Mount Everest"
}
"""


client = OpenAI(api_key="sk-bb493c6f434043d68ccb2a2c686cc5a1", base_url="https://api.deepseek.com")
response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "中国的首都是?"},
    ],
    response_format={'type': 'json_object'}
)

print(json.loads(response.choices[0].message.content))


# print(response.choices[0].message.content)
# 按 json 格式输出
#print(json.dumps(response.model_dump(), indent=2))