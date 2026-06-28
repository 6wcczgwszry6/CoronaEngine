from __future__ import annotations


def load_scene_tools(*args, **kwargs):
    from .scene_tools import load_scene_tools as _load_scene_tools

    return _load_scene_tools(*args, **kwargs)


__all__ = ["load_scene_tools"]
