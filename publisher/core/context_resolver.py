"""Resolve the pipeline context from the environment, then from the config.

Why this module exists
----------------------
Inside a DCC the launcher (Pipeline Hatch) injects ``PIPELINE_*`` /
``SHOW`` / ``SEQ`` / ``SHOT`` / ``PROJECT_ROOT`` / ``PUBLISH_ROOT``, so the
context widget could read ``os.environ`` and be done. Started **standalone**
(double-click, ``python publisher/standalone.py``) there is no launcher:
every field rendered ``"Not set"`` and every publish died on
``Missing required context fields`` — the tool looked broken for the simplest
possible test case.

Rules
-----
* The environment always wins, per field. A launcher-injected context can
  therefore never be shadowed by a stale file on disk.
* ``config/publisher.yaml: standalone_context`` fills only the gaps, and only
  exists so a standalone session has something to publish.
* Roots follow the same fallback (``PROJECT_ROOT`` / ``PUBLISH_ROOT``, else the
  yaml ``project_root`` / ``publish_root``). This matters: the UI reads roots
  from this resolver while the publish service reads them from
  :class:`~publisher.core.config.settings.ConfigManager` — if the two disagree
  a publish lands in the wrong tree.

Both root values are the **parent of the shows**
(``.../y_pipeline_projects``, not ``.../y_pipeline_projects/<Show>``), because
the path builders append ``<project>/<sequence>/<shot>`` themselves.
"""

from __future__ import annotations

import os
from typing import Mapping, Optional

NOT_SET = "Not set"

#: ``TITLE_CASE`` field -> environment variables, most specific first.
ENV_KEYS: Mapping[str, tuple] = {
    "project": ("PIPELINE_PROJECT", "SHOW"),
    "sequence": ("PIPELINE_SEQUENCE", "SEQ"),
    "shot": ("PIPELINE_SHOT", "SHOT"),
    "department": ("PIPELINE_DEPARTMENT", "ROLE"),
    "dcc": ("PIPELINE_DCC",),
}

ROOT_ENV_KEYS: Mapping[str, str] = {
    "project_root": "PROJECT_ROOT",
    "publish_root": "PUBLISH_ROOT",
}

SOURCE_ENV = "env"
SOURCE_YAML = "config"
SOURCE_NONE = "none"


def _first_env(env: Mapping[str, str], keys: tuple) -> str:
    """Return the first non-empty value among *keys*."""
    for key in keys:
        value = (env.get(key) or "").strip()
        if value:
            return value
    return ""


def resolve_context(
    env: Optional[Mapping[str, str]] = None,
    config=None,
) -> dict:
    """Build the context dict the UI and the publish service both use.

    Args:
        env: Environment mapping. Defaults to ``os.environ`` (injectable so the
            resolution rules are testable without touching the real process).
        config: A ``PublisherConfig`` (anything with ``standalone_context``,
            ``project_root`` and ``publish_root`` attributes). ``None`` means
            "environment only".

    Returns:
        Dict with ``project``, ``sequence``, ``shot``, ``department``, ``dcc``,
        ``project_root``, ``publish_root`` and ``source``. Missing values are
        the literal ``"Not set"`` — the sentinel the UI already validates on.
        ``source`` is ``"env"`` (everything from the environment), ``"config"``
        (at least one field came from ``standalone_context`` / the yaml roots)
        or ``"none"`` (nothing resolved at all).
    """
    env = os.environ if env is None else env
    static = getattr(config, "standalone_context", None) or {}

    data: dict = {}
    used_fallback = False
    used_env = False

    for field, keys in ENV_KEYS.items():
        value = _first_env(env, keys)
        if value:
            used_env = True
        else:
            value = str(static.get(field, "") or "").strip()
            if value:
                used_fallback = True
        data[field] = value or NOT_SET

    if data["department"] != NOT_SET:
        data["department"] = data["department"].lower()
    if data["dcc"] != NOT_SET:
        data["dcc"] = data["dcc"].lower()

    for field, key in ROOT_ENV_KEYS.items():
        value = _first_env(env, (key,))
        if value:
            used_env = True
        else:
            value = str(getattr(config, field, "") or "").strip() if config else ""
            if value:
                used_fallback = True
        data[field] = value or NOT_SET

    if not used_env and not used_fallback:
        data["source"] = SOURCE_NONE
    elif used_fallback:
        data["source"] = SOURCE_YAML
    else:
        data["source"] = SOURCE_ENV

    return data
