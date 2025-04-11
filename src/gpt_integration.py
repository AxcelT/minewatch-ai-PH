# Module for interfacing with your GPT API
import openai
from config import OPENAI_API_KEY

# Set your GPT API key.
openai.api_key = OPENAI_API_KEY

def analyze_image(image_path: str, context: str) -> str:
    """
    Sends an image file path and context to the GPT API for analysis.
    Returns the API's response as a string.
    """
    prompt = (
        f"Analyze the image found at '{image_path}' with the following context: {context}.\n"
        "Provide environmental and mining-related observations."
    )
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",  # Change the model if needed.
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a highly experienced mining site analysis assistant. "
                        "Evaluate images for features such as tailings, water discoloration, "
                        "erosion, and other environmental indicators."
                    )
                },
                {"role": "user", "content": prompt}
            ],
            max_tokens=150,
        )
        # Extract and return the analysis from the response.
        analysis = response["choices"][0]["message"]["content"]
        return analysis
    except Exception as e:
        return f"Error during API call: {e}"

# To test this module independently, you can uncomment the section below.
# if __name__ == "__main__":
#     test_result = analyze_image("data/frames/frame_0.jpg", "Site type: open pit; Mineral: Gold")
#     print("Analysis:", test_result)
