#!/usr/bin/env python3
"""Tests for save_llm_response.py. Run: python3 test_save_llm_response.py"""

from __future__ import annotations

import io
import json
import sqlite3
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import save_llm_response as slr


def claude_assistant(text=None, thinking=False, tool_use=False, sidechain=False):
    content = []
    if thinking:
        content.append({"type": "thinking", "thinking": "..."})
    if tool_use:
        content.append({"type": "tool_use", "id": "t1", "name": "Bash", "input": {}})
    if text is not None:
        content.append({"type": "text", "text": text})
    return {
        "type": "assistant",
        "isSidechain": sidechain,
        "message": {"role": "assistant", "content": content},
    }


def claude_user(text):
    return {"type": "user", "isSidechain": False, "message": {"role": "user", "content": text}}


def claude_tool_result():
    return {
        "type": "user",
        "isSidechain": False,
        "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t1", "content": "ok"}]},
    }


class SlugifyTests(unittest.TestCase):
    def test_heading_preferred(self):
        self.assertEqual(slr.slugify("# MCP Frequent List\n\nbody"), "mcp-frequent-list")

    def test_punctuation_and_word_cap(self):
        self.assertEqual(
            slr.slugify("Hello, World! This is a fairly long title about nothing"),
            "hello-world-this-is-a-fairly",
        )

    def test_empty(self):
        self.assertEqual(slr.slugify("   "), "response")


class ExtractorTests(unittest.TestCase):
    def test_claude_skips_thinking_tools_and_current_user(self):
        records = [
            claude_user("explain the pipeline"),
            claude_assistant(thinking=True, tool_use=True),
            claude_tool_result(),
            claude_assistant(text="The pipeline has three rules."),
            claude_user("/save-last"),
        ]
        self.assertEqual(slr.claude_last_text(records), "The pipeline has three rules.")

    def test_claude_concatenates_and_ignores_sidechain(self):
        records = [
            claude_user("go"),
            claude_assistant(text="First."),
            claude_assistant(thinking=True, tool_use=True),
            claude_tool_result(),
            claude_assistant(text="Second."),
            claude_assistant(text="Subagent chatter.", sidechain=True),
        ]
        self.assertEqual(slr.claude_last_text(records), "First.\n\nSecond.")

    def test_grok_skips_synthetic_and_tools(self):
        records = [
            {"type": "system", "content": "You are Grok"},
            {"type": "user", "content": [{"type": "text", "text": "<user_query>\nexplain\n</user_query>"}]},
            {"type": "assistant", "content": "", "tool_calls": [{"name": "Bash"}]},
            {"type": "tool_result", "content": "ok"},
            {"type": "user", "synthetic_reason": "skills", "content": [{"type": "text", "text": "skills list"}]},
            {"type": "assistant", "content": "Grok answer about liftOver."},
            {"type": "user", "content": [{"type": "text", "text": "<user_query>\n/save-last\n</user_query>"}]},
        ]
        self.assertEqual(slr.grok_last_text(records), "Grok answer about liftOver.")

    def test_codex_assistant_output_text(self):
        records = [
            {"type": "session_meta", "payload": {"cwd": "/tmp/proj"}},
            {
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": "hi"}],
                },
            },
            {
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": "Codex reply."}],
                },
            },
        ]
        self.assertEqual(slr.codex_last_text(records), "Codex reply.")

    def test_sniff(self):
        self.assertEqual(slr.sniff_jsonl([{"type": "session_meta", "payload": {}}]), "codex")
        self.assertEqual(slr.sniff_jsonl([{"type": "assistant", "content": "hi"}]), "grok")
        self.assertEqual(slr.sniff_jsonl([{"type": "user", "message": {"content": "x"}, "sessionId": "a"}]), "claude")


class OpenCodeTests(unittest.TestCase):
    def test_opencode_sql(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "opencode.db"
            con = sqlite3.connect(db)
            con.executescript(
                """
                CREATE TABLE session (id TEXT, directory TEXT, time_updated INTEGER);
                CREATE TABLE message (id TEXT, session_id TEXT, time_created INTEGER, data TEXT);
                CREATE TABLE part (id TEXT, message_id TEXT, session_id TEXT, time_created INTEGER, data TEXT);
                """
            )
            con.execute("INSERT INTO session VALUES ('s1', ?, 2)", (tmp,))
            con.execute(
                "INSERT INTO message VALUES ('m1', 's1', 1, ?)",
                (json.dumps({"role": "user"}),),
            )
            con.execute(
                "INSERT INTO message VALUES ('m2', 's1', 2, ?)",
                (json.dumps({"role": "assistant"}),),
            )
            con.execute(
                "INSERT INTO part VALUES ('p1', 'm2', 's1', 2, ?)",
                (json.dumps({"type": "text", "text": "OpenCode answer."}),),
            )
            con.commit()
            con.close()
            with patch.object(slr, "opencode_db_path", return_value=db):
                self.assertEqual(slr.opencode_last_text(tmp), "OpenCode answer.")


class HookTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cwd = Path(self.tmp.name) / "proj"
        self.cwd.mkdir()
        self.transcript = Path(self.tmp.name) / "session.jsonl"
        self.markers = Path(self.tmp.name) / "markers"
        self.markers.mkdir()
        self.state = Path(self.tmp.name) / "state"
        self.state.mkdir()
        self._patches = [
            patch.object(slr, "MARKER_DIR", self.markers),
            patch.object(slr, "STATE_DIR", self.state),
            patch.object(slr, "DEDUP_PATH", self.state / "last-save.json"),
        ]
        for item in self._patches:
            item.start()

    def tearDown(self):
        for item in self._patches:
            item.stop()
        self.tmp.cleanup()

    def _write_transcript(self, records):
        with self.transcript.open("w", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(record) + "\n")

    def _run(self, payload):
        buf = io.StringIO()
        with redirect_stdout(buf):
            try:
                slr.dispatch(payload)
            except SystemExit as exc:
                code = exc.code if isinstance(exc.code, int) else 0
            else:
                code = 0
        raw = buf.getvalue()
        parsed = json.loads(raw) if raw.strip() else None
        return code, parsed

    def test_save_last_writes_file_and_blocks(self):
        body = "Previous answer about MCP frequent list."
        self._write_transcript([claude_user("what?"), claude_assistant(text=body)])
        code, out = self._run(
            {
                "hook_event_name": "UserPromptExpansion",
                "command_name": "save-last",
                "command_args": "",
                "cwd": str(self.cwd),
                "transcript_path": str(self.transcript),
                "session_id": "s1",
            }
        )
        self.assertEqual(code, 0)
        self.assertEqual(out["decision"], "block")
        saved = Path(out["reason"].split("Saved to ", 1)[1])
        self.assertTrue(saved.is_file())
        text = saved.read_text(encoding="utf-8")
        self.assertIn(body, text)
        self.assertIn("source: \"save-last (previous assistant turn)\"", text)

    def test_grok_prompt_submit_camel_case(self):
        body = "Grok previous reply."
        self._write_transcript(
            [
                {"type": "user", "content": "q"},
                {"type": "assistant", "content": body},
            ]
        )
        code, out = self._run(
            {
                "hookEventName": "user_prompt_submit",
                "prompt": "/save-last",
                "cwd": str(self.cwd),
                "sessionId": "g1",
                "transcriptPath": str(self.transcript),
            }
        )
        self.assertEqual(code, 0)
        self.assertEqual(out["decision"], "block")
        saved = Path(out["reason"].split("Saved to ", 1)[1])
        self.assertIn(body, saved.read_text(encoding="utf-8"))

    def test_save_last_empty_turn_blocks_without_file(self):
        self._write_transcript([claude_user("go"), claude_assistant(thinking=True)])
        code, out = self._run(
            {
                "hook_event_name": "UserPromptExpansion",
                "command_name": "save-last",
                "cwd": str(self.cwd),
                "transcript_path": str(self.transcript),
                "session_id": "s1",
            }
        )
        self.assertEqual(out["decision"], "block")
        self.assertIn("No previous assistant reply", out["reason"])
        self.assertFalse((self.cwd / "docs" / "llm_responses").exists())

    def test_save_response_requires_args(self):
        code, out = self._run(
            {
                "hook_event_name": "UserPromptExpansion",
                "command_name": "save-response",
                "command_args": "  ",
                "cwd": str(self.cwd),
                "session_id": "s2",
            }
        )
        self.assertIn("Usage:", out["reason"])

    def test_save_response_stop_camel_case(self):
        self._run(
            {
                "hookEventName": "UserPromptExpansion",
                "commandName": "save-response",
                "commandArgs": "What is liftOver?",
                "cwd": str(self.cwd),
                "sessionId": "sess-99",
            }
        )
        code, out = self._run(
            {
                "hookEventName": "stop",
                "sessionId": "sess-99",
                "cwd": str(self.cwd),
                "lastAssistantMessage": "liftOver converts coordinates between genome builds.",
                "backgroundTasks": [],
                "reason": "end_turn",
            }
        )
        self.assertEqual(code, 0)
        saved = Path(out["systemMessage"].split("Saved to ", 1)[1])
        text = saved.read_text(encoding="utf-8")
        self.assertIn("What is liftOver?", text)
        self.assertIn("liftOver converts coordinates", text)
        self.assertFalse(slr.marker_path("sess-99").exists())

    def test_stop_skips_session_end_reason(self):
        slr.marker_path("bg").write_text(json.dumps({"cwd": str(self.cwd), "question": "q"}), encoding="utf-8")
        code, out = self._run(
            {
                "hookEventName": "stop",
                "sessionId": "bg",
                "reason": "shutdown",
                "lastAssistantMessage": "bye",
                "cwd": str(self.cwd),
            }
        )
        self.assertEqual(code, 0)
        self.assertIsNone(out)
        self.assertTrue(slr.marker_path("bg").is_file())

    def test_stop_without_marker_is_silent(self):
        code, out = self._run({"hook_event_name": "Stop", "session_id": "no-marker", "last_assistant_message": "hello"})
        self.assertEqual(code, 0)
        self.assertIsNone(out)

    def test_dedup_same_body(self):
        body = "Same body twice."
        self._write_transcript([claude_user("q"), claude_assistant(text=body)])
        payload = {
            "hook_event_name": "UserPromptExpansion",
            "command_name": "save-last",
            "cwd": str(self.cwd),
            "transcript_path": str(self.transcript),
            "session_id": "d1",
        }
        _, out1 = self._run(payload)
        _, out2 = self._run(payload)
        self.assertEqual(out1["reason"], out2["reason"])

    def test_cli_last(self):
        body = "CLI extracted reply."
        self._write_transcript([claude_user("q"), claude_assistant(text=body)])
        buf = io.StringIO()
        with redirect_stdout(buf):
            slr.cli(
                [
                    "last",
                    "--cwd",
                    str(self.cwd),
                    "--transcript",
                    str(self.transcript),
                    "--harness",
                    "claude",
                ]
            )
        path = Path(buf.getvalue().strip())
        self.assertTrue(path.is_file())
        self.assertIn(body, path.read_text(encoding="utf-8"))


class StdinMainTests(unittest.TestCase):
    def test_main_empty_stdin(self):
        with patch("sys.argv", ["save_llm_response.py"]), patch("sys.stdin", io.StringIO("")):
            with self.assertRaises(SystemExit) as exc:
                slr.main()
            self.assertEqual(exc.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
