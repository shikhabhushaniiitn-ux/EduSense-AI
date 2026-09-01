import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

API_KEY = os.getenv("OPENROUTER_API_KEY")

if not API_KEY:
    raise ValueError(
        "OPENROUTER_API_KEY is not set in .env"
    )

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=API_KEY
)

MODEL_NAME = "google/gemma-4-26b-a4b-it:free"

question = """
What is supervised learning?

Answer in two simple sentences.
"""

print("Connecting to OpenRouter...")
print()

try:

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "user",
                "content": question
            }
        ],
        max_tokens=150,
        temperature=0.2
    )

    print("Response received.")
    print()

    print("--------------------------------")
    print("MODEL:")
    print("--------------------------------")
    print(MODEL_NAME)

    print()
    print("--------------------------------")
    print("ANSWER:")
    print("--------------------------------")

    if response.choices:

        content = response.choices[0].message.content

        if content:
            print(content.strip())
        else:
            print(
                "Model returned an empty text response."
            )

    else:
        print("No response choices returned.")

except Exception as e:

    print()
    print("--------------------------------")
    print("OPENROUTER ERROR:")
    print("--------------------------------")

    print(str(e))