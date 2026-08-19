"""
AI-Based Schema Designer using Docker + Ollama


This script connects to the Ollama container running locally (via Docker),
uses the llama3 model to design database schemas based on user requirements,
and supports data management operations like insert/query generation.
"""

import requests
import json
import os
from datetime import datetime

# ── Configuration ──────────────────────────────────────────────────────────────
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL      = "llama3"
OUTPUT_DIR = "generated_schemas"

# ── System prompt that instructs the AI how to behave ─────────────────────────
SYSTEM_PROMPT = """You are an expert database architect and SQL specialist.
When a user describes their data or application requirements, you must:
1. Design a clean, normalized relational database schema
2. Provide SQL CREATE TABLE statements with appropriate data types, 
   primary keys, foreign keys, and constraints
3. Briefly explain each table and its purpose
4. Suggest sample INSERT statements to populate the tables
5. Suggest useful SELECT queries for data management

Always format SQL in clean code blocks. Be concise but complete.
If the user asks for modifications or additional queries, help them accordingly."""

# ── Helper: call Ollama API ────────────────────────────────────────────────────
def ask_ollama(conversation_history):
    """Send conversation history to Ollama and return the AI response."""
    payload = {
        "model": MODEL,
        "messages": conversation_history,
        "stream": False
    }
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=300)
        response.raise_for_status()
        data = response.json()
        return data["message"]["content"]
    except requests.exceptions.ConnectionError:
        return "ERROR: Cannot connect to Ollama. Make sure Docker is running and 'ollama' container is up."
    except requests.exceptions.Timeout:
        return "ERROR: Request timed out. The model may be loading — please try again."
    except Exception as e:
        return f"ERROR: {str(e)}"

# ── Helper: save schema to file ────────────────────────────────────────────────
def save_schema(content, requirement_summary):
    """Save the generated schema to a .sql file."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Clean the summary for use as a filename
    safe_name = "".join(c if c.isalnum() or c == "_" else "_" for c in requirement_summary[:30])
    filename = f"{OUTPUT_DIR}/schema_{safe_name}_{timestamp}.sql"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"-- AI Generated Schema\n")
        f.write(f"-- Requirement: {requirement_summary}\n")
        f.write(f"-- Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"-- Model: {MODEL} via Ollama (Docker)\n\n")
        f.write(content)
    return filename

# ── Helper: check Ollama is reachable ─────────────────────────────────────────
def check_ollama_connection():
    """Verify the Ollama container is reachable before starting."""
    try:
        response = requests.get("http://localhost:11434", timeout=5)
        if "Ollama" in response.text:
            return True
    except:
        pass
    return False

# ── Main application ───────────────────────────────────────────────────────────
def main():
    print("=" * 65)
    print("   AI-Based Schema Designer")
    print("   Powered by Ollama (Docker) + LLaMA 3")
    print("=" * 65)

    # Check connection to Ollama
    print("\n[*] Checking Ollama connection...", end=" ")
    if not check_ollama_connection():
        print("FAILED")
        print("\n[!] Cannot reach Ollama at http://localhost:11434")
        print("    Make sure your Docker containers are running:")
        print("    > docker compose ps")
        return
    print("OK")
    print(f"[*] Model : {MODEL}")
    print(f"[*] Schemas will be saved to: ./{OUTPUT_DIR}/\n")

    print("-" * 65)
    print("COMMANDS:")
    print("  Type your requirement  ->  Generate or refine schema")
    print("  save                   ->  Save current schema to .sql file")
    print("  new                    ->  Start a fresh conversation")
    print("  quit                   ->  Exit")
    print("-" * 65)

    # Conversation loop — supports multi-turn so user can refine schema
    conversation_history = [{"role": "system", "content": SYSTEM_PROMPT}]
    current_schema = ""
    first_requirement = ""
    session_count = 0

    while True:
        print()
        user_input = input("You: ").strip()

        # Handle special commands
        if not user_input:
            continue

        if user_input.lower() == "quit":
            print("\n[*] Goodbye! Don't forget to submit your generated schema files.")
            break

        if user_input.lower() == "new":
            conversation_history = [{"role": "system", "content": SYSTEM_PROMPT}]
            current_schema = ""
            first_requirement = ""
            session_count += 1
            print(f"\n[*] Started new session #{session_count + 1}. Conversation cleared.")
            continue

        if user_input.lower() == "save":
            if not current_schema:
                print("\n[!] Nothing to save yet. Generate a schema first.")
                continue
            filepath = save_schema(current_schema, first_requirement)
            print(f"\n[*] Schema saved to: {filepath}")
            continue

        # Add user message to history
        conversation_history.append({"role": "user", "content": user_input})

        # Store first requirement for filename
        if not first_requirement:
            first_requirement = user_input

        # Call Ollama
        print("\n[AI is thinking...]\n")
        response = ask_ollama(conversation_history)

        # Add AI response to history for multi-turn context
        conversation_history.append({"role": "assistant", "content": response})
        current_schema = response

        # Display response
        print("AI Schema Designer:")
        print("-" * 65)
        print(response)
        print("-" * 65)
        print("[Tip] Type 'save' to save this schema, or ask for modifications.")

# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    main()
