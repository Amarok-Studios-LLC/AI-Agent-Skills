"""Explicit global instruction integration; preserves other skills, hooks and settings."""
from pathlib import Path
import uuid

from toolkit_records import atomic_write, timestamp


BEGIN = '<!-- software-engineering-toolkit:start -->'
END = '<!-- software-engineering-toolkit:end -->'


def integrate(codex_home, skill_path, remove=False):
    home = Path(codex_home).expanduser().resolve()
    agents = home / 'AGENTS.md'
    if agents.is_symlink():
        raise ValueError('Refusing to replace symlinked global instructions')
    before = agents.read_bytes().decode('utf-8') if agents.exists() else ''
    if before.count(BEGIN) != before.count(END) or before.count(BEGIN) > 1:
        raise ValueError('Ambiguous integration markers; preserve the file and inspect manually')
    block = (BEGIN + '\n'
             'For software engineering project work, use the globally installed software-engineering-toolkit skill at '
             + str(Path(skill_path).resolve() / 'SKILL.md') + '. '
             'Apply it across project chats and prompts unless the user explicitly scopes it out. '
             'Start new projects with a focused, bounded definition interview; gather enough confirmed information to begin, '
             'and clarify ambiguity before dependent work. Favor confirmed single-server/shared-host capabilities and free tools; '
             'do not add setup hurdles or assume a stack. '
             'On EVERY project turn, read the portable context and relevant knowledge/decision records, evaluate ALL project '
             'documents and applicable engineering, optimization, SEO, security and support requirements for consistency, '
             'act on relevant changes, and persist the resulting state before handoff. '
             'Keep records project-specific, version every substantive document revision without deleting older versions, '
             'record decisions with timestamps, sources and concise rationale, and surface conflicts for clarification. '
             'Use incremental evidence for unchanged material; do not replace the every-turn review with occasional cleanup. '
             'Obtain developer decisions for major refactoring, architecture changes or new third-party integrations. '
             'Existing authorization, project instructions and explicit requests to discuss/define without implementation still apply. '
             'Do not initialize projects during unrelated conversation or imply that this instruction authorizes publication, '
             'messages, paid services or production changes.\n' + END)
    if BEGIN in before:
        start = before.index(BEGIN)
        finish = before.index(END) + len(END)
        if finish < start:
            raise ValueError('Integration markers are out of order')
        after = before[:start] + ('' if remove else block) + before[finish:]
    elif remove:
        after = before
    else:
        # Marked block has no separator outside its markers, so removal restores the original exactly.
        after = before + block
    if before == after:
        return {'changed': False, 'installed': not remove, 'global_instructions': str(agents)}
    backup_root = home / 'skill-integrations' / 'software-engineering-toolkit'
    for candidate in (home / 'skill-integrations', backup_root):
        if candidate.is_symlink():
            raise ValueError('Refusing to follow an integration backup symlink')
    backup_root.mkdir(parents=True, exist_ok=True)
    backup = backup_root / ('AGENTS-' + timestamp().replace(':', '-') + '-' + uuid.uuid4().hex + '.md')
    if agents.exists():
        with backup.open('xb') as stream:
            stream.write(agents.read_bytes())
    atomic_write(agents, after)
    return {'changed': True, 'installed': not remove, 'global_instructions': str(agents),
            'backup': str(backup) if backup.exists() else None,
            'activation': 'Start a new chat or reload instructions. Global instructions guide behavior; no command hooks or trust settings are changed.'}
