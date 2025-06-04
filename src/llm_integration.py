# llm_integration.py
import base64
import os
from typing import List, Dict
from config import OPENAI_API_KEY, MODEL_NAME

from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate

# Instantiate a single ChatOpenAI client (reused across calls)
chat_client = ChatOpenAI(
    model_name=MODEL_NAME,     # e.g. "gpt-4o"
    openai_api_key=OPENAI_API_KEY,
    temperature=0
)

# Build a PromptTemplate for summarization
_summary_template = """You are a mining site expert. Based on the individual category analyses below, produce a final conclusion that highlights:
- Key operational issues (e.g., pit geometry, haul road condition)
- Geotechnical concerns (e.g., slope stability, bench integrity)
- Environmental observations (e.g., water management, tailings containment)
- Safety hazards (e.g., loose debris, unauthorized personnel)

Provide your answer as concise bullet points, grouped by category, followed by an overall recommendation.
---

{combined_analyses}
"""
_summary_prompt = PromptTemplate(
    input_variables=["combined_analyses"],
    template=_summary_template
)

# Compose a RunnableSequence instead of using LLMChain
_summary_chain = _summary_prompt | chat_client


def summarize_with_chain(analysis_results: Dict[str, str]) -> str:
    """
    Combine all individual frame analyses (values of analysis_results)
    and send to ChatOpenAI for a final summary.
    """
    combined = "\n".join(analysis_results.values())
    # .invoke(...) runs the prompt → LLM sequence under the hood
    return _summary_chain.invoke({"combined_analyses": combined})


def _encode_image(image_path: str) -> str:
    """Read and base64-encode an image file."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _is_relevant(image_path: str, context: str) -> bool:
    """
    Send a quick yes/no prompt to check if the frame shows a mine site.
    Returns True if relevant, False otherwise.
    """
    img_b64 = _encode_image(image_path)
    resp = chat_client.generate(
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a mining-site relevance checker. "
                    "Answer strictly 'yes' or 'no'."
                )
            },
            {
                "role": "user",
                "content": f"Context: {context}. Is this image of an active open-pit mine site? "
                           "Answer only 'yes' or 'no'.",
                "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}
            }
        ]
    )
    answer = resp.generations[0][0].message.content.strip().lower()
    return answer.startswith("yes")


def analyze_frame(image_path: str, context: str) -> Dict[str, str]:
    """
    For a single frame:
      1. Check relevance. If 'no', return {'relevant': 'false'}.
      2. Otherwise, loop through categories and collect each prompt’s output.
    """
    results: Dict[str, str] = {}
    if not _is_relevant(image_path, context):
        return {"relevant": "false"}

    categories = {
        "operational": (
            "Evaluate pit geometry and benches (height, width, slope angles), "
            "haul road condition (surface, gradient), and visible loading/hauling activity."
        ),
        "geotechnical": (
            "Identify any slope stability indicators (cracks, tension zones), "
            "bench integrity issues (undercutting, loose rock), and evidence of rockfall or debris."
        ),
        "environmental": (
            "Assess water management (pools, drainage), "
            "tailings or waste stockpile condition, and any signs of erosion or sediment runoff."
        ),
        "safety": (
            "Spot safety hazards (e.g., loose rocks on benches, equipment too close to edges, "
            "unauthorized personnel), and note missing signage or barriers."
        )
    }

    img_b64 = _encode_image(image_path)
    for key, prompt_text in categories.items():
        resp = chat_client.generate(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a mining site analysis assistant. Provide observations "
                        "in bullet-point format for each category, being as concise as possible."
                    )
                },
                {
                    "role": "user",
                    "content": f"Context: {context}. {prompt_text}",
                    "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}
                }
            ]
        )
        # Each `resp.generations[0][0].message.content` should already be bullet points
        results[key] = resp.generations[0][0].message.content.strip()

    results["relevant"] = "true"
    return results


def analyze_frames(frame_paths: List[str], context: str) -> Dict[str, Dict[str, str]]:
    """
    Loop through all extracted frame paths:
      - Call analyze_frame() on each path.
      - Aggregate results in a dict: {frame_path: {...results...}}
    """
    all_results: Dict[str, Dict[str, str]] = {}
    for path in frame_paths:
        all_results[path] = analyze_frame(path, context)
    return all_results
