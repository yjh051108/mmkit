# Contributing to mmkit

Thanks for your interest in contributing to mmkit! This kit is designed to stay **general, host-agnostic, and competition-agnostic**. Please keep that in mind for every change.

## How to contribute

1. **Fork** the repo and create a feature branch.
2. Make your changes (see conventions below).
3. Run the verification steps.
4. Open a Pull Request with a clear description of what changed and why.

## Conventions

### Skill structure

- Every sub-skill lives in `skills/<skill-name>/` and **must** contain a `SKILL.md` with YAML frontmatter:
  - `name` — matches the directory name
  - `description` — includes trigger phrases (bilingual where relevant) and the `Use when user says ...` pattern
  - `argument-hint`, `allowed-tools`
- A sub-skill must be **independently usable** — do not assume the orchestrator is running.
- Shared logic goes in `shared/` (scripts) or a skill's `references/` (markdown) — avoid duplicating rules across skills.

### Parameters over variants

Prefer a single skill with a parameter (`lang`, `output_format`, `provider`, `plan_mode`, `domain`) over near-duplicate skills. This kit deliberately merged per-language / per-format variants.

### Language

- Chinese skills: keep Chinese as the working language of the workflow instructions.
- English skills: English.
- When a skill covers both, use the language of the primary audience and keep trigger phrases for both in the description.

### Verification (must pass before PR)

```bash
# 1. Workflow template references resolve to real skill dirs
python -c "
import json, os
t = json.load(open('templates/workflow_templates.json', encoding='utf-8'))
ref = set()
for w in t.values():
    ref.add(w.get('pipeline_skill'))
    for s in w.get('sub_steps', []):
        ref.add(s.get('skill_name') if isinstance(s, dict) else s)
ref.discard(None)
missing = ref - {d for d in os.listdir('skills') if os.path.isdir(os.path.join('skills', d))}
assert not missing, f'Unresolved skill refs: {missing}'
print('OK: all template refs resolve')
"

# 2. All Python compiles
python -m py_compile orchestrator/*.py shared/*.py skills/*/*.py

# 3. CLI help works
python orchestrator/mm_flow.py --help
```

## Code of conduct

- Be respectful; this is a community project under the MIT license.
- No fabricated references in docs or examples — mark uncertain facts `[待验证]`.
- Don't add competition-specific hardcoding to shared/generic paths (competition-specific data belongs in `templates/competition_rules.json`).
