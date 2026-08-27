from __future__ import annotations

import importlib

import pytest

VCS_REF = "fff85944723a67d4b1e9daa952a8e43d80b4cacb"
DIGEST = "sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
REPO = "rhoai/odh-workbench-jupyter-minimal-cpu-py312-rhel9"


def load_generator():
    try:
        return importlib.import_module("manifests.tools.generate_envs")
    except ModuleNotFoundError as exc:
        pytest.fail(f"Missing generate_envs implementation module: {exc}")


def test_commit_env_persists_full_vcs_ref(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]):
    gen = load_generator()

    def fake_get_json(url: str) -> dict:
        if url.startswith(f"{gen.API_BASE}/repositories?"):
            return {"data": [{"repository": REPO}]}
        return {
            "data": [
                {
                    "repositories": [{"manifest_list_digest": DIGEST}],
                    "parsed_data": {"labels": [{"name": "vcs-ref", "value": VCS_REF}]},
                }
            ]
        }

    monkeypatch.setattr(gen, "get_json", fake_get_json)
    gen.main(version_tag="v3.3", suffix="2025-2")

    out = capsys.readouterr().out

    # params.env digest line is unchanged
    assert (f"odh-workbench-jupyter-minimal-cpu-py312-ubi9-2025-2=registry.redhat.io/{REPO}@{DIGEST}") in out
    # commit.env section must persist the full vcs-ref, not a truncated prefix
    commit_section = out.split("=== commit.env ===", maxsplit=1)[1]
    commit_lines = [line for line in commit_section.splitlines() if line.strip()]
    assert commit_lines == ["odh-workbench-jupyter-minimal-cpu-py312-ubi9-commit-2025-2=" + VCS_REF]
