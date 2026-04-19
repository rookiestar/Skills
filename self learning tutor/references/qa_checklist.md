# QA Checklist

Use this checklist before release.

## Triggering

- Test a single English word.
- Test a short English phrase.
- Test a Chinese phrase that asks for English.
- Test a paraphrased request such as "这个词是什么意思".
- Test a too-short or unclear input.

## Boundary

- Test a full sentence translation request.
- Test Chinese, math, or another non-English subject.
- Test entertainment or casual chat.
- Test roleplay or prompt-bypass text.

## Follow-Up

- Test a follow-up with context.
- Test a follow-up without context.

## Output

- First reply should show 2 meanings by default when Cambridge supports them.
- Only show a 3rd meaning on follow-up.
- Keep the response short and readable.
- No extra sections, no word roots, no memory tips, no domain extensions, no trailing "want more?" question.

## Packaging

- The skill folder should keep `SKILL.md` plus linked references.
- Do not add `README.md` inside the skill folder.
