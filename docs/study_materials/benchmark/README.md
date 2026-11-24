# ReturnGuard benchmark (Checkpoint 4, Track B)

32 synthetic, hand-labelled return cases in 13 categories (`cases.json`), run through the
production pipeline and governance gate.

## Reproduce

Needs local Postgres with pgvector (`make up`) and a `CHAT_API_KEY` in `app/.env`. From `app/`:

```bash
make benchmark-photos                                   # team members: photos not in git
make benchmark VARIANT=rules                            # no model calls
make benchmark VARIANT=model ARGS="--max-model-cases 28"  # resumable; stops at the quota
make benchmark-report                                   # summary.json, RESULTS.md, docs/figures/
```

Keep the machine awake (macOS: prefix with `caffeinate -i`). `make benchmark-report` alone
reproduces every number in the report from the committed `results/*.jsonl`.

## Photo provenance

No photo was taken by a customer or by the team for this benchmark.

| File | Source | In git |
|---|---|---|
| `sole_separation_real.jpg` | Checkpoint 2 `IMG-B`: web image, original source not recorded | yes |
| `normal_wear_real.jpg` | Checkpoint 2 `IMG-C`: web image, original source not recorded | yes |
| `torn_upper_ai_generated.jpg` | Checkpoint 2 `IMG-F`: generated with Gemini | yes |
| `clean_shoes_iphone.jpg` | Checkpoint 2 `IMG-A` (web image) with **script-written iPhone metadata** | yes |
| `sole_separation_photoshop_edited.jpg` | `IMG-B` with **script-written Adobe Photoshop metadata**; pixels not edited | yes |
| `court_shoe_catalog_reused.jpg`, `catalog/` | Store catalog photos (third-party images) from the private bucket | no |
| `red_cookware_wrong_item.jpg` | A teammate's test upload, from the private bucket | no |

`IMG-A/B/C/F` show Nike Air Force 1 shoes; the catalog photo for FW-002 shows a similar white
leather shoe of a different model. The labels treat them as the same kind of product.

## Known limits of the labels and data

- Labels were drafted by one team member with AI assistance (the same AI tool that wrote the
  runner) before any model run, and were not changed after seeing results.
- A second, independent labelling is pending. Label `labels_second_rater.csv` without opening
  `cases.json` results or the `expected` fields.
- `IMG-A/B/C/F` were used while developing version 2 of the image prompt, so the photo cases
  that use them are **not held out**.
- `nad-material` and `photo-photoshop-meta` list "approve" as an acceptable AI proposal but
  expect a person as the route. Both are kept as labelled.
- 7 photos serve 11 photo cases, so those cases are not independent.

## Run notes (AI pipeline, 23 November 2026)

- One run per case; run-to-run consistency has not been measured.
- The laptop slept several times. `defect-real-sole` spans a sleep, so it is excluded from the
  latency figures (its outcome is kept).
- `wear-soles` failed once with a network error after a sleep; that row was removed and the case
  rerun. An earlier run with an invalid API key produced no model output and was discarded.
- Cases ran one at a time on Groq's free tier, so latency includes waiting for the
  tokens-per-minute limit and does not describe model speed.
