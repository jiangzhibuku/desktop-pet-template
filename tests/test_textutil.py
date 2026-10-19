from __future__ import annotations

from desktop_pet.textutil import wrap_text


def test_wrap_chinese_by_character_count():
    lines = wrap_text("今天也要好好休息呀不许熬夜", limit=5)
    assert lines == ["今天也要好", "好休息呀不", "许熬夜"]
    assert all(len(line) <= 5 for line in lines)


def test_wrap_keeps_explicit_newlines():
    assert wrap_text("第一行\n第二行", limit=10) == ["第一行", "第二行"]


def test_wrap_long_ascii_word():
    lines = wrap_text("abcdefghijklmnop", limit=6)
    assert lines == ["abcdef", "ghijkl", "mnop"]


def test_wrap_empty_text():
    assert wrap_text("", limit=10) == [""]
    assert wrap_text(None, limit=10) == [""]
