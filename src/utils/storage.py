"""Persistent JSON storage for the ZERO ticket system."""

import json
import os
import re
import threading
from pathlib import Path
from typing import Any, Optional

# ── Paths ──────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parents[1]  # ZERO/
DATA_DIR = PROJECT_ROOT / "data"
DATA_FILE = DATA_DIR / "tickets.json"
_LOCK = threading.Lock()

# ── Default seed data ──────────────────────────────────────────────────────

DEFAULT_CATEGORIES = [
    {"id": "giveaway",          "name": "🎁 Giveaway Claim",       "description": "Claim your giveaway prize",          "enabled": True, "position": 0},
    {"id": "partnership",       "name": "🤝 Partnership",          "description": "Propose a partnership",               "enabled": True, "position": 1},
    {"id": "support",           "name": "🆘 Support",              "description": "Get help with an issue",              "enabled": True, "position": 2},
    {"id": "sponsor",           "name": "💰 Sponsor",              "description": "Become a sponsor",                    "enabled": True, "position": 3},
    {"id": "staff_application", "name": "👮 Staff Application",    "description": "Apply for a staff position",         "enabled": True, "position": 4},
]

DEFAULT_SETTINGS = {
    "staff_role_ids": [],
    "admin_role_ids": [],
    "panel_channel_id": None,
    "active_category_id": None,
    "closed_category_id": None,
    "ticket_log_channel_id": None,
}


# ── Helpers ────────────────────────────────────────────────────────────────

def slugify(text: str) -> str:
    """Convert a category name to a lowercase ID safe for channel names."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


# ── Core storage ───────────────────────────────────────────────────────────

def load_data() -> dict:
    """Load the tickets JSON database. Seeds defaults on first run."""
    if not DATA_FILE.exists():
        data = _default_data()
        save_data(data)
        return data
    with _LOCK:
        with open(DATA_FILE, encoding="utf-8") as f:
            return json.load(f)


def save_data(data: dict) -> None:
    """Atomically write the database to disk."""
    with _LOCK:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        tmp = DATA_FILE.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(str(tmp), str(DATA_FILE))


def _default_data() -> dict:
    return {
        "categories": [c.copy() for c in DEFAULT_CATEGORIES],
        "settings": DEFAULT_SETTINGS.copy(),
        "tickets": [],
    }


# ── Category helpers ───────────────────────────────────────────────────────

def get_categories() -> list[dict]:
    return load_data()["categories"]


def save_categories(categories: list[dict]) -> None:
    data = load_data()
    data["categories"] = categories
    save_data(data)


def get_enabled_categories() -> list[dict]:
    return [c for c in get_categories() if c.get("enabled", True)]


def add_category(name: str, description: str = "") -> dict:
    categories = get_categories()
    category_id = slugify(name)
    if any(c["id"] == category_id for c in categories):
        raise ValueError(f"Category ID '{category_id}' already exists")
    category = {
        "id": category_id,
        "name": name,
        "description": description.strip(),
        "enabled": True,
        "position": len(categories),
    }
    categories.append(category)
    save_categories(categories)
    return category


def update_category(category_id: str, name: Optional[str] = None,
                    description: Optional[str] = None) -> Optional[dict]:
    categories = get_categories()
    for c in categories:
        if c["id"] == category_id:
            if name is not None:
                new_id = slugify(name)
                if new_id != category_id and any(x["id"] == new_id for x in categories):
                    raise ValueError(f"Category ID '{new_id}' already exists")
                c["id"] = new_id
                c["name"] = name
            if description is not None:
                c["description"] = description.strip()
            save_categories(categories)
            return c
    return None


def remove_category(category_id: str) -> bool:
    categories = get_categories()
    before = len(categories)
    categories = [c for c in categories if c["id"] != category_id]
    if len(categories) == before:
        return False
    save_categories(categories)
    return True


def toggle_category(category_id: str) -> Optional[dict]:
    categories = get_categories()
    for c in categories:
        if c["id"] == category_id:
            c["enabled"] = not c.get("enabled", True)
            save_categories(categories)
            return c
    return None


def reorder_category(category_id: str, new_position: int) -> Optional[dict]:
    categories = get_categories()
    cat = next((c for c in categories if c["id"] == category_id), None)
    if cat is None:
        return None
    categories = [c for c in categories if c["id"] != category_id]
    cat["position"] = new_position
    categories.insert(min(new_position, len(categories)), cat)
    for i, c in enumerate(categories):
        c["position"] = i
    save_categories(categories)
    return cat


# ── Settings helpers ───────────────────────────────────────────────────────

def get_settings() -> dict:
    return load_data()["settings"]


def save_settings(settings: dict) -> None:
    data = load_data()
    data["settings"] = settings
    save_data(data)


def update_settings(**kwargs) -> dict:
    settings = get_settings()
    settings.update(kwargs)
    save_settings(settings)
    return settings


# ── Ticket helpers ─────────────────────────────────────────────────────────

def get_tickets() -> list[dict]:
    return load_data()["tickets"]


def save_tickets(tickets: list[dict]) -> None:
    data = load_data()
    data["tickets"] = tickets
    save_data(data)


def add_ticket(ticket: dict) -> None:
    data = load_data()
    data["tickets"].append(ticket)
    save_data(data)
