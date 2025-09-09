import asyncio
import time
import argparse
from statistics import mean
from openai import AsyncOpenAI, APIConnectionError
import tiktoken

# 获取tokenizer对象，目前只支持通义千问系列模型
# from dashscope import get_tokenizer
# tokenizer = get_tokenizer('qwen-turbo')

"""
pip install openai
pip install tiktoken

python -u simple-bench-to-api.py --url https://api.deepseek.com/v1 \
  --model deepseek-chat \
  --concurrencys 5,10 \
  --prompt "Introduce the history of China" \
  --max_tokens 100,1024,16384 \
  --api_key sk-bb493c6f434043d68ccb2a2c686cc5a1 \
  --duration_seconds 30
"""

KEY_of_concurrency = "并发数"

# 这行会联网下载编码文件。且不同模型可能依赖不同编码（如gpt-4o使用o200k_base），需确保下载的编码文件与目标模型匹配。
encoder = tiktoken.get_encoding("cl100k_base")


async def send_request(client, payload):
    start_time = time.time()
    first_token_received = False
    first_token_latency = None
    tokens_generated = 0

    try:
        stream = await client.chat.completions.create(**payload)
        async for chunk in stream:
            if not first_token_received:  # 首Token到达
                first_token_latency = time.time() - start_time
                first_token_received = True
            if chunk.choices[0].finish_reason:
                break
            # 累计生成token数
            content = chunk.choices[0].delta.content or ""
            tokens_generated += len(encoder.encode(content))
            # 简单用 split() 代替
            # tokens_generated += len(content.split())
        return {
            "success": True,
            "first_token_latency": first_token_latency,
            "total_latency": time.time() - start_time,
            "tokens_generated": tokens_generated
        }
    except Exception as e:
        print(f"Unexpected error: {e}")
        return {
            "success": False,
            "first_token_latency": None,
            "total_latency": None,
            "tokens_generated": 0
        }

# 基于线性插值计算百分位数


def calculate_percentile(latencies, percentile):
    if not latencies:
        return 0
    sorted_latencies = sorted(latencies)
    n = len(sorted_latencies)
    index = (n-1) * percentile/100
    lower = int(index)
    # upper = lower + 1 # 会报错，因为 upper 可能超出索引范围
    upper = min(lower + 1, n - 1)  # 限制 upper 的最大值为 n-1
    weight = index - lower
    return sorted_latencies[lower]*(1-weight) + sorted_latencies[upper]*weight


# 固定时长持续发送请求
async def run_load_test(api_config, payload, concurrency, total_requests, duration_seconds=60):
    start_time = time.time()
    semaphore = asyncio.Semaphore(concurrency)
    client = AsyncOpenAI(**api_config)
    total_requests = 0  # 动态计数总请求数
    results = []

    async def worker():
        nonlocal total_requests
        while time.time() - start_time < duration_seconds:
            async with semaphore:
                result = await send_request(client, payload)
                results.append(result)  # 将结果添加到列表中
                total_requests += 1  # 每次请求后递增计数器
                # return result
            # await asyncio.sleep(1/concurrency)  # 控制QPS

    tasks = [asyncio.create_task(worker()) for _ in range(concurrency)]
    await asyncio.gather(*tasks, return_exceptions=True)

    # 过滤掉 None 值
    results = [r for r in results if r is not None]

    # 统计逻辑保持不变
    success_count = sum(1 for r in results if r["success"])
    success_rate = success_count / total_requests * 100

    # 提取各延迟指标
    success_results = [r for r in results if r["success"]]

    # 首Token延迟列表（仅成功请求）
    first_latencies = [r["first_token_latency"]
                       for r in success_results if r["first_token_latency"] is not None]

    # 总延迟列表（仅成功请求）
    total_latencies = [r["total_latency"]
                       for r in success_results if r["total_latency"] is not None]

    # 平均延迟
    avg_latency = mean(total_latencies) if total_latencies else 0

    # 计算统计量
    success_count = len(success_results)
    success_rate = success_count / total_requests * 100

    total_tokens = sum(r['tokens_generated'] for r in success_results)
    throughputs = [r['tokens_generated']/(r['total_latency']-r['first_token_latency'])
                   for r in success_results if r['total_latency'] > 0]

    return {
        KEY_of_concurrency: concurrency,
        "总请求数": total_requests,
        "成功率": f"{success_rate:.2f}%",
        "平均延迟": f"{avg_latency:.4f}s",
        "最大延迟": f"{max(total_latencies):.4f}s" if total_latencies else "0s",
        "最小延迟": f"{min(total_latencies):.4f}s" if total_latencies else "0s",
        "P90延迟": f"{calculate_percentile(total_latencies, 90):.4f}s",
        "P95延迟": f"{calculate_percentile(total_latencies, 95):.4f}s",
        "P99延迟": f"{calculate_percentile(total_latencies, 99):.4f}s",
        "平均首字延迟": f"{mean(first_latencies):.4f}s" if first_latencies else "N/A",
        "总生成tokens数": total_tokens,
        "单并发最小吞吐量": f"{(min(throughputs)):.2f} tokens/s",
        "单并发最大吞吐量": f"{(max(throughputs)):.2f} tokens/s",
        "单并发平均吞吐量": f"{(mean(throughputs)):.2f} tokens/s",
        "总体吞吐量": f"{(total_tokens/(time.time() - start_time)):.2f} tokens/s"
    }


def main():
    parser = argparse.ArgumentParser(description="OpenAI服务压测工具(v1.x)")
    parser.add_argument("--url", required=True,
                        help="API基础地址，例如：http://localhost:8000/v1")
    parser.add_argument("--model", required=True, help="模型名称")
    parser.add_argument("--concurrencys", required=False, help="逗号分隔的并发数")
    parser.add_argument("--concurrency", required=False,
                        type=int, help="并发数，如果设置了，则忽略concurrencys参数")
    parser.add_argument("--requests", type=int, default=10)
    parser.add_argument("--prompt", default="Once upon a time")
    parser.add_argument("--max_tokens", default="10")
    parser.add_argument("--api_key", required=True)
    parser.add_argument("--duration_seconds", type=int, default=60)
    args = parser.parse_args()

    api_config = {
        "base_url": args.url,
        "api_key": args.api_key,
        "default_headers": {"User-Agent": "LoadTestClient/1.0"}
    }

    payload = {
        "model": args.model,
        "messages": [{"role": "user", "content": args.prompt}],
        "stream": True,
        "max_tokens": args.max_tokens,
        "temperature": 0.1
    }

    if args.concurrency:
        # 执行压测
        metrics = asyncio.run(run_load_test(
            api_config, payload, args.concurrency, args.requests, args.duration_seconds
        ))

        # 输出结果
        print(f"\n压测结果：")
        for k, v in metrics.items():
            print(f"{k:<15}: {v}")
        return

    max_token_list = list(map(int, args.max_tokens.split(",")))
    concurrencys = list(map(int, args.concurrencys.split(",")))
    for max_tokens in max_token_list:
        print(
            f"\n\n===== 开始 max_tokens={max_tokens} 的 {args.concurrencys} 并发压测 =====\n")
        payload["max_tokens"] = max_tokens
        run_with_max_token(api_config, payload, args.requests,
                           concurrencys, args.duration_seconds)


def run_with_max_token(api_config, payload, requests, concurrencys, duration_seconds):
    # 多并发压测
    all_metrics = []
    for concurrency in concurrencys:
        print(f"\n----- 开始{concurrency}个并发压测 -----")
        metrics = asyncio.run(run_load_test(
            api_config, payload, concurrency, requests, duration_seconds
        ))
        all_metrics.append(metrics)

        print(f"\n--- {concurrency}个并发压测结果：")
        for k, v in metrics.items():
            print(f"{k:<15}: {v}")

        time.sleep(5)

    print(f"\n\n----- max_tokens={payload['max_tokens']} 压测结果汇总 -----\n")
    # 构造 Markdown 横向表（每个 metrics 字典的 key 一致）
    # headers = list(all_metrics[0].keys())
    # header_line = "| " + " | ".join(headers) + " |"
    # separator_line = "| " + " | ".join(["---"] * len(headers)) + " |"
    # rows = []
    # for metrics in all_metrics:
    #     row = "| " + " | ".join(str(metrics[h]) for h in headers) + " |"
    #     rows.append(row)

    # markdown_table = "\n".join([header_line, separator_line] + rows)
    # print(markdown_table)

    # 构造 Markdown 纵向表，KEY_of_concurrency 作为列标题
    concurrency_headers = [str(metrics[KEY_of_concurrency])
                           for metrics in all_metrics]
    header_line = "| 指标 \\ 并发数 | " + \
        "个并发 | ".join(concurrency_headers) + "个并发 |"
    separator_line = "| --- | " + \
        " | ".join(["---"] * len(concurrency_headers)) + " |"

    # 获取所有指标 key（每个 metrics 字典的 keys 都一致）
    metric_keys = list(all_metrics[0].keys())
    rows = []
    for key in metric_keys:
        if key == KEY_of_concurrency:
            continue
        # 每行的第一个单元格是指标名称，后续单元格是每个并发下该指标的数值
        row_values = [str(metrics[key]) for metrics in all_metrics]
        row = "| " + key + " | " + " | ".join(row_values) + " |"
        rows.append(row)

    markdown_table = "\n".join([header_line, separator_line] + rows)
    print(markdown_table)


if __name__ == "__main__":
    main()
