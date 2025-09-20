from abc import ABC, abstractmethod

class LLMProviderBase(ABC):
    @abstractmethod
    def response(self, dialogue, functions=None):
        pass

    @abstractmethod
    def response_stream(self, dialogue, functions=None):
        pass
