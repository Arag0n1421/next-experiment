"""Reapply the verified isolated Omnigent 0.16.0 subscription-model fix."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import omnigent

root = Path(__file__).resolve().parents[1]
receipt = json.loads((root / "setup/CODEX-COMPATIBILITY.json").read_text())
path = Path(omnigent.__file__).parent / "inner/codex_executor.py"
digest = hashlib.sha256(path.read_bytes()).hexdigest()
if digest == receipt["patched_sha256"]:
    print("Compatibility patch already applied.")
elif importlib.metadata.version("omnigent") == "0.16.0" and digest == receipt["original_sha256"]:
    text = path.read_text().replace('        if self._model_provider_override is not None:\n            model = None\n', '        if self._model_provider_override is not None and self._model_provider_override != "openai":\n            model = None\n')
    assert hashlib.sha256(text.encode()).hexdigest() == receipt["patched_sha256"]
    path.write_text(text)
    print("Verified compatibility patch applied.")
else:
    raise SystemExit("Different package version or source hash; review rather than patching blindly.")
