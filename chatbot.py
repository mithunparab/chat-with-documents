from dotenv import load_dotenv
import os
load_dotenv()

os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY")

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage
model= init_chat_model("llama-3.1-8b-instant", model_provider="groq")

message = [
    SystemMessage(content="You are a helpful assistant."),
    HumanMessage(content="What is the capital of France?"),]

response=model.invoke(message)
print(response.content)