import os
import yaml
from datetime import datetime
from dotenv import load_dotenv
from IFL.provider.modules_factory import create_provider


def main():
    load_dotenv()

    ## 加载配置文件
    code_path = os.path.dirname( os.path.abspath(__file__) )
    lore_path = os.path.join(code_path, "../IFL/config.yaml")
    with open(lore_path, "r") as file:
        config = yaml.safe_load(file)

    llm = create_provider(config)

    ## 定义工具
    tools = [
        {
            "type": "function",
            "function": {
                "name": "GetCurrentTime",
                "description": "获取当前的系统时间",
                "strict": True,
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
    ]

    ## 定义对话
    messages = [{
            "role": "system",
            "content": "You are a helpful assistant that helps people find information."
        }]

    ## 第一轮测试，直接问答
    print("== 第一轮测试，直接问答 ==")
    messages.append({
        "role": "user",
        "content": "简单介绍一下你自己"
    })
    thinking, answer, fcall = llm.response(messages, tools)
    print("思考: ", thinking)
    print("回答: ", answer)
    print("函数调用: ", fcall)
    print("\n\n")

    ## 第二轮测试，触发对话，stream模式
    print("== 第二轮测试，流式模式问答 ==")
    messages.append({
        "role": "user",
        "content": "Python是谁发明的？"
    })
    response = llm.response_stream(messages, tools)
    for thinking, answer, fcall in response:
        if thinking:
            print("思考: ", thinking)
        if answer:
            print("回答: ", answer)
        if fcall:
            print("函数调用: ", fcall)
    print("\n\n")

    print("== 第三轮测试，测试工具 ==")
    messages.append({
        "role": "user",
        "content": "现在几点了？"
    })
    thinking, answer, fcall = llm.response(messages, tools)
    print("思考: ", thinking)
    print("回答: ", answer)
    print("函数调用: ", fcall)
    print("\n\n")

    print("== 第四轮测试，验证工具 ==")
    if(fcall and fcall['function'].get("name") == "GetCurrentTime"):
        ## 将之前的 fcall 增加到 messages队列中。
        messages.append({
            "role": "assistant",
            "content": None,
            "tool_calls": [fcall]
        })
        messages.append({
            "role": "tool",
            "tool_call_id": fcall.get("id"),
            "content": f"现在是北京时间 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        })
        thinking, answer, fcall = llm.response(messages, tools)
        print("思考: ", thinking)
        print("回答: ", answer)
        print("函数调用: ", fcall)
        print("\n\n")

    else:
        print(f"没有触发工具调用，测试失败！{fcall}")

    print("== 测试结束 ==")

if __name__ == "__main__":
    main()
