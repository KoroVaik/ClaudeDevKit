"""The title prefixes of the sessions rules-kit makes or tells apart (plans/role-names.md): one place for `retro.py`,
`fixes.py` and `talk.py`. A script that makes a title uses the new prefix; a script that matches a title uses the
`*_PREFIXES` tuple, which holds the new prefix and the old one, so a session that runs under an old title keeps
working until it ends. Drop the old prefixes once no such session is left. This is a copy of dev-kit's
`scripts/session_titles.py` (no plugin imports another's code); change both together."""

LEAD = "L:"  # the project lead, `L: <project>`
MANAGER = "M:"  # a task session, `M: <task>`
DISCUSS = "Discuss:"  # a discussion session, `Discuss: <topic>`
RETRO = "Retro:"  # the background retro session, `Retro: <project folder>`
DOCS = "Docs:"  # the weekly docs session, `Docs: <project folder>`

LEGACY_LEAD = "P:"
LEGACY_MANAGER = "C:"
LEGACY_DISCUSS = "Обговорення:"
LEGACY_RETRO = "Ретро:"
LEGACY_DOCS = "Документація:"

LEAD_PREFIXES = (LEAD, LEGACY_LEAD)
MANAGER_PREFIXES = (MANAGER, LEGACY_MANAGER)
DISCUSS_PREFIXES = (DISCUSS, LEGACY_DISCUSS)
RETRO_PREFIXES = (RETRO, LEGACY_RETRO)
DOCS_PREFIXES = (DOCS, LEGACY_DOCS)
