import argparse
import os
import time
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain.chat_models import init_chat_model
from langchain.prompts import ChatPromptTemplate
from dotenv import load_dotenv

load_dotenv()

os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")
os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY")

CHROMA_PATH = "chroma"

PROMPT_TEMPLATE = """
Please formulate your response strictly based on the information provided in the context below. 
Refrain from introducing any external data, assumptions, or extrapolations beyond the given text.
Also try to provide examples from the context to support your answer.

Context:
{context}
---

Answer the question based on the context above : {question}"""

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("query_text", type=str, help="The query text.")
    args = parser.parse_args()
    query_text = args.query_text
    
    print(f"Searching for: {query_text}")

    embedding_function = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    print("Loading Chroma database...")
    db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embedding_function)
    
    results = db.similarity_search_with_relevance_scores(query_text, k=7)
    
    print(f"Found {len(results)} results")
    if len(results) > 0:
        print(f"Top result score: {results[0][1]}")
        for i, (doc, score) in enumerate(results):
            print(f"Result {i+1}: Score {score:.3f}, Content preview: {doc.page_content[:100]}...")
    
    if len(results) == 0 or results[0][1] < 0.3:  # Lowered threshold for debugging
        print("Unable to find the relevant results.")
        return
    
    context = "\n\n---\n\n".join([doc.page_content for doc, _score in results])
    prompt_template = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
    prompt = prompt_template.format(context=context, question=query_text)
    print(f"Prompt: {prompt}")

    model = init_chat_model("meta-llama/llama-4-maverick-17b-128e-instruct", model_provider="groq")
    response_text = model.invoke(prompt)

    sources = [doc.metadata.get("source", None) for doc, _score in results]
    
    # Typewriter animation for response
    print("\nResponse: ", end="", flush=True)
    for char in response_text.content:
        print(char, end="", flush=True)
        time.sleep(0.03)  # Adjust speed here (0.03 seconds per character)
    
    print(f"\n\nSources: {sources}")


if __name__ == "__main__":
    main()