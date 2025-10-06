import os
import sys
import json
import uuid
import signal

from abc import ABC
import yaml
import argparse
from dotenv import load_dotenv

from IFL.provider.modules_factory import create_provider
from IFL.utils import ( apply_patch, readfile_with_linenumber, content_from_input,
                           print_line, framed_print,
                           confirm_from_input, display_search_replace )

class IFL(ABC):
    def __init__(self, config):
        self.config = config
        self.current_round = 0
        self.max_rounds = config.get("MaxRounds", 10)
        self.tools = config["AllTools"]
        self.llm = create_provider(config)

    ## 钳工操作，意味着精细、半自动操作
    def fitter(self, task, inputs):
        ## 初始消息队列
        allMessages = [
            {
                'role': "system",
                'content': self.config["SystemPrompt"]
            },
            {
                'role': "user",
                'content': task,
            }
        ]

        ## 自动加载输入文件内容
        for infile in inputs:
            if not os.path.exists(infile):
                raise Exception(f"Cannot open file: {infile}")

            argument = {
                "file_name" : infile
            }
            callid = str(uuid.uuid4())[:6]
            fcall = {
                "type": "function",
                "id":  callid,
                "function": {
                    "name": "ReadFile",
                    "arguments": json.dumps(argument)
                }
            }
            ## 模拟一次 function call 的 assistant 的消息
            allMessages.append({
                'role': "assistant",
                'content': None,
                'tool_calls': [fcall]
            })

            ## 模拟 function call 的结果
            file_content = readfile_with_linenumber(infile, True)
            call_result = {
                'role' : 'tool',
                'tool_call_id': callid,
                'content': file_content
            }
            allMessages.append(call_result)

        ## 消息已经准备完成
        self.chat_loop(allMessages)


    def chat_loop(self, allMessages):
        self.current_round += 1
        print_line(f"Calling LLM (round {self.current_round})")

        if self.current_round > self.max_rounds:
            print(f"Maximum rounds {self.max_rounds} reached, exiting")
            sys.exit(0)

        thinking, talking, fcall = self.llm.response(allMessages, self.tools)

        new_message = {
            'role': "assistant",
            'content': talking,
            'reasoning_content': thinking,
            'tool_calls': [fcall] if fcall is not None else None
        }

        ## 显示LLM响应消息
        if thinking is not None and thinking.strip() != "":
            framed_print("思考", thinking, "info")

        if talking is not None and talking.strip() != "":
            framed_print("回答", talking, "info")

        ## 如果没有工具调用
        if fcall is None:
            confirm = confirm_from_input(f"Model did not invoke tool call, exit? (y/n)", False)
            if confirm:
                sys.exit(0)
                return
            else:
                response = content_from_input("Continue input: ")
                if response.strip() == "":
                    print("Input cannot be empty, exiting")
                    sys.exit(0)
                    return

                allMessages.append(new_message)
                allMessages.append({
                    'role': 'user',
                    'content': response
                })
                return self.chat_loop(allMessages)

        ## 修改文件
        if fcall["function"]["name"] == "ModifyFile":
            return self.handle_modify_file(fcall, new_message, allMessages)

        ## 输出文件
        if fcall["function"]["name"] == "WriteFile":
            return self.handle_write_file(fcall, new_message, allMessages)

        ## 读取文件
        if fcall["function"]["name"] == "ReadFile":
            return self.handle_read_file(fcall, new_message, allMessages)

    def handle_modify_file(self, fcall, new_message, allMessages):
        try:
            callid = fcall["id"]
            arguments = fcall["function"]["arguments"]
            arguments = json.loads(arguments)
            blocks = arguments["modify_blocks"]
            file_name = arguments["file_name"]

        except Exception as e:
            framed_print("ModifyFile 解析出错!", f'{e}\nRetrying...', "warning")
            response = f"parse tool error : {str(e)}"
            call_result = {
                'role' : 'tool',
                'tool_call_id': callid,
                'content': response
            }
            allMessages.append(new_message)
            allMessages.append(call_result)
            return self.chat_loop(allMessages)

        framed_print("调用 Tool (ModifyFile)", display_search_replace(blocks), "success")

        confirm = confirm_from_input(f"Confirm modification of {file_name}? (y/n)")
        if confirm == True:
            ## 根据获得 path/diff 字符串，修改目标文件
            success, msg = apply_patch(file_name, blocks)
            if success :
                response = self.config["AcceptTemplate"]
            else:
                response = self.config["ChangeFailedTemplate"]
                response = response.replace("{__USER_RESPOSNE__}", msg)
                framed_print("ModifyFile 执行出错!", f'{msg}', "warning")

            call_result = {
                'role' : 'tool',
                'tool_call_id': callid,
                'content': response
            }
            allMessages.append(new_message)
            allMessages.append(call_result)
            return self.chat_loop(allMessages)

        ## 用户输入反馈，继续下一轮次调用
        response = content_from_input("Enter feedback: ")
        response = self.config["RefuseTemplate"].replace("{__USER_RESPOSNE__}", response)
        call_result = {
            'role' : 'tool',
            'tool_call_id': callid,
            'content': response
        }
        allMessages.append(new_message)
        allMessages.append(call_result)
        return self.chat_loop(allMessages)

    def handle_write_file(self, fcall, new_message, allMessages):
        try:
            callid = fcall["id"]
            arguments = fcall["function"]["arguments"]
            arguments = json.loads(arguments)
            file_content = arguments["file_content"]
            file_name = arguments['file_name']

        except Exception as e:
            framed_print("Writefile 解析出错!", f'{e}\nRetrying...', "warning")
            response = f"Parse tool call error: {str(e)}"
            call_result = {
                'role' : 'tool',
                'tool_call_id': callid,
                'content': response
            }
            allMessages.append(new_message)
            allMessages.append(call_result)
            return self.chat_loop(allMessages)

        framed_print("Tool (WriteFile)", file_content, "success")

        confirm = confirm_from_input(f"Confirm writing file {file_name}? (y/n)")
        if confirm == True:
            with open(file_name, 'w', encoding='utf-8') as f:
                f.write(file_content)
            response = self.config["AcceptTemplate"]
            call_result = {
                'role' : 'tool',
                'tool_call_id': callid,
                'content': response
            }
            allMessages.append(new_message)
            allMessages.append(call_result)
            return self.chat_loop(allMessages)

        ## 用户输入反馈，继续下一轮次调用
        response = content_from_input("Enter feedback: ")
        response = self.config["RefuseTemplate"].replace("{__USER_RESPOSNE__}", response)
        call_result = {
            'role' : 'tool',
            'tool_call_id': callid,
            'content': response
        }
        allMessages.append(new_message)
        allMessages.append(call_result)
        return self.chat_loop(allMessages)

    def handle_read_file(self, fcall, new_message, allMessages):
        try:
            callid = fcall["id"]
            arguments = fcall["function"]["arguments"]
            arguments = json.loads(arguments)
            file_name = arguments["file_name"]
        except Exception as e:
            framed_print("Readfile 解析出错!", f'{e}\nRetrying...', "warning")

            response = f"parse tool error : {str(e)}"
            call_result = {
                'role' : 'tool',
                'tool_call_id': callid,
                'content': response
            }
            allMessages.append(new_message)
            allMessages.append(call_result)
            return self.chat_loop(allMessages)

        framed_print("Tool (ReadFile)", f"文件名：{file_name}", "success")

        # 确保文件存在
        if not os.path.exists(file_name):
            print(f"Cannot open file: {file_name}, exiting")
            sys.exit(0)

        response = readfile_with_linenumber(file_name, True)
        call_result = {
            'role' : 'tool',
            'tool_call_id': callid,
            'content': response
        }
        allMessages.append(new_message)
        allMessages.append(call_result)
        return self.chat_loop(allMessages)

def get_args_from_command():
    ## 解析命令行参数
    parser = argparse.ArgumentParser(description="ifl(I'm Feeling Lucky) - Command line coding agent")
    parser.add_argument('-i', '--inputs', nargs='*', default=[], help='Input files')
    parser.add_argument('-t', '--task', type=str, help='Task description')
    parser.add_argument('-m', '--model', type=str, help='Model provider (SiFlow/GLM)')

    args = parser.parse_args()
    return args

def signal_handler(sig, frame):
    print("\nInterrupt signal received, program exiting...")
    sys.exit(0)

def main():
    signal.signal(signal.SIGINT, signal_handler)

    try:
        ## 加载环境变量
        load_dotenv()

        ## 加载配置文件
        code_path = os.path.dirname( os.path.abspath(__file__) )
        lore_path = os.path.join(code_path, "config.yaml")
        with open(lore_path, "r") as file:
            config = yaml.safe_load(file)

        args = get_args_from_command()

        ## 如果指定了模型供应商，更新配置
        if args.model:
            if args.model in config["Model"] :
                config["Model"]["selected"] = args.model
            else:
                print(f"Invalid model provider: {args.model}")
                print(f"Available providers: {[k for k in config['Model'].keys() if k != 'selected']}")
                sys.exit(1)

        agent = IFL(config)

        if args.task and args.task.strip() != "":
            task = args.task
        else:
            task = content_from_input("Enter your programing task: ")
            if task.strip() == "":
                print("Task description cannot be empty")
                sys.exit(0)

        agent.fitter(task, args.inputs)
    except KeyboardInterrupt:
        print("\nProgram interrupted by user, exiting...")
        sys.exit(0)
    except Exception as e:
        print(f"Program execution error: {e}")
        sys.exit(1)
