"""UserPromptSubmit hook: tell a session that the project lead watches it.

A session the owner started and the lead took over is an active record with `"owner": true` in the project's
session registry (`dev-kit-sessions add --owner`). At each owner message to such a session this hook adds a short
note to its context. It never blocks: any error ends it with exit code 0 and no output."""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

NOTE = ("Цю сесію відкрив власник, а тепер її веде керівник проєкту: він читає твій стан і останню відповідь, "
        "повідомлень не надсилає. Коли задачу повністю закінчено, напиши в останній відповіді окремим рядком "
        "«Роботу завершено»; поки є питання до власника, цього рядка не пиши.")
COMMIT_NOTE = " Свою роботу коміть у main після кожного завершеного кроку: керівник її не зливає."


def is_owner_session(project, session_id):
    """Whether the project's registry holds an active owner record for this session id (full or prefix)."""
    import sessions  # imported late so that any failure of it is caught by main
    path = sessions.registry_path(project, create=False)  # a project with no registry gets no state folder
    if not path.is_file():
        return False
    records = sessions.load(path)
    return any(record.get("owner") is True and sessions.matches(session_id, str(record.get("id")))
               for record in sessions.active(records))


def in_worktree(cwd):
    """Whether cwd is inside a linked git worktree (its git dir differs from the repository's common dir)."""
    import sessions
    out = sessions.run_git(cwd, "rev-parse", "--git-dir", "--git-common-dir")
    lines = (out or "").splitlines()
    if len(lines) != 2:
        return False
    git_dir, common = (sessions.norm(Path(cwd) / line) for line in lines)
    return git_dir != common


def main():
    try:
        call = json.loads(sys.stdin.buffer.read().decode("utf-8-sig"))
        session_id = str(call.get("session_id") or "")
        cwd = str(call.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or "")
    except Exception:
        return
    if not session_id or not cwd:
        return
    try:
        if not is_owner_session(cwd, session_id):
            return
        note = NOTE if in_worktree(cwd) else NOTE + COMMIT_NOTE
        sys.stdout.reconfigure(encoding="utf-8")
        json.dump({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": note}}, sys.stdout)
    except Exception:
        return  # a broken registry never blocks a message


if __name__ == "__main__":
    main()
    sys.exit(0)
