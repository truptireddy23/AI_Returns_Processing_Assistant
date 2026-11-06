# Packaged prompts

A copy of `app/prompts/*.md`, shipped inside the `returnguard` package so the deployed API
(Vercel and Docker deploy only `app/backend`) can read them. `app/prompts/` is the source of
truth: edit there, then run `make sync-prompts`. `tests/backend/test_prompts.py` fails if the
two copies differ.
