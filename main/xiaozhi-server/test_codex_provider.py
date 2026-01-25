import argparse
import sys
from pathlib import Path


def _build_dialogue(system_prompt, user_text, history):
    dialogue = []
    if system_prompt:
        dialogue.append({"role": "system", "content": system_prompt})
    dialogue.extend(history)
    if user_text:
        dialogue.append({"role": "user", "content": user_text})
    return dialogue


def _run_once(provider, session_id, dialogue):
    chunks = []
    for token in provider.response(session_id, dialogue):
        sys.stdout.write(token)
        sys.stdout.flush()
        chunks.append(token)
    sys.stdout.write("\n")
    reply = "".join(chunks).strip()
    if reply:
        dialogue.append({"role": "assistant", "content": reply})
    return reply


def main():
    parser = argparse.ArgumentParser(
        description="Minimal Codex LLMProvider streaming test."
    )
    parser.add_argument("--codex-bin", default="codex.cmd")
    parser.add_argument("--model", default="gpt-5.2")
    parser.add_argument("--workspace", default=str(Path.cwd()))
    parser.add_argument(
        "--system-prompt",
        default="You are a concise assistant. Reply in short sentences.",
    )
    parser.add_argument("--session-id", default="codex-test-session")
    parser.add_argument(
        "--once",
        default="",
        help="Run a single prompt and exit. Leave empty for interactive mode.",
    )
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    sys.path.insert(0, str(script_dir))

    from core.providers.llm.codex.codex import LLMProvider

    config = {
        "type": "codex",
        "codex_bin": args.codex_bin,
        "model_name": args.model,
        "workspace": args.workspace,
        "auto_approve": True,
        "network_access": True,
        "system_prompt_mode": "first_turn",
        "bootstrap_mode": "none",
        "export_api_key": False,
    }

    provider = LLMProvider(config)
    dialogue_history = []
    session_id = args.session_id

    try:
        if args.once:
            dialogue = _build_dialogue(args.system_prompt, args.once, dialogue_history)
            _run_once(provider, session_id, dialogue)
            return

        while True:
            user_text = input("You> ").strip()
            if not user_text or user_text.lower() in ("exit", "quit"):
                break
            dialogue = _build_dialogue(args.system_prompt, user_text, dialogue_history)
            reply = _run_once(provider, session_id, dialogue)
            if reply:
                dialogue_history.append({"role": "user", "content": user_text})
                dialogue_history.append({"role": "assistant", "content": reply})
    finally:
        # Best-effort cleanup of Codex app-server processes.
        sessions = getattr(provider, "_sessions", {})
        for session in sessions.values():
            try:
                session.close()
            except Exception:
                pass


if __name__ == "__main__":
    main()
