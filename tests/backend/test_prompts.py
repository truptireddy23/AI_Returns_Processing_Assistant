"""The prompts the API ships with match app/prompts/, the version-controlled source.

The API deploys from app/backend only (Vercel's root directory, Docker's build
context), so it reads a copy packaged inside `returnguard`. Production once failed
every model-backed review with FileNotFoundError because only app/prompts/ existed.
"""

from pathlib import Path

import pytest

from returnguard.pipeline import chat_assist, model_steps

SOURCE_DIR = Path(__file__).resolve().parents[2] / "app" / "prompts"
PACKAGED_DIR = model_steps._PROMPTS_DIR
STEP_PROMPTS = sorted(p.name for p in SOURCE_DIR.glob("*.md") if p.name != "README.md")


def test_the_packaged_prompts_live_inside_the_backend_package() -> None:
    backend_src = Path(model_steps.__file__).resolve().parents[2]
    assert PACKAGED_DIR.is_relative_to(backend_src)
    assert chat_assist._PROMPTS_DIR == PACKAGED_DIR


def test_every_step_prompt_is_packaged() -> None:
    packaged = sorted(p.name for p in PACKAGED_DIR.glob("*.md") if p.name != "README.md")
    assert packaged == STEP_PROMPTS, "run `make sync-prompts`"


@pytest.mark.parametrize("name", STEP_PROMPTS)
def test_packaged_prompt_matches_the_source(name: str) -> None:
    assert (PACKAGED_DIR / name).read_text() == (SOURCE_DIR / name).read_text(), (
        f"{name} differs from app/prompts/{name}: run `make sync-prompts`"
    )


@pytest.mark.parametrize("name", STEP_PROMPTS)
def test_each_step_loads_its_system_prompt_from_the_package(name: str) -> None:
    assert model_steps._load_system_prompt(name).strip()
