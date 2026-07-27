"""
Ad-hoc verification script for core/model_client.py's
fetch_article_via_headline_search() -- run directly with
`python tools/test_fetch_article_via_headline_search.py`. No live network
calls -- mocks the OpenAI client's responses.create().
"""
from unittest.mock import MagicMock, patch

import core.model_client as mc

failures = []


def check(label, condition):
    status = "OK" if condition else "FAIL"
    print(f"[{status}] {label}")
    if not condition:
        failures.append(label)


def _fake_response(output_text):
    resp = MagicMock()
    resp.output_text = output_text
    resp.usage = MagicMock(input_tokens=100, output_tokens=50)
    return resp


def test_returns_extracted_content_on_success():
    with patch.object(mc.client.responses, "create", return_value=_fake_response(
        "- IDFC First Bank shares rose 9.5% after posting Rs 1,075 crore Q1 profit\n"
        "- Brokerages raised target prices following the results"
    )):
        content = mc.fetch_article_via_headline_search(
            "IDFC First Bank shares surge 5% after Q1 results", "Economic Times"
        )
    check("returns the extracted bullet content", "IDFC First Bank shares rose 9.5%" in content)


test_returns_extracted_content_on_success()


def test_returns_empty_on_not_found_sentinel():
    with patch.object(mc.client.responses, "create", return_value=_fake_response("NOT_FOUND")):
        content = mc.fetch_article_via_headline_search("some headline that doesn't exist", "")
    check("NOT_FOUND sentinel converts to empty string", content == "")


test_returns_empty_on_not_found_sentinel()


def test_returns_empty_on_api_exception():
    with patch.object(mc.client.responses, "create", side_effect=Exception("API error")):
        content = mc.fetch_article_via_headline_search("some headline", "")
    check("API exception returns empty string, not a raised error", content == "")


test_returns_empty_on_api_exception()

if failures:
    print(f"\n{len(failures)} FAILURE(S)")
    raise SystemExit(1)
print("\nAll cases passed.")
