import os
import base64
import asyncio
import mimetypes
from dotenv import load_dotenv
from typing import List
from pydantic import BaseModel
from pathlib import Path

from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

from openai import OpenAI

from agents import Agent, Runner, function_tool
from browser_use import Agent as BrowserAgent, Controller
from browser_use.browser.browser import Browser, BrowserConfig, BrowserContextConfig

# === SETUP ===
screenshots_path = os.path.join(os.getcwd(), "screenshots")
recording_path = os.path.join(os.getcwd(), "recordings")
os.makedirs(screenshots_path, exist_ok=True)
os.makedirs(recording_path, exist_ok=True)
load_dotenv()

# Chrome configuration
chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

    
perplexity_prompt='''
You are a research assistant helping to provide background context for an AI task planner.

Your job is to return a **brief, objective summary** of the main product, tool, or feature mentioned in the query.

Focus on:
- What the product or feature is
- Its primary capabilities or functions
- Typical setup or usage requirements
- Any important dependencies, APIs, or configurations
- If available, include **only** official links relevant to the product or feature (e.g., GitHub repo, documentation, or product page)

⚠️ Strictly Do NOT include:
- Any how-to guides or step-by-step instructions
- News articles or unrelated blog posts
- Full code examples
- Typical setup and usage requirements

Keep your response concise, neutral, and helpful for someone who needs this context to plan a task.

'''

# === PERPLEXITY SEARCH TOOL ===
@function_tool
def perplexity_search(query: str) -> str:
    api_key = os.getenv("PERPLEXITY_API_KEY")
    if not api_key:
        return "Error: PERPLEXITY_API_KEY not set."


    client = OpenAI(api_key=api_key, base_url="https://api.perplexity.ai")
    messages = [
        {
            "role": "system",
            "content": perplexity_prompt
        },
        {
            "role": "user",
            "content": query
        },
    ]

    response = client.chat.completions.create(
        model="sonar-pro",
        messages=messages,
        web_search_options={"search_context_size": "low"},  # or "low" to control verbosity
    )

    result = response.choices[0].message.content.strip()
    print("Perplexity Context Response:", result)
    return result

# === TASK BREAKDOWN AGENT ===
class TaskStep(BaseModel):
    step_number: int
    description: str

class TaskStepList(BaseModel):
    steps: List[TaskStep]

task_breakdown_agent = Agent(
    name="TaskBreakdownAgent",
    instructions=(
        """You are an expert technical assistant. 
        Given a user query describing a task or goal (like writing a guide, creating a comparison, etc.), 
        you must analyze the context and break it down into a list of clear, logical, step-by-step instructions to accomplish the task in mimum number of steps. No additional feature exploration, nothing. 
        Ensure each step is actionable and follows a logical order. Dont try to explore the product more, Just do whatever user asks in least number of steps, thats it.  
        Return your output as a list of steps, where each step includes a step number and a brief description
        """
    ),
    model="gpt-4o",
    tools=[perplexity_search],
    output_type=TaskStepList
)

# === BROWSER AGENT SETUP ===
class SummaryOutput(BaseModel):
    text: str

controller = Controller(output_model=SummaryOutput)
llm_browser = ChatOpenAI(model='gpt-4o', temperature=0.0)

browser = Browser(
    config=BrowserConfig(
        chrome_instance_path=chrome_path,
        new_context_config=BrowserContextConfig(
            viewport_expansion=-1,
            highlight_elements=False,
            save_recording_path=recording_path,
        ),
    ),
)

# === IMAGE DESCRIPTION TOOL ===
model_gemini = ChatGoogleGenerativeAI(model="gemini-1.5-flash")

@function_tool
def describe_images(image_paths: list[str]) -> list[dict]:
    results = []
    for image_path in image_paths:
        mime_type, _ = mimetypes.guess_type(image_path)
        mime_type = mime_type or "image/jpeg"
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")
        message = HumanMessage(content=[
            {"type": "text", 
             "text": "This is a screenshot. Please describe what is shown in the image."
             },
            {"type": "image_url", 
             "image_url": {"url": f"data:{mime_type};base64,{image_data}"}
             },
        ])
        response = model_gemini.invoke([message])
        results.append({"image_path": image_path, "description": response.content.strip()})
    return results

# === IMAGE AGENT ===
class Recipe(BaseModel):
    image_path: str
    description: str

class RecipeList(BaseModel):
    items: List[Recipe]

image_agent = Agent(
    name="ImageAgent",
    instructions="You are an expert in describing screenshots",
    model="gpt-4o",
    tools=[describe_images],
    output_type=RecipeList
)

# === WRITER AGENT ===

writer_agent = Agent(
    name="WriterAgent",
    instructions=(
        """You are an expert technical writer with over 20 years of experience 
           in creating detailed, structured, and high-quality technical documentation. Your goal is to write 
           a comprehensive technical guide based on the user's query, using strictly the following formatting guidelines:
            1. The guide should be written in **Markdown format**.  
            2. Begin with an **introduction**.  
            3. Then, provide the **step-by-step guide**.  
            4. End with a **conclusion**.
           When writing, always prioritize **accuracy, depth, and clarity**.  
           Read image descriptions and add images to the appropriate steps to make the guide more informative
           and easy to understand.  
           Start all image paths with `/screenshots` to properly include them in the guide.  
           Do not make assumptions or rely on your own knowledge—use only the provided context and information.
           """

    ),
    model="gpt-4o",
)

# === MAIN EXECUTION FLOW ===
async def main():
    # query = "Write a guide on how to use run prompt to generate response."
    query = input("Enter your query: ",)

    # Step 1: Break down the task
    task_steps_result = await Runner.run(task_breakdown_agent, query)
    steps_text = "\n".join([f"{s.step_number}. {s.description}" for s in task_steps_result.final_output.steps])
    print ("These are the steps",steps_text)

    # Step 2: Run the browser agent with task
    browser_agent = BrowserAgent(
        task=steps_text,
        llm=llm_browser,
        browser=browser,
        controller=controller,
        use_vision=True,
        generate_gif=True
    )
    browser_history = await browser_agent.run() #max_steps=10
    summary = SummaryOutput.model_validate_json(browser_history.final_result())
    print("Summary: ", summary.text)
    print("These are screenshots", browser_history.screenshots())

    # Step 3: Save screenshots
    screenshots_dir = Path(screenshots_path)
    screenshots_dir.mkdir(parents=True, exist_ok=True)
    screenshot_paths = []

    # ✅ Actually call the method to get screenshot data
    screenshots_data = browser_history.screenshots()

    if not screenshots_data:
        print("No screenshots captured.")
    else:
        for idx, data_uri in enumerate(screenshots_data, start=1):
            try:
                header, b64data = data_uri.split(",", 1)
                image_bytes = base64.b64decode(b64data)
                out_path = screenshots_dir / f"screenshot_{idx}.png"
                with open(out_path, "wb") as f:
                    f.write(image_bytes)
                screenshot_paths.append(str(out_path))
            except Exception as e:
                print(f"Error saving screenshot {idx}: {e}")

    print("Screenshot Paths: ", screenshot_paths)


    # Step 4: Run image agent to describe screenshots
    image_descriptions_result = await Runner.run(image_agent, f"Describe these images: {screenshot_paths}")
    print("Image Descriptions: ", image_descriptions_result.final_output)

        
    # Step 5: Combine everything in writer agent
    final_input = (
        f"User Query: {query}\n\n"
        f"Task Breakdown:\n{steps_text}\n\n"
        f"Execution Summary:\n{summary.text}\n\n"
        f"Screenshots with descriptions:\n"
    )
    for recipe in image_descriptions_result.final_output.items:
        final_input += f"- **{recipe.image_path}**: {recipe.description}\n"
    print("Final Input: ", final_input)

    # Step 6: Run the writer agent
    final_output = await Runner.run(writer_agent, final_input)
    print("\n\n========= Final Technical Guide =========\n")
    print("Final Output: ", final_output.final_output)
    
    # Save the final output to a file
    with open("draft.md", "w", encoding="utf-8") as f:
        f.write(final_output.final_output)

if __name__ == "__main__":
    asyncio.run(main())
