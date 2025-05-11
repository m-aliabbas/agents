import asyncio
import openai

async def main():
    client = openai.AsyncClient(base_url="http://localhost:8000/v1", api_key="dummy")

    response = await client.chat.completions.create(
        model="llama3.1",
        messages=[{"role": "user", "content": "Hello test"}],
    )

    print(response)

if __name__ == "__main__":
    asyncio.run(main())
