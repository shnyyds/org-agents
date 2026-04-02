import json
from pathlib import Path
from typing import Any, Dict, List


AGENT_KB_FILE = Path(__file__).resolve().parent.parent / "data" / "agent_kb_bindings.json"


def _ensure_store():
    AGENT_KB_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not AGENT_KB_FILE.exists():
        AGENT_KB_FILE.write_text(json.dumps({"bindings": {}}, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_store() -> Dict[str, Any]:
    _ensure_store()
    return json.loads(AGENT_KB_FILE.read_text(encoding="utf-8"))


def _write_store(data: Dict[str, Any]):
    _ensure_store()
    AGENT_KB_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


class AgentKnowledgeBindingService:
    def list_bindings(self) -> Dict[str, List[str]]:
        return _read_store().get("bindings", {})

    def get_binding(self, agent_id: str) -> List[str]:
        bindings = self.list_bindings()
        return bindings.get(agent_id, [])

    def set_binding(self, agent_id: str, kb_ids: List[str]) -> List[str]:
        store = _read_store()
        store.setdefault("bindings", {})[agent_id] = kb_ids
        _write_store(store)
        return kb_ids


agent_kb_service = AgentKnowledgeBindingService()
