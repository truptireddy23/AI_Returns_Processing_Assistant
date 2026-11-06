# Prompts

Each Markdown file contains its version, system prompt, few-shot examples, output schema
and intended settings. The backend ships a synchronized copy. Edit here, run
`make sync-prompts`, and run `test_prompts.py` to check the copies match.

| File | Step |
|---|---|
| `policy.md` | Policy eligibility grounded in active clauses |
| `image.md` | Product match, photo condition and authenticity concerns |
| `recommendation.md` | Proposed outcome, rationale and uncertainties |
| `critic.md` | Independent prompt that can add caution |
| `chat.md` | Case-specific customer assistance |

Runtime settings in `.env` override illustrative model roles in prompt documents. All
roles currently share `CHAT_MODEL`, temperature and provider configuration. Actual reply
caps live in `pipeline/model_steps.py` and `pipeline/chat_assist.py`. The critic uses a
separate prompt, not a separate provider/model family.

With `CHAT_TOOLS_ENABLED=true`, the policy client executes `search_policy` and
`check_return_window` as actual model function calls. Both are read-only, take no
arguments and stay scoped to the current return. The code still owns retrieval, math
and the final gate. Blocking window/Final Sale checks skip the policy model call.

Judgment step traces record the prompt file's version, model identity, token counts,
latency, tool calls and configured cost estimates. Chat usage appears in its reply
metadata. Missing provider usage or prices remain unknown. `CHAT_STREAM_ENABLED=true`
streams provider responses, then validates the assembled JSON before using it. The UI
streams safe step metadata rather than partial model text.
