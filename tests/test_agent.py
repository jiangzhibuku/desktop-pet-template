from __future__ import annotations

from desktop_pet.agent import TOOLS, Agent
from desktop_pet.config import ApiConfig, Config
from desktop_pet.paths import build_paths


def make_agent(tmp_path, **api_kwargs):
    root = tmp_path / "repo"
    (root / "assets" / "characters").mkdir(parents=True)
    paths = build_paths(root=root, data=tmp_path / "data")
    cfg = Config(api=ApiConfig(**api_kwargs))
    return Agent(cfg, paths), paths


def test_every_declared_tool_is_implemented(tmp_path):
    agent, _ = make_agent(tmp_path)
    declared = {tool["function"]["name"] for tool in TOOLS}

    assert declared == set(agent._tool_map)


def test_offline_chat_points_at_config_file(tmp_path):
    agent, paths = make_agent(tmp_path)

    reply = agent.chat("你好")

    assert "API Key" in reply
    assert str(paths.config) in reply


def test_todo_roundtrip(tmp_path):
    agent, paths = make_agent(tmp_path)

    assert "已添加" in agent._todo("add", "买牛奶")
    assert "买牛奶" in agent._todo("list")
    assert "已完成" in agent._todo("done", "1")
    assert agent._todo("list") == "待办清单是空的"
    assert paths.todos.is_file()


def test_remember_persists_across_agents(tmp_path):
    agent, paths = make_agent(tmp_path)
    agent._remember("称呼", "小姜")

    second = Agent(agent.config, paths)
    assert second.memory_store.load() == {"称呼": "小姜"}


def test_feed_and_status(tmp_path):
    agent, _ = make_agent(tmp_path)

    agent._feed()
    agent._feed()
    status = agent._pet_status()

    assert "Lv.1" in status
    assert "喂食 2 次" in status
    assert agent.stats_store.load()["exp"] == 30


def test_app_whitelist_roundtrip(tmp_path):
    agent, _ = make_agent(tmp_path)

    assert "已添加" in agent.add_app("测试应用", "notepad")
    assert "测试应用" in agent.user_apps
    assert "已移除" in agent.remove_app("测试应用")
    assert "测试应用" not in agent.user_apps
    assert "内置应用不能删除" in agent.remove_app("记事本")


def test_open_url_rejects_non_http(tmp_path, monkeypatch):
    agent, _ = make_agent(tmp_path)
    opened = []
    monkeypatch.setattr("webbrowser.open", lambda url: opened.append(url))

    assert "只支持" in agent._open_url("file:///etc/passwd")
    assert opened == []


def test_trim_history_never_starts_with_orphans(tmp_path):
    agent, _ = make_agent(tmp_path)
    agent.config.agent.history_limit = 4
    agent.messages = [
        {"role": "user", "content": "a"},
        {"role": "assistant", "content": "", "tool_calls": [{"id": "1"}]},
        {"role": "tool", "tool_call_id": "1", "content": "ok"},
        {"role": "assistant", "content": "b"},
        {"role": "user", "content": "c"},
        {"role": "assistant", "content": "d"},
    ]

    agent._trim_history()

    assert agent.messages[0]["role"] != "tool"
    assert not (
        agent.messages[0]["role"] == "assistant" and agent.messages[0].get("tool_calls")
    )
    assert len(agent.messages) <= 4
