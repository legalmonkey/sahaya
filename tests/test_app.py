"""Unit tests for the Sahaya HTTP application server endpoints."""
from __future__ import annotations

import json
import sqlite3
import unittest
from http import HTTPStatus
from io import BytesIO
from unittest.mock import MagicMock

from app import Handler, PRIORITIZER


class DummyServer:
    pass


class AppEndpointTests(unittest.TestCase):
    def setUp(self):
        self.handler = Handler.__new__(Handler)
        self.handler.server = DummyServer()
        self.handler.wfile = BytesIO()
        self.handler.headers = {}

    def _setup_request(self, method: str, path: str, body: dict | None = None):
        self.handler.command = method
        self.handler.path = path
        if body is not None:
            raw = json.dumps(body).encode("utf-8")
            self.handler.rfile = BytesIO(raw)
            self.handler.headers["Content-Length"] = str(len(raw))
        else:
            self.handler.rfile = BytesIO()
        self.handler.send_response = MagicMock()
        self.handler.send_header = MagicMock()
        self.handler.end_headers = MagicMock()

    def test_get_root_returns_html(self):
        self._setup_request("GET", "/")
        self.handler.do_GET()
        self.handler.send_response.assert_called_with(HTTPStatus.OK)
        output = self.handler.wfile.getvalue().decode("utf-8")
        self.assertIn("सहया • Sahaya", output)
        self.assertIn("households-view", output)
        self.assertIn("detail-view", output)
        self.assertIn("voice-sheet", output)

    def test_get_households_api(self):
        self._setup_request("GET", "/api/households")
        self.handler.do_GET()
        self.handler.send_response.assert_called_with(HTTPStatus.OK)
        res = json.loads(self.handler.wfile.getvalue().decode("utf-8"))
        self.assertIn("households", res)
        self.assertIsInstance(res["households"], list)

    def test_refresh_prioritize_api(self):
        self._setup_request("POST", "/api/prioritize/refresh")
        self.handler.do_POST()
        self.handler.send_response.assert_called_with(HTTPStatus.OK)
        res = json.loads(self.handler.wfile.getvalue().decode("utf-8"))
        self.assertTrue(res.get("success"))
        self.assertIn("households", res)

    def test_ask_without_model_configured_returns_strict_error(self):
        # Strict adherence to no-mock, no-fallback principle
        self._setup_request("POST", "/api/ask", {"query": "When are OPV doses scheduled?"})
        self.handler.do_POST()
        self.handler.send_response.assert_called_with(HTTPStatus.UNPROCESSABLE_ENTITY)
        res = json.loads(self.handler.wfile.getvalue().decode("utf-8"))
        self.assertIn("error", res)
        self.assertIn("Local Gemma GGUF is not configured", res["error"])


if __name__ == "__main__":
    unittest.main()
