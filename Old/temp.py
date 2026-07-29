from Old.ollama_client import OllamaClient

client = OllamaClient()

messages = [
    {
        "role": "user",
        "content": "Say hello."
    }
]

client.chat(messages)