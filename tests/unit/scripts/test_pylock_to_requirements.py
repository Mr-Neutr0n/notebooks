from __future__ import annotations

import importlib.util
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_MODULE_PATH = _REPO_ROOT / "scripts" / "lockfile-generators" / "helpers" / "pylock-to-requirements.py"
_SPEC = importlib.util.spec_from_file_location("pylock_to_requirements", _MODULE_PATH)
assert _SPEC is not None
assert _SPEC.loader is not None
helper = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(helper)


def test_extract_default_index_from_pylock_strips_format_json(tmp_path: Path) -> None:
    pylock_path = tmp_path / "pylock.toml"
    pylock_path.write_text(
        "# uv pip compile --default-index=https://example.invalid/simple/?format=json\n",
        encoding="utf-8",
    )

    assert helper.extract_default_index_from_pylock(pylock_path) == "https://example.invalid/simple/"


def test_wheel_is_el9_compatible() -> None:
    assert helper.wheel_is_el9_compatible(
        "https://example.invalid/uv-0.12.5-py3-none-manylinux_2_17_x86_64.manylinux2014_x86_64.whl"
    )
    assert helper.wheel_is_el9_compatible("pkg-1.0-py3-none-any.whl")
    assert helper.wheel_is_el9_compatible("pkg-1.0-cp312-cp312-manylinux2010_x86_64.whl")
    assert helper.wheel_is_el9_compatible("pkg-1.0-cp312-cp312-manylinux_2_34_x86_64.whl")
    assert not helper.wheel_is_el9_compatible("pkg-1.0-cp312-cp312-manylinux_2_35_x86_64.whl")
    assert not helper.wheel_is_el9_compatible("ripgrep-15.1.0-py3-none-manylinux_2_39_x86_64.whl")
    assert not helper.wheel_is_el9_compatible("pkg-1.0-py3-none-musllinux_1_1_x86_64.whl")
    assert not helper.wheel_is_el9_compatible("manylinux2010_helper-1.0-cp312-cp312-manylinux_2_39_x86_64.whl")
    assert not helper.wheel_is_el9_compatible("not-a-wheel.tar.gz")


def test_collect_index_hashes_omits_sdist_when_el9_wheel_exists() -> None:
    pkg = {
        "wheels": [
            {
                "url": "https://example.invalid/uv-0.12.5-py3-none-manylinux_2_17_x86_64.whl",
                "hashes": {"sha256": "wheelhash"},
            }
        ],
        "sdist": {
            "url": "https://example.invalid/uv-0.12.5.tar.gz",
            "hashes": {"sha256": "sdisthash"},
        },
    }
    assert helper.collect_index_hashes(pkg) == ["--hash=sha256:wheelhash"]


def test_collect_index_hashes_keeps_sdist_without_el9_wheel() -> None:
    pkg = {
        "wheels": [
            {
                "url": "https://example.invalid/ripgrep-15.1.0-py3-none-manylinux_2_39_x86_64.whl",
                "hashes": {"sha256": "wheelhash"},
            }
        ],
        "sdist": {
            "url": "https://example.invalid/ripgrep-15.1.0.tar.gz",
            "hashes": {"sha256": "sdisthash"},
        },
    }
    assert helper.collect_index_hashes(pkg) == [
        "--hash=sha256:wheelhash",
        "--hash=sha256:sdisthash",
    ]


def test_collect_index_hashes_omits_sdist_if_any_el9_wheel_exists() -> None:
    """A too-new amd64 wheel must not hide an EL9 aarch64 wheel (or vice versa)."""
    pkg = {
        "wheels": [
            {
                "url": "https://example.invalid/pkg-1.0-py3-none-manylinux_2_39_x86_64.whl",
                "hashes": {"sha256": "newamd64"},
            },
            {
                "url": "https://example.invalid/pkg-1.0-py3-none-manylinux_2_17_aarch64.whl",
                "hashes": {"sha256": "el9arm"},
            },
        ],
        "sdist": {
            "url": "https://example.invalid/pkg-1.0.tar.gz",
            "hashes": {"sha256": "sdisthash"},
        },
    }
    assert helper.collect_index_hashes(pkg) == [
        "--hash=sha256:newamd64",
        "--hash=sha256:el9arm",
    ]


def test_collect_index_hashes_sdist_only() -> None:
    pkg = {
        "sdist": {
            "url": "https://example.invalid/pkg-1.0.tar.gz",
            "hashes": {"sha256": "sdisthash"},
        }
    }
    assert helper.collect_index_hashes(pkg) == ["--hash=sha256:sdisthash"]


def test_wheel_el9_arches() -> None:
    assert helper.wheel_el9_arches("pkg-1.0-py3-none-any.whl") == helper.KONFLUX_EL9_ARCHES
    assert helper.wheel_el9_arches(
        "https://example.invalid/uv-0.12.5-py3-none-manylinux_2_17_x86_64.manylinux2014_x86_64.whl"
    ) == frozenset({"x86_64"})
    assert helper.wheel_el9_arches(
        "uv-0.12.5-py3-none-manylinux_2_17_aarch64.manylinux2014_aarch64.musllinux_1_1_aarch64.whl"
    ) == frozenset({"aarch64"})
    assert helper.wheel_el9_arches("pkg-1.0-cp312-cp312-manylinux_2_17_ppc64le.whl") == frozenset({"ppc64le"})
    assert helper.wheel_el9_arches("pkg-1.0-cp312-cp312-manylinux2014_s390x.whl") == frozenset({"s390x"})
    assert helper.wheel_el9_arches("pkg-1.0-cp312-cp312-manylinux_2_17_armv7l.whl") == frozenset()
    assert helper.wheel_el9_arches("pkg-1.0-py3-none-musllinux_1_1_x86_64.whl") == frozenset()
    assert helper.wheel_el9_arches("ripgrep-15.1.0-py3-none-manylinux_2_39_x86_64.whl") == frozenset()
    assert helper.wheel_el9_arches("not-a-wheel.tar.gz") == frozenset()


def test_konflux_arches_required() -> None:
    assert helper.konflux_arches_required("") == helper.KONFLUX_EL9_ARCHES
    assert helper.konflux_arches_required("implementation_name == 'cpython' and sys_platform == 'linux'") == (
        helper.KONFLUX_EL9_ARCHES
    )
    assert helper.konflux_arches_required(
        "(platform_machine == 'aarch64' and sys_platform == 'linux') or "
        "(platform_machine == 'x86_64' and sys_platform == 'linux')"
    ) == frozenset({"x86_64", "aarch64"})
    assert helper.konflux_arches_required('platform_machine == "s390x"') == frozenset({"s390x"})


def test_collect_index_hashes_prefer_includes_sdist_when_el9_wheel_exists() -> None:
    """A single-arch EL9 wheel must not drop the sdist (ppc64le/s390x still need it)."""
    pkg = {
        "wheels": [
            {
                "url": "https://example.invalid/uv-0.12.5-py3-none-manylinux_2_17_x86_64.whl",
                "hashes": {"sha256": "wheelhash"},
            }
        ],
        "sdist": {
            "url": "https://example.invalid/uv-0.12.5.tar.gz",
            "hashes": {"sha256": "sdisthash"},
        },
    }
    assert helper.collect_index_hashes(pkg, sdist_hashes=helper.SDIST_HASHES_PREFER) == [
        "--hash=sha256:wheelhash",
        "--hash=sha256:sdisthash",
    ]


def test_collect_index_hashes_prefer_omits_sdist_when_all_konflux_arches_have_el9_wheels() -> None:
    """uv/rpds-py publish EL9 wheels for all four Konflux arches; their sdists break cargo vendor."""
    pkg = {
        "wheels": [
            {
                "url": "https://example.invalid/uv-0.12.5-py3-none-manylinux_2_17_x86_64.whl",
                "hashes": {"sha256": "amd64"},
            },
            {
                "url": "https://example.invalid/uv-0.12.5-py3-none-manylinux_2_17_aarch64.whl",
                "hashes": {"sha256": "arm64"},
            },
            {
                "url": "https://example.invalid/uv-0.12.5-py3-none-manylinux_2_17_ppc64le.whl",
                "hashes": {"sha256": "ppc"},
            },
            {
                "url": "https://example.invalid/uv-0.12.5-py3-none-manylinux_2_17_s390x.whl",
                "hashes": {"sha256": "s390"},
            },
        ],
        "sdist": {
            "url": "https://example.invalid/uv-0.12.5.tar.gz",
            "hashes": {"sha256": "sdisthash"},
        },
    }
    assert helper.collect_index_hashes(pkg, sdist_hashes=helper.SDIST_HASHES_PREFER) == [
        "--hash=sha256:amd64",
        "--hash=sha256:arm64",
        "--hash=sha256:ppc",
        "--hash=sha256:s390",
    ]


def test_collect_index_hashes_prefer_omits_sdist_for_py3_none_any() -> None:
    pkg = {
        "wheels": [
            {
                "url": "https://example.invalid/pkg-1.0-py3-none-any.whl",
                "hashes": {"sha256": "wheelhash"},
            }
        ],
        "sdist": {
            "url": "https://example.invalid/pkg-1.0.tar.gz",
            "hashes": {"sha256": "sdisthash"},
        },
    }
    assert helper.collect_index_hashes(pkg, sdist_hashes=helper.SDIST_HASHES_PREFER) == [
        "--hash=sha256:wheelhash",
    ]


def test_collect_index_hashes_prefer_keeps_sdist_when_x86_64_and_aarch64_only() -> None:
    """Ungated packages still need the sdist when ppc64le/s390x have no EL9 wheel."""
    pkg = {
        "wheels": [
            {
                "url": "https://example.invalid/pkg-1.0-cp312-cp312-manylinux_2_17_x86_64.whl",
                "hashes": {"sha256": "amd64"},
            },
            {
                "url": "https://example.invalid/pkg-1.0-cp312-cp312-manylinux_2_17_aarch64.whl",
                "hashes": {"sha256": "arm64"},
            },
        ],
        "sdist": {
            "url": "https://example.invalid/pkg-1.0.tar.gz",
            "hashes": {"sha256": "sdisthash"},
        },
    }
    assert helper.collect_index_hashes(pkg, sdist_hashes=helper.SDIST_HASHES_PREFER) == [
        "--hash=sha256:amd64",
        "--hash=sha256:arm64",
        "--hash=sha256:sdisthash",
    ]


def test_collect_index_hashes_prefer_omits_sdist_when_marker_arches_have_el9_wheels() -> None:
    """Marker-gated rpds-py (x86_64+aarch64 only) must not pull a Cargo sdist."""
    pkg = {
        "marker": (
            "(platform_machine == 'aarch64' and sys_platform == 'linux') or "
            "(platform_machine == 'x86_64' and sys_platform == 'linux')"
        ),
        "wheels": [
            {
                "url": "https://example.invalid/rpds_py-1.0-cp312-cp312-manylinux_2_17_x86_64.whl",
                "hashes": {"sha256": "amd64"},
            },
            {
                "url": "https://example.invalid/rpds_py-1.0-cp312-cp312-manylinux_2_17_aarch64.whl",
                "hashes": {"sha256": "arm64"},
            },
        ],
        "sdist": {
            "url": "https://example.invalid/rpds_py-1.0.tar.gz",
            "hashes": {"sha256": "sdisthash"},
        },
    }
    assert helper.collect_index_hashes(pkg, sdist_hashes=helper.SDIST_HASHES_PREFER) == [
        "--hash=sha256:amd64",
        "--hash=sha256:arm64",
    ]


def test_collect_index_hashes_prefer_sdist_only() -> None:
    pkg = {
        "sdist": {
            "url": "https://example.invalid/pkg-1.0.tar.gz",
            "hashes": {"sha256": "sdisthash"},
        }
    }
    assert helper.collect_index_hashes(pkg, sdist_hashes=helper.SDIST_HASHES_PREFER) == [
        "--hash=sha256:sdisthash",
    ]
