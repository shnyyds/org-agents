import json
import hashlib
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Skills storage
# ---------------------------------------------------------------------------
SKILLS_FILE = Path(__file__).resolve().parent.parent / "data" / "skills.json"


def _ensure_skills_store():
    SKILLS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not SKILLS_FILE.exists():
        SKILLS_FILE.write_text(json.dumps({"skills": []}, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_skills_store() -> Dict[str, Any]:
    _ensure_skills_store()
    return json.loads(SKILLS_FILE.read_text(encoding="utf-8"))


def _write_skills_store(data: Dict[str, Any]):
    _ensure_skills_store()
    SKILLS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


class SkillService:
    def list_skills(self) -> List[Dict]:
        return _read_skills_store().get("skills", [])

    def get_skill(self, skill_id: str) -> Optional[Dict]:
        for skill in self.list_skills():
            if skill["id"] == skill_id:
                return skill
        return None

    def create_skill(self, name: str, description: str = "", content: str = "", enabled: bool = True) -> Dict:
        store = _read_skills_store()
        now = time.strftime("%Y-%m-%dT%H:%M:%S")
        skill_id = hashlib.md5(f"{name}{now}".encode()).hexdigest()[:10]
        skill = {
            "id": skill_id,
            "name": name,
            "description": description,
            "content": content,
            "enabled": enabled,
            "created_at": now,
            "updated_at": now,
        }
        store.setdefault("skills", []).append(skill)
        _write_skills_store(store)
        return skill

    def update_skill(self, skill_id: str, **kwargs) -> Optional[Dict]:
        store = _read_skills_store()
        for skill in store.get("skills", []):
            if skill["id"] == skill_id:
                for key in ("name", "description", "content", "enabled"):
                    if key in kwargs and kwargs[key] is not None:
                        skill[key] = kwargs[key]
                skill["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
                _write_skills_store(store)
                return skill
        return None

    def delete_skill(self, skill_id: str) -> bool:
        store = _read_skills_store()
        original_len = len(store.get("skills", []))
        store["skills"] = [s for s in store.get("skills", []) if s["id"] != skill_id]
        if len(store["skills"]) < original_len:
            _write_skills_store(store)
            # Cascade: remove from bindings
            agent_skill_service.remove_skill_from_all(skill_id)
            return True
        return False


# ---------------------------------------------------------------------------
# Agent-Skill bindings storage
# ---------------------------------------------------------------------------
AGENT_SKILL_FILE = Path(__file__).resolve().parent.parent / "data" / "agent_skill_bindings.json"


def _ensure_binding_store():
    AGENT_SKILL_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not AGENT_SKILL_FILE.exists():
        AGENT_SKILL_FILE.write_text(json.dumps({"bindings": {}}, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_binding_store() -> Dict[str, Any]:
    _ensure_binding_store()
    return json.loads(AGENT_SKILL_FILE.read_text(encoding="utf-8"))


def _write_binding_store(data: Dict[str, Any]):
    _ensure_binding_store()
    AGENT_SKILL_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


class AgentSkillBindingService:
    def list_bindings(self) -> Dict[str, List[str]]:
        return _read_binding_store().get("bindings", {})

    def get_binding(self, agent_id: str) -> List[str]:
        return self.list_bindings().get(agent_id, [])

    def set_binding(self, agent_id: str, skill_ids: List[str]) -> List[str]:
        store = _read_binding_store()
        store.setdefault("bindings", {})[agent_id] = skill_ids
        _write_binding_store(store)
        return skill_ids

    def remove_skill_from_all(self, skill_id: str):
        store = _read_binding_store()
        changed = False
        for agent_id, ids in store.get("bindings", {}).items():
            if skill_id in ids:
                store["bindings"][agent_id] = [sid for sid in ids if sid != skill_id]
                changed = True
        if changed:
            _write_binding_store(store)


# Module-level singletons
skill_service = SkillService()
agent_skill_service = AgentSkillBindingService()
