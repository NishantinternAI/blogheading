"""
Ad-hoc verification script for submit_weekly_batch() -- run directly with
`python tools/test_submit_weekly_batch.py`. Uses a stub OpenAI client so no
real network calls or costs occur.
"""
import json
import os
import tempfile

import content_engine.image_module.template_batch_generator as tbg

failures = []


def check(label, condition):
    status = "OK" if condition else "FAIL"
    print(f"[{status}] {label}")
    if not condition:
        failures.append(label)


class _FakeFiles:
    def create(self, file, purpose):
        return type("Obj", (), {"id": "file_abc123"})()


class _FakeBatches:
    def __init__(self):
        self.create_calls = []

    def create(self, input_file_id, endpoint, completion_window):
        self.create_calls.append((input_file_id, endpoint, completion_window))
        return type("Obj", (), {"id": "batch_xyz789"})()


class _FakeClient:
    def __init__(self):
        self.files = _FakeFiles()
        self.batches = _FakeBatches()


with tempfile.TemporaryDirectory() as tmp_dir:
    original_state_path = tbg.BATCH_STATE_PATH
    tbg.BATCH_STATE_PATH = os.path.join(tmp_dir, "template_batch_state.json")
    try:
        # -- First submit: should go through and write state -------------
        fake_client = _FakeClient()
        result = tbg.submit_weekly_batch(openai_client=fake_client)
        check("first submit is not skipped", "skipped" not in result)
        check("batch_id recorded", result.get("batch_id") == "batch_xyz789")
        check("status is 'submitted'", result.get("status") == "submitted")
        check(
            "category_assignments has WEEKLY_TEMPLATE_COUNT entries",
            len(result.get("category_assignments", [])) == tbg.WEEKLY_TEMPLATE_COUNT,
        )
        check("exactly one batches.create call made", len(fake_client.batches.create_calls) == 1)
        check("state file was written", os.path.exists(tbg.BATCH_STATE_PATH))
        with open(tbg.BATCH_STATE_PATH, encoding="utf-8") as f:
            on_disk = json.load(f)
        check("on-disk state matches returned state", on_disk == result)

        # -- Second submit while still 'submitted': should be skipped -----
        fake_client_2 = _FakeClient()
        result_2 = tbg.submit_weekly_batch(openai_client=fake_client_2)
        check("second submit is skipped", "skipped" in result_2)
        check(
            "second submit made no batches.create call",
            len(fake_client_2.batches.create_calls) == 0,
        )
    finally:
        tbg.BATCH_STATE_PATH = original_state_path

if failures:
    print(f"\n{len(failures)} FAILURE(S)")
    raise SystemExit(1)
print("\nAll cases passed.")
