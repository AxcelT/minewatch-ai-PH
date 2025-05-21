# services/llm_service.py
import openai
from langchain import OpenAI, LLMChain, PromptTemplate

# LangChain setup
_template = """You are a mining site expert.
Summarize the following analyses into a final conclusion:

{combined_analyses}
"""
_prompt = PromptTemplate(
    input_variables=["combined_analyses"],
    template=_template
)
_llm = OpenAI(model_name="gpt-4", temperature=0)
_chain = LLMChain(llm=_llm, prompt=_prompt)

def summarize_with_chain(analysis_results: dict[str, str]) -> str:
    combined = "\n".join(analysis_results.values())
    return _chain.run(combined_analyses=combined)

#OpenAI fallback
def summarize_with_openai(analysis_results: dict[str, str], max_tokens=300) -> str:
    combined = "\n".join(analysis_results.values())
    prompt = (
        "You are a mining site expert.\n"
        "Summarize the following analyses into a final conclusion:\n\n"
        + combined
    )
    resp = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a mining site expert."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=max_tokens
    )
    return resp.choices[0].message.content
