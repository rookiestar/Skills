# Output Contract

This skill has two separate layers:

1. Strict lookup output
2. Optional learning expansion

Only the strict lookup output is active today.

## Strict Lookup Output

The model must call `scripts/dict_lookup.py --format text` once and return the script output exactly.

Allowed sections:

- Header: `**word**` or `**中文词**`
- Phonetic line
- Meaning line
- Optional second meaning line
- Optional example line

Forbidden in strict output:

- Greeting or acknowledgement
- Memory tips
- Root or affix analysis
- Common collocations
- Confusable-word explanation
- Closing question
- Any model-written extra paragraph

The validator is `scripts/validate_lookup_output.py`. Deployment runs real lookups through this validator before promoting a release.

## Learning Expansion

Expansion can be useful for middle-school students, but it must not be free-form model output.

When enabled later, it should be a separate script-controlled mode with a small fixed template. The model may choose to request that mode only when the user asks for help remembering a word, but the final content should still come from code or structured data.

Suggested future sections:

- One short memory hook
- One everyday example
- One common collocation
- One confusable pair, only when data exists

Hard limits for expansion:

- Strict lookup card always comes first
- Expansion is optional and clearly separated
- No unsupported claims
- No closing question
- No long motivational text
