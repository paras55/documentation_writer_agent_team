# 🧠 AI-Powered Technical Documentation Automation

This project automates the generation of technical documentation using a multi-agent AI workflow. It simulates a complete research, execution, and writing pipeline based on user queries — ideal for guides, how-tos, and tutorials.

## 🚀 Features

- **Task Decomposition**: Breaks down a user query into logical steps using GPT-4o.
- **Automated Browser Execution**: Uses a headless Chrome browser to perform tasks and capture screenshots.
- **Image Analysis**: Describes screenshots using Gemini or GPT-4o.
- **Research Context**: Pulls background information using Perplexity API.
- **Technical Guide Writer**: Generates a polished, structured guide in Markdown format.

## 🛠️ Requirements

- Python 3.10+
- Chrome installed (adjust `chrome_path` if necessary)
- Environment Variables:
  - `OPENAI_API_KEY`
  - `PERPLEXITY_API_KEY`
  - `GOOGLE_API_KEY` (for Gemini)

## 📦 Installation

1. Clone the repo and install dependencies:

```bash
pip install -r requirements.txt
```

2. Create a `.env` file with your API keys:

```env
OPENAI_API_KEY=your_openai_key
PERPLEXITY_API_KEY=your_perplexity_key
GOOGLE_API_KEY=your_google_api_key
```

3. Make sure the Chrome path is correct (Mac default included in code).

## 🧪 How It Works

1. You enter a query describing a goal (e.g., "Generate a prompt response guide").
2. The system:
   - Breaks it into steps
   - Executes the task in a headless browser
   - Captures and analyzes screenshots
   - Summarizes execution and writes a Markdown guide

## 📂 Output

- Screenshots are saved to `/screenshots`
- A Markdown guide is saved as `draft.md`

## 🖥️ Running the Program

```bash
python main.py
```

Then enter your query when prompted.

## 📸 Screenshots & Recording

Optionally, you can modify the script to enable or disable GIF recording or change viewport behavior.

## ✨ Example Queries

- "Create a guide on exporting JSON from Postman"
- "Write a walkthrough on using GitHub Actions for CI"

---

Built with ❤️ using OpenAI, Google Gemini, and Perplexity AI.
