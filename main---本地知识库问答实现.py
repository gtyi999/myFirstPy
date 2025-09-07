# Please install OpenAI SDK first: `pip3 install openai`
import json
from openai import OpenAI


with open('哪吒2剧情.txt', 'r', encoding='utf-8') as f:
    chatCompletion_kg= f.read()

client = OpenAI(api_key="sk-bb493c6f434043d68ccb2a2c686cc5a1", base_url="https://api.deepseek.com")

def chat_with_model(messages):
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=messages
    )
    return response.choices[0].message.content

# 测试函数
def gpt_chat_with_model():
    # 初始问候
    messages = [
        {"role": "system", "content": chatCompletion_kg}, ##添加本地知识库
        {"role": "user", "content": "你好！"},
        {"role": "assistant", "content": "你好！我是一个AIGC智能助理，有什么问题我可以帮助你？"}
    ]
    print(chat_with_model(messages))
    # 进行对话
    while True:
        user_input = input("用户：")
        messages.append({"role": "user", "content": user_input})
        assistant_response = chat_with_model(messages)
        messages.append({"role": "assistant", "content": assistant_response})
        print("助理：" + assistant_response)
        # 判断是否结束对话
        if user_input.lower() in ["退出", "再见", "拜拜", "quit"]:
            print("助理：再见！")
            break

gpt_chat_with_model()