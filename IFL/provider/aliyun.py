import json
import os
from httpx import Client

from IFL.provider.base import LLMProviderBase

class LLMProvider(LLMProviderBase):
    def __init__(self, config):
        self.model_name = config.get("model_name")
        self.base_url = config.get("base_url")
        api_key_env = config.get("api_key")
        self.api_key = os.getenv(api_key_env)
        if self.api_key == None:
            raise Exception("从环境变量中，无法获取 API_KEY")
        self.client = Client()

    def _build_request(self, dialogue, functions = None, stream = True):
        url = self.base_url + "/chat/completions"
        payload =  {
            "model": self.model_name,
            "messages" : dialogue,
            "stream": stream,
            "thinking": True,
            "temperature": 0.3,
            "response_format": {"type": "text"}
        };
        headers = {
            "Authorization": "Bearer " + self.api_key, # type: ignore
            "Content-Type": "application/json"
        };

        if functions is not None :
            payload["tools"] = functions;

        return url, payload, headers

    def response(self, dialogue, functions=None):
        try:
            url, payload, headers = self._build_request(dialogue, functions, False)
            response = self.client.post(url, headers=headers, json=payload, timeout=300)

            if response.status_code != 200:
                raise Exception( f"LLM调用异常：{response.json()}")

            result = response.json()
            thinking = None
            if "reasoning_content" in result["choices"][0]["message"]:
                thinking = result["choices"][0]["message"]["reasoning_content"]

            content = None
            if "content" in result["choices"][0]["message"]:
                content = result["choices"][0]["message"]["content"]

            fcall = None
            if "tool_calls" in result["choices"][0]["message"]:
                fcall = result["choices"][0]["message"]["tool_calls"][0]

            return thinking, content, fcall

        except Exception as e:
            raise Exception(f"LLM调用异常：{str(e)}")

    def response_stream(self, dialogue, functions=None):
        tool_call = {
            "type": "function",
            "function": {
                "name": None,
                "arguments":  ""
            }
        }
        try:
            url, payload, headers = self._build_request(dialogue, functions)
            with self.client.stream('POST', url , headers = headers, json = payload, timeout=300 ) as response:
                ## 检查 API 是否 200 OK
                if response.status_code != 200:
                    response.read()
                    raise Exception( f"LLM调用异常：{response.json()}")

                ## 解析 streaming 响应
                for line in response.iter_lines():
                    lj = line[6:];
                    if lj.startswith("{"):
                        lj = json.loads(lj)
                        thinking = None
                        if "reasoning_content" in lj["choices"][0]["delta"]:
                            thinking = lj["choices"][0]["delta"]["reasoning_content"]

                        token = None
                        if "content" in lj["choices"][0]["delta"]:
                            token = lj["choices"][0]["delta"]["content"]

                        if "tool_calls" in lj["choices"][0]["delta"]:
                            fcall = lj["choices"][0]["delta"]["tool_calls"]
                            fcall = fcall[0]
                            if "id" in fcall and fcall["id"] is not None:
                                tool_call["id"] = fcall["id"]
                            if "function" in fcall and fcall["function"] is not None:
                                fcall = fcall["function"]
                                if "name" in fcall and fcall["name"] is not None:
                                    tool_call["function"]["name"] = fcall["name"]
                                if "arguments" in fcall and fcall["arguments"] is not None:
                                    tool_call["function"]["arguments"] = tool_call["function"]["arguments"] + fcall["arguments"]

                        if (token is not None) or (thinking is not None):
                            yield thinking, token, None

            if tool_call["function"]["name"] is not None:
                yield None, None, tool_call
        except Exception as e:
            raise Exception(f"LLM调用异常：{str(e)}")

