# Prompts

Version-controlled prompts for every model step in the pipeline (added in M5–M6).

Each step gets one Markdown file whose first line is `version: N`, followed by its system
prompt and few-shot examples, plus a JSON Schema for the step's output and its model
settings (role, temperature, max tokens). The version is logged with every model call.

| File (planned) | Step | Model role |
|---|---|---|
| `policy.md` | Policy eligibility, with policy search tools | `reason` |
| `image.md` | Photo match and condition | `vision` |
| `recommendation.md` | Approve / deny / escalate, with rationale | `reason` |
| `critic.md` | Independent check that can only add caution | `critic` |
