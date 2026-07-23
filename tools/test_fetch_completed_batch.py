"""
Ad-hoc verification script for fetch_completed_batch() -- run directly with
`python tools/test_fetch_completed_batch.py`. Uses a stub OpenAI client and
a locally-generated PNG (no network calls) for both the batch-output and
synchronous-fallback code paths.
"""
import base64
import io
import json
import os
import tempfile

from PIL import Image

import content_engine.image_module.template_batch_generator as tbg

failures = []


def check(label, condition):
    status = "OK" if condition else "FAIL"
    print(f"[{status}] {label}")
    if not condition:
        failures.append(label)


def _fake_b64_image():
    buf = io.BytesIO()
    Image.new("RGB", (1536, 1024), (10, 100, 200)).save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


ASSIGNMENTS = [
    {"category": "dividend", "idx": 0},
    {"category": "tech", "idx": 0},
]


def _seed_state(tmp_base):
    state = {
        "batch_id": "batch_xyz789",
        "submitted_at": "2026-07-25T02:00:00+00:00",
        "category_assignments": ASSIGNMENTS,
        "status": "submitted",
    }
    tbg._save_state(state)


class _FakeOutputFile:
    def __init__(self, text):
        self.text = text


class _FakeFiles:
    def __init__(self, output_text):
        self._output_text = output_text

    def content(self, file_id):
        return _FakeOutputFile(self._output_text)


class _FakeBatches:
    def __init__(self, status):
        self.status_to_report = status

    def retrieve(self, batch_id):
        return type("Obj", (), {
            "id": batch_id,
            "status": self.status_to_report,
            "output_file_id": "outfile_1",
        })()


class _FakeImages:
    def __init__(self):
        self.generate_calls = 0

    def generate(self, model, prompt, size, quality, n):
        self.generate_calls += 1
        return type("Obj", (), {
            "data": [type("D", (), {"b64_json": _fake_b64_image()})()]
        })()


class _FakeClient:
    def __init__(self, status, output_lines=None):
        self.batches = _FakeBatches(status)
        self.files = _FakeFiles(output_lines or "")
        self.images = _FakeImages()


with tempfile.TemporaryDirectory() as tmp_dir:
    original_state_path = tbg.BATCH_STATE_PATH
    original_template_base = tbg.TEMPLATE_BASE
    tbg.BATCH_STATE_PATH = os.path.join(tmp_dir, "state", "template_batch_state.json")
    tbg.TEMPLATE_BASE = os.path.join(tmp_dir, "templates")
    try:
        # -- No active batch: no-op ---------------------------------------
        result = tbg.fetch_completed_batch(openai_client=_FakeClient("completed"))
        check("no-op when no active batch", "noop" in result)

        # -- Completed: downloads, pads, saves, marks 'fetched' ------------
        _seed_state(tmp_dir)
        b64 = _fake_b64_image()
        output_lines = "\n".join(
            json.dumps({
                "custom_id": f"{a['category']}__{a['idx']}",
                "response": {"status_code": 200, "body": {"data": [{"b64_json": b64}]}},
            })
            for a in ASSIGNMENTS
        )
        fake_client = _FakeClient("completed", output_lines)
        result = tbg.fetch_completed_batch(openai_client=fake_client)
        check("completed batch reports fetched", "fetched" in result)
        check("2 files saved", len(result["fetched"]) == 2)
        for a in ASSIGNMENTS:
            outer_dir = os.path.join(tbg.TEMPLATE_BASE, a["category"], "outer")
            inner_dir = os.path.join(tbg.TEMPLATE_BASE, a["category"], "inner")
            check(f"{a['category']} outer dir has 1 file", len(os.listdir(outer_dir)) == 1)
            check(f"{a['category']} inner dir has 1 file", len(os.listdir(inner_dir)) == 1)
            outer_file = os.path.join(outer_dir, os.listdir(outer_dir)[0])
            check(f"{a['category']} outer image is 640x480", Image.open(outer_file).size == (640, 480))
        state_after = tbg._load_state()
        check("state marked 'fetched'", state_after["status"] == "fetched")

        # -- In progress: leaves state as 'submitted' ----------------------
        _seed_state(tmp_dir)
        result = tbg.fetch_completed_batch(openai_client=_FakeClient("in_progress"))
        check("in-progress batch reports in_progress", "in_progress" in result)
        check("state remains 'submitted'", tbg._load_state()["status"] == "submitted")

        # -- Failed: falls back to synchronous generation ------------------
        _seed_state(tmp_dir)
        fallback_client = _FakeClient("failed")
        result = tbg.fetch_completed_batch(openai_client=fallback_client)
        check("failed batch reports fetched_via_fallback", "fetched_via_fallback" in result)
        check(
            "images.generate called once per assignment",
            fallback_client.images.generate_calls == len(ASSIGNMENTS),
        )
        check("state marked 'fetched_via_fallback'", tbg._load_state()["status"] == "fetched_via_fallback")
    finally:
        tbg.BATCH_STATE_PATH = original_state_path
        tbg.TEMPLATE_BASE = original_template_base

if failures:
    print(f"\n{len(failures)} FAILURE(S)")
    raise SystemExit(1)
print("\nAll cases passed.")
