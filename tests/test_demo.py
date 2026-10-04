"""Security and evidence-integrity checks for the local demonstration surface."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load_script(name):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DemoTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "Node is required for client rendering regression")
    def test_failed_benchmark_does_not_render_improvement(self):
        program = r'''
const assert = require('assert');
const fs = require('fs');
const vm = require('vm');
class Element {
  constructor() { this.children = []; this.textContent = ''; }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = children; }
  addEventListener() {}
  setAttribute() {}
}
const nodes = new Map();
const context = vm.createContext({
  document: {
    querySelectorAll: () => [],
    getElementById: id => { if (!nodes.has(id)) nodes.set(id, new Element()); return nodes.get(id); },
    createElement: () => new Element(),
  },
  fetch: () => new Promise(() => {}),
});
vm.runInContext(fs.readFileSync('demo/app.js', 'utf8'), context);
(async () => {
  for (const status of ['failed', undefined]) {
    context.fetch = async () => ({ok: true, json: async () => ({status, headline: 'FAKE 100x improvement', metrics: {'Decision mismatches': 2}, limitations: []})});
    await context.loadBenchmark();
    assert.equal(nodes.get('benchmark-status').textContent, 'COMPARISON FAILED VALIDATION');
    assert(!nodes.get('benchmark-headline').textContent.includes('100x'));
    assert.equal(nodes.get('benchmark-metrics').children.length, 0);
    assert(nodes.get('benchmark-limitations').children.some(c => c.textContent === 'Decision mismatches: 2'));
  }
  context.fetch = async () => ({ok: true, json: async () => ({status: 'passed', headline: 'Verified comparison', metrics: {'Decision mismatches': 0}, limitations: []})});
  await context.loadBenchmark();
  assert.equal(nodes.get('benchmark-headline').textContent, 'Verified comparison');
  assert.equal(nodes.get('benchmark-metrics').children.length, 1);
})().catch(error => { console.error(error); process.exitCode = 1; });
'''
        subprocess.run([shutil.which("node"), "-e", program], cwd=ROOT, check=True, capture_output=True, text=True)

    @unittest.skipUnless(shutil.which("node"), "Node is required for client rendering regression")
    def test_panel_renders_dependence_and_degrades_without_it(self):
        evidence = (ROOT / "demo" / "evidence" / "panel.json").read_text()
        result = subprocess.run([shutil.which("node"), "tests/panel_render_check.js"], cwd=ROOT, input=evidence, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("panel render checks passed", result.stdout)

    def test_only_allowlisted_files_served(self):
        server = load_script("serve-demo")
        for path in ("/.env", "/.venv/pyvenv.cfg", "/SCIENCE.md", "/../SCIENCE.md", "/%2e%2e/SCIENCE.md", "/runs/verified-workflow/session.json"):
            with self.subTest(path=path):
                self.assertEqual(server.resolve_response(path)[0], 404)
        self.assertEqual(server.resolve_response("/")[0], 200)
        for path in ("/panel", "/panel.js", "/panel.css", "/evidence/panel.json"):
            with self.subTest(path=path):
                self.assertEqual(server.resolve_response(path)[0], 200)
        panel = json.loads(server.resolve_response("/evidence/panel.json")[2])
        self.assertTrue(all("decision_dependence" in c for c in panel["candidates"]))
        self.assertNotIn("/Volumes/", server.resolve_response("/evidence/panel.json")[2].decode())

    def test_symlink_escape_rejected(self):
        server = load_script("serve-demo")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "demo").mkdir()
            (root / "secret.txt").write_text("private")
            (root / "demo" / "index.html").symlink_to(root / "secret.txt")
            self.assertEqual(server.resolve_response("/", root)[0], 404)

    def test_evidence_has_exact_source_ids_hashes_and_values(self):
        build = load_script("build-demo")
        manifest = build.build()
        for name, record_id in build.RECORDS.items():
            raw = (ROOT / "runs" / "live" / f"{record_id}.json").read_bytes()
            public = json.loads((ROOT / "demo" / "evidence" / f"{name}.json").read_text())
            self.assertEqual(public["id"], record_id)
            self.assertEqual(manifest["records"][name]["source_sha256"], hashlib.sha256(raw).hexdigest())
            source = json.loads(raw)
            source["payload"].pop("artifact_paths", None)
            self.assertEqual(public, source)
        check = json.loads((ROOT / "demo" / "evidence" / "guide-check.json").read_text())
        no = check["payload"]["observations"]["conditions"]["without_il6"]
        self.assertEqual(len(no["leave_one_out"]["omissions"]), 3)
        self.assertLess(no["leave_one_out"]["score_min"], 0)

    def test_benchmark_missing_and_redacted_summary(self):
        server = load_script("serve-demo")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(server.resolve_response("/runs/benchmark/report.json", root)[0], 404)
            (root / "runs" / "benchmark").mkdir(parents=True)
            (root / "runs" / "benchmark" / "report.json").write_text(json.dumps({"headline": "Measured", "metrics": {"calls": 5, "api_key": "secret"}, "limitations": ["See /Users/private/a.json"], "credentials": "private", "source_path": "private"}))
            code, _, body = server.resolve_response("/runs/benchmark/report.json", root)
            self.assertEqual(code, 200)
            self.assertNotIn(b"secret", body)
            self.assertNotIn(b"/Users/", body)
            self.assertNotIn(b"credentials", body)
            self.assertEqual(json.loads(body)["metrics"]["calls"], 5)


if __name__ == "__main__":
    unittest.main()
