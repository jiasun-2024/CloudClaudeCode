from app.agent import build_agent_option_payload


def test_agent_option_payload_uses_claude_code_presets() -> None:
    payload = build_agent_option_payload(cwd="/tmp/workspace", resume="sess-abc", model="claude-sonnet-4-5")

    assert payload["tools"] == {"type": "preset", "preset": "claude_code"}
    assert payload["system_prompt"] == {"type": "preset", "preset": "claude_code"}
    assert payload["setting_sources"] == ["user", "project", "local"]
    assert payload["cwd"] == "/tmp/workspace"
    assert payload["resume"] == "sess-abc"
    assert payload["model"] == "claude-sonnet-4-5"
    assert payload["permission_mode"] == "default"
