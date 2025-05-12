from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from typing import List
import json
import time
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pathlib import Path

app = FastAPI()

class Message(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[Message]
    stream: bool = False


audios = ["hello","intro","transfer"]

counter = {}
current_message = 0
@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()
    chat_request = ChatCompletionRequest(**body)
    # Simulate classification by echoing user input as "predicted class"
    user_message = next((m['content'] for m in reversed(body['messages']) if m['role'] == 'user'), "")
    try:
        parts = user_message.split(";")
        user_text = parts[0]
        room_id = parts[1] if len(parts) > 1 else ''
    except Exception:
        user_text = ''
        room_id = ''
        current_message = 1
    else:
        if len(room_id) > 1:
            current_message = counter.get(room_id, 1)
            counter[room_id] = current_message + 1
        else:
            current_message = 1
    
    # print('Counter',counter)
    current_message = counter.get(room_id,1)
    print(parts)
    model = chat_request.model
    
    if current_message <= 0:
        predicted_class = "hello"  # Replace with actual classification logic
    elif current_message == 2:
        predicted_class = "intro"
    elif current_message == 3:
        predicted_class = "transfer"
    else:
        print('Falling to Else')
        predicted_class = "hello"

    # predicted_class = predicted_class+';ali'
    # STREAMING RESPONSE
    if chat_request.stream:
        async def event_generator():
            chunk = {
                "id": "chatcmpl-dummy",
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": model,
                "choices": [
                    {
                        "delta": {
                            "role": "assistant",
                            "content": predicted_class
                        },
                        "index": 0,
                        "finish_reason": None
                    }
                ]
            }
            yield f"data: {json.dumps(chunk)}\n\n"
            await asyncio.sleep(0.1)  # Optional: simulate delay
            yield "data: [DONE]\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    # NON-STREAMING RESPONSE
    return JSONResponse({
        "id": "chatcmpl-dummy",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": predicted_class
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": 5,
            "completion_tokens": 1,
            "total_tokens": 6
        }
    })


AUDIO_DIR = Path(__file__).with_name("audio")   #   ./audio/test.wav …

CHUNK_SIZE = 4096


def file_byte_iter(path: Path, chunk_size: int = CHUNK_SIZE):
    """Yield raw file bytes chunk‑by‑chunk."""
    with path.open("rb") as f:
        while True:
            data = f.read(chunk_size)
            if not data:
                break
            yield data


@app.get("/tts")
async def tts(file_name: str):
    """
    GET /tts?file_name=test.wav   →  streams audio/wav
    """

    safe_name = Path(file_name).name           # "folder/../foo" → "foo"
    if not safe_name.lower().endswith(".wav"):
        safe_name += ".wav"

    wav_path = AUDIO_DIR / safe_name

    if not wav_path.is_file():
        raise HTTPException(404, f"{safe_name} not found")

    return StreamingResponse(
        file_byte_iter(wav_path),
        media_type="audio/wav",
        headers={"Content-Disposition": f'inline; filename="{safe_name}"'},
    )


if __name__ == "__main__":
    import uvicorn
    AUDIO_DIR.mkdir(exist_ok=True)
    uvicorn.run("server:app", host="0.0.0.0", port=4001, reload=False)
