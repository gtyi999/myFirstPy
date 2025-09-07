import json
import requests
from openai import OpenAI


def get_weather(loc):
    open_weather_key = '6685131a3111bcf962e07bdb7a8d8f8e'
    # Step 1.构建请求
    url = "https://api.openweathermap.org/data/2.5/weather"
    # Step 2.设置查询参数
    params = {
        "q": loc,  # 查询城市
        "appid": open_weather_key,  # 输入API key
        "units": "metric",  # 使用摄氏度而不是华氏度
        "lang": "zh_cn"  # 输出语言为简体中文
    }

    # Step 3.发送GET请求
    response = requests.get(url, params=params)

    # Step 4.解析响应
    data = response.json()
    return json.dumps(data)


get_weather_function = {
    "type": "function",
    "function": {
        'name': 'get_weather',
        'description': '查询即时天气函数，根据输入的城市名称，查询对应城市的实时天气',
        'parameters': {
            'type': 'object',
            'properties': {
                'loc': {
                    'description': "城市名称，注意，中国的城市需要用对应城市的英文名称代替，例如如果需要查询北京市天气，则loc参数需要输入'Beijing'",
                    'type': 'string'
                }
            },
            'required': ['loc']
        }
    }
}

client = OpenAI(api_key="sk-bb493c6f434043d68ccb2a2c686cc5a1", base_url="https://api.deepseek.com")

tools = [get_weather_function]

messages = [
    {"role": "user", "content": "请帮我查询深圳地区今日天气情况"}
]

response = client.chat.completions.create(
    model="deepseek-chat",
    messages=messages,
    tools=tools,
    tool_choice="auto"
)

print(response.choices[0].message)

# 检查是否需要调用函数
if response.choices[0].message.tool_calls:
    # 添加助手的消息到对话历史
    messages.append(response.choices[0].message)

    # 处理每个函数调用
    for tool_call in response.choices[0].message.tool_calls:
        function_name = tool_call.function.name
        print(f"调用函数: {function_name}")
        function_args = json.loads(tool_call.function.arguments)
        print(f"函数参数: {function_args}")

        # 调用对应的函数
        if function_name == "get_weather":
            function_result = get_weather(function_args["loc"])

            # 添加函数调用结果到对话历史
            messages.append({
                "tool_call_id": tool_call.id,
                "role": "tool",
                "name": function_name,
                "content": function_result
            })

    # 再次调用 API 获取最终回复
    final_response = client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        tools=tools
    )

    print(final_response.choices[0].message.content)
else:
    # 如果没有函数调用，直接输出内容
    print("No function call needed.")
    print(response.choices[0].message.content)
