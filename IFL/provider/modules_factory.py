import importlib
import os
import sys

from IFL.provider.base import LLMProviderBase

"""工厂方法创建实例"""
def create_provider(config) -> LLMProviderBase:
    try:
        config = config["Model"]
        config = config[config["selected"]]
        
        module = importlib.import_module(f'{config["import"]}')
        return module.LLMProvider(config)

    except Exception as e:
        raise ValueError(f"错误：{str(e)}，LLM Provider创建失败!")
