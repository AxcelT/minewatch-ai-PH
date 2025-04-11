# Module for interfacing with your GPT API
from openai import OpenAI
from config import OPENAI_API_KEY
import base64

# Set your GPT API key.
client = OpenAI(api_key=OPENAI_API_KEY)

def analyze_image(image_path: str, context: str) -> str:
    """
    Sends an image file path and context to the GPT API for analysis.
    Returns the API's response as a string.
    """
    try:
        # Read and encode the image to base64
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")
        
        # Prepare the message with text and image
        response = client.chat.completions.create(
            model="gpt-4o",  # gpt-4o supports image inputs
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a highly experienced mining site analysis assistant. "
                        "Evaluate images for features such as tailings, water discoloration, "
                        "erosion, and other environmental indicators."
                    )
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"Site context: {context}. Provide environmental and mining-related observations."},
                        {"type": "image_url", "image_url": {
                            "url": f"data:image/jpeg;base64,{image_data}"
                        }},
                    ]
                }
            ],
            max_tokens=500,
        )
        
        return response.choices[0].message.content
    except Exception as e:
        return f"Error during API call: {e}"

# To test this module independently, you can uncomment the section below.
if __name__ == "__main__":
    test_result = analyze_image("data/frames/frame_370.jpg", "Site type: open pit; Mineral: Gold")
    print("Analysis:", test_result)