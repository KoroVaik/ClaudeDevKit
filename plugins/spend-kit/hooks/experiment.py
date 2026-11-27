"""PreToolUse hook for the Agent tool: the helper experiments and the reset of context-heavy helpers (see
`scripts/experiments.py`, docs/features/catch-wasted-work.md).

- A `subagent_type` of an experiment type (EXPERIMENTS) whose `model` is missing or equals its agent file's `model:` gets
  the next variant's `model` and `effort`, and the pick is logged in `experiments.jsonl`. A caller's other model is its
  own choice: left alone, nothing logged. A stopped variant is skipped; with only the old one left nothing changes.
- A `subagent_type` in CONTEXT_HEAVY whose `model` is Opus or Fable gets the agent file's model back (`model` removed
  from the input); logged with the variant `reset`.

When it changes the input it prints the whole `tool_input` with the changes as `updatedInput` and allows the call.
It prints nothing otherwise, never blocks and never fails: any error ends it with exit code 0."""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


def same_model(given, wanted):
    given, wanted = str(given or "").lower(), str(wanted or "").lower()
    import signals
    return given == wanted or (signals.family(given) is not None and signals.family(given) == signals.family(wanted))


def updated_input(payload):
    """The changed `tool_input` of an `Agent` call, or None when nothing changes."""
    import experiments
    import signals
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return None
    kind = str(tool_input.get("subagent_type") or "")
    session = os.environ.get("CLAUDE_CODE_SESSION_ID") or str(payload.get("session_id") or "")
    call = payload.get("tool_use_id")
    given = tool_input.get("model")
    if kind in experiments.CONTEXT_HEAVY:
        if signals.family(given) not in experiments.EXPENSIVE:
            return None
        settings = signals.agent_settings(kind, payload.get("cwd")) or {}
        experiments.log_reset(kind, session, call, settings.get("model"), given)
        return {key: value for key, value in tool_input.items() if key != "model"}
    if kind not in experiments.EXPERIMENTS:
        return None
    settings = signals.agent_settings(kind, payload.get("cwd")) or {}
    if given and not same_model(given, settings.get("model")):
        return None  # the caller chose another model: its own choice
    picked = experiments.choose(kind, session, call)
    if picked is None:
        return None
    _, model, effort = picked
    return {**tool_input, "model": model, "effort": effort}


def main():
    payload = json.loads(sys.stdin.buffer.read().decode("utf-8-sig"))
    changed = updated_input(payload) if isinstance(payload, dict) else None
    if changed is not None:
        sys.stdout.write(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow",
                                                           "updatedInput": changed}}, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception:  # a hook must never block a call
        pass
    sys.exit(0)
