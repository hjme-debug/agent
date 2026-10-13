import os
import json
import time
import subprocess
import sys
import tempfile

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL") or None,
)

MODEL = os.getenv("MODEL", "gpt-4o-mini")

SYSTEM_PROMPT = """
You are a code review agent. You can call tools to read files and execute Python code.

Workflow:
1. Understand user requirements.
2. If you need to view code, call read_file.
3. If you need to verify syntax or run results, call run_python.
4. Finally, output a Markdown report including: overall evaluation, issue list, severity, location, reason, and fix suggestions.
Do not make up code that you have not read.
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the content of a text file",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path"}
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_python",
            "description": "Execute Python code and return stdout/stderr",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Python code to execute"}
                },
                "required": ["code"],
            },
        },
    },
]


def read_file(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        if len(content) > 12000:
            return content[:12000] + "\n\n...content truncated..."
        return content
    except Exception as e:
        return f"Read file failed: {type(e).__name__}: {e}"


def run_python(code: str) -> str:
    with tempfile.NamedTemporaryFile(
        "w", suffix=".py", delete=False, encoding="utf-8"
    ) as f:
        f.write(code)
        tmp_path = f.name

    try:
        result = subprocess.run(
            [sys.executable, tmp_path],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return (
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}\n"
            f"returncode: {result.returncode}"
        )
    except Exception as e:
        return f"Execution failed: {type(e).__name__}: {e}"
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


def execute_tool(name: str, args: dict) -> str:
    try:
        if name == "read_file":
            return read_file(args.get("path", ""))
        if name == "run_python":
            return run_python(args.get("code", ""))
        return f"Unknown tool: {name}"
    except Exception as e:
        return f"Tool execution error: {type(e).__name__}: {e}"


def call_llm_with_retry(messages, retries=3):
    last_error = None
    for i in range(retries):
        try:
            return client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
                temperature=0.2,
            )
        except Exception as e:
            last_error = e
            print(f"LLM call failed, retry {i + 1}... Error: {e}")
            time.sleep(2 ** i)
    raise last_error


def chat_with_agent(user_input: str, history=None, max_steps=8):
    if history is None:
        history = []

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_input})

    for step in range(max_steps):
        print(f"\n[Agent thinking... step {step + 1}]")
        response = call_llm_with_retry(messages)
        msg = response.choices[0].message

        assistant_msg = {
            "role": "assistant",
            "content": msg.content or "",
        }

        if msg.tool_calls:
            assistant_msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in msg.tool_calls
            ]

        messages.append(assistant_msg)

        if msg.tool_calls:
            for tc in msg.tool_calls:
                name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}

                print(f"[Tool call] {name}({args})")
                result = execute_tool(name, args)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": str(result)[:8000],
                })
        else:
            answer = msg.content or "Agent did not return content."
            history.extend(messages[1:])
            return answer, history

    return "Max steps reached, agent did not finish.", history


def main():
    print("Code Review Agent. Type 'exit' to quit.")
    history = []

    while True:
        user_input = input("\nYou> ").strip()
        if user_input.lower() in {"exit", "quit"}:
            break
        if not user_input:
            continue

        answer, history = chat_with_agent(user_input, history)
        print("\nAgent>")
        print(answer)


if __name__ == "__main__":
    main()