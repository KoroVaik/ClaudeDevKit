"""PreToolUse hook for the Agent tool: only the project's own narrow agents (.claude/agents/*.md) and agents of
enabled plugins may be launched, never a built-in or user-level agent type."""
import json
import os
import sys
from pathlib import Path


def read_json(path):
    """Return the JSON object in path, or {} if the file is missing or broken."""
    try:
        data = json.loads(path.read_text(encoding='utf-8-sig'))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def agent_stems(folder):
    return sorted(p.stem for p in folder.glob('*.md'))


def enabled_plugins(project):
    """Keys '<plugin>@<marketplace>' enabled after merging user, project and local settings (later overrides earlier)."""
    merged = {}
    files = [Path.home() / '.claude' / 'settings.json']
    if project:
        files += [project / '.claude' / 'settings.json', project / '.claude' / 'settings.local.json']
    for path in files:
        plugins = read_json(path).get('enabledPlugins')
        if isinstance(plugins, dict):
            merged.update(plugins)
    return sorted(key for key, value in merged.items() if value is True)


def same_path(left, right):
    try:
        return str(Path(left).resolve()).lower() == str(Path(right).resolve()).lower()
    except (OSError, TypeError, ValueError):
        return False


def install_path(key, project):
    """The install folder of a plugin key for this project from installed_plugins.json, or None."""
    entries = read_json(Path.home() / '.claude' / 'plugins' / 'installed_plugins.json').get('plugins')
    entries = [e for e in (entries.get(key) if isinstance(entries, dict) else None) or [] if isinstance(e, dict)]
    scoped = [e for e in entries if e.get('scope') in ('project', 'local') and project
              and same_path(e.get('projectPath') or '', project)]
    chosen = scoped or [e for e in entries if e.get('scope') == 'user']
    path = chosen[0].get('installPath') if chosen else None
    return Path(path) if isinstance(path, str) and path else None


def marketplace_agents_folder(key):
    """Agents folder of a plugin in a directory marketplace (loaded in place), or None."""
    name, _, marketplace = key.partition('@')
    entry = read_json(Path.home() / '.claude' / 'plugins' / 'known_marketplaces.json').get(marketplace)
    source = entry.get('source') if isinstance(entry, dict) else None
    location = entry.get('installLocation') if isinstance(entry, dict) else None
    if not (isinstance(source, dict) and source.get('source') == 'directory' and isinstance(location, str) and location):
        return None
    plugins = read_json(Path(location) / '.claude-plugin' / 'marketplace.json').get('plugins')
    for plugin in plugins if isinstance(plugins, list) else []:
        relative = plugin.get('source') if isinstance(plugin, dict) else None
        if plugin.get('name') == name and isinstance(relative, str) and relative.startswith('.'):
            return Path(location) / relative / 'agents'
    return None


def plugin_agents(key, project, plugin_root):
    """Agent names of an enabled plugin key (directory marketplace, install folder, sibling folder), or None if unknown."""
    name = key.split('@', 1)[0]
    installed = install_path(key, project)
    for folder in (marketplace_agents_folder(key), installed / 'agents' if installed else None,
                   plugin_root.parent / name / 'agents'):
        if folder and folder.is_dir():
            return agent_stems(folder)
    return None


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    try:
        call = json.loads(sys.stdin.buffer.read().decode('utf-8-sig'))
    except ValueError:
        call = {}
    call = call if isinstance(call, dict) else {}
    tool_input = call.get('tool_input')
    kind = (tool_input.get('subagent_type') if isinstance(tool_input, dict) else '') or ''

    project_dir = os.environ.get('CLAUDE_PROJECT_DIR') or call.get('cwd') or ''
    project = Path(project_dir) if project_dir else None
    project_agents = agent_stems(project / '.claude' / 'agents') if project else []
    plugin_root = Path(os.environ.get('CLAUDE_PLUGIN_ROOT') or Path(__file__).resolve().parents[1])

    # plugin name -> one agent list per enabled key (None: folder not found, any agent allowed)
    plugins = {}
    for key in enabled_plugins(project):
        plugins.setdefault(key.split('@', 1)[0], []).append(plugin_agents(key, project, plugin_root))

    plugin, _, agent = kind.partition(':')
    if kind in project_agents:
        return
    if agent and any(names is None or agent in names for names in plugins.get(plugin, [])):
        return

    allowed = list(project_agents)
    for name, lists in sorted(plugins.items()):
        if None in lists:
            allowed.append(f'{name}:*')
        allowed += sorted({f'{name}:{a}' for names in lists if names for a in names})
    json.dump({'hookSpecificOutput': {
        'hookEventName': 'PreToolUse', 'permissionDecision': 'deny',
        'permissionDecisionReason': f"subagent type {kind or '(none)'!r} is not a narrow project or enabled plugin "
                                    "agent; use one of: " + (', '.join(allowed) or '(none)')}}, sys.stdout)


if __name__ == '__main__':
    main()
