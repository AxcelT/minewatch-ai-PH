# llm_integration.py
import base64
import os
from typing import List, Dict
from config import OPENAI_API_KEY, MODEL_NAME

from langchain_community.chat_models import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage

# Instantiate a single ChatOpenAI client (reused across calls)
chat_client = ChatOpenAI(
    model_name=MODEL_NAME,  # e.g. "gpt-4o"
    openai_api_key=OPENAI_API_KEY
)

def _encode_image(image_path: str) -> str:
    """Read and base64‐encode an image file."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def _is_relevant(image_path: str, context: str) -> bool:
    """
    Send a quick yes/no prompt to check if the frame shows a mine site.
    Returns True if relevant, False otherwise.
    """
    img_b64 = _encode_image(image_path)
    messages = [
        SystemMessage(
            content=(
                "You are a mining‐site relevance checker. "
                "Answer strictly 'yes' or 'no'."
            )
        ),
        HumanMessage(
            content=[
                {"type": "text", "text": f"Context: {context}. Is this image of a mining site?"},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
            ]
        ),
    ]
    resp = chat_client.generate(messages=messages)
    answer = resp.generations[0][0].message.content.strip().lower()
    return answer.startswith("yes")

def analyze_frame(image_path: str, context: str) -> Dict[str, str]:
    """
    For a single frame:
      1. Check relevance. If 'no', return {'relevant': 'false'}.
      2. Otherwise, loop through categories (water, safety, tailings, etc.)
         and collect each prompt’s output. Return a dict of results.
    """
    results: Dict[str, str] = {}
    if not _is_relevant(image_path, context):
        return {"relevant": "false"}

    # list of specific checks per frame
    categories = {
        "water": "Describe any water discoloration or pooling.",
        "safety": "Identify visible safety hazards (e.g., loose rocks, equipment).",
        "tailings": "Assess tailings condition and possible overflow risks.",
        # add more keys/prompts if needed
    }

    img_b64 = _encode_image(image_path)
    for key, prompt_text in categories.items():
        messages = [
            SystemMessage(
                content=(
                    "You are a mining site analysis assistant. "
                    "Provide concise observations for each category."
                )
            ),
            HumanMessage(
                content=[
                    {"type": "text", "text": f"Context: {context}. {prompt_text}"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
                ]
            ),
        ]
        resp = chat_client.generate(messages=messages)
        results[key] = resp.generations[0][0].message.content.strip()

    results["relevant"] = "true"
    return results

def analyze_frames(frame_paths: List[str], context: str) -> Dict[str, Dict[str, str]]:
    """
    Loop through all extracted frame paths:
      - Call analyze_frame() on each path.
      - Skip further prompts if not relevant.
      - Aggregate results in a dict: {frame_path: {...results...}}
    """
    all_results: Dict[str, Dict[str, str]] = {}
    for path in frame_paths:
        all_results[path] = analyze_frame(path, context)
    return all_results
