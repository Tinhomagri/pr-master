import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULTS = ROOT / "config" / "default.json"
PROJECTS = ROOT / "config" / "projects"
STANDARDS = ROOT / "standards"
CACHE = ROOT / ".cache"


def _deep_merge(base, override):
    out = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def load(project=None):
    cfg = json.loads(DEFAULTS.read_text(encoding="utf-8"))
    if project:
        path = PROJECTS / f"{project}.json"
        if not path.exists():
            available = sorted(p.stem for p in PROJECTS.glob("*.json"))
            raise SystemExit(
                f"projeto '{project}' nao encontrado em config/projects. "
                f"disponiveis: {', '.join(available) or 'nenhum'}"
            )
        cfg = _deep_merge(cfg, json.loads(path.read_text(encoding="utf-8")))
    cfg["model"] = os.getenv("BOT_MODEL", cfg["model"])
    return cfg


def persona(cfg):
    name = cfg.get("persona", "caio-magri")
    path = STANDARDS / f"{name}.md"
    if not path.exists():
        raise SystemExit(f"persona '{name}' nao encontrada em standards/{name}.md")
    return path.read_text(encoding="utf-8")


def project_standards(cfg):
    parts = []
    for name in cfg.get("standards_files", []):
        path = STANDARDS / name
        if path.exists():
            parts.append(f"<!-- {name} -->\n{path.read_text(encoding='utf-8')}")
    return "\n\n".join(parts)
