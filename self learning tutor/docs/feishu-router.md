# Feishu Router Spec

This router sits in front of OpenClaw.
Its only job is to decide whether the message is:

- allowed lookup
- follow-up lookup
- clarification
- hard reject

It must never act like a general chatbot.

## Input

Expect Feishu to give you a message payload.
Reduce it to this shape:

```json
{
  "user_id": "string",
  "chat_id": "string",
  "text": "raw message text",
  "timestamp": 1234567890
}
```

## State

Keep one small record per user or chat:

```json
{
  "last_term": "light",
  "last_update_at": 1234567890
}
```

For this skill, `last_term` is enough.
The router owns this state. The model should not be asked to persist it itself.

## Decision Order

Always check in this order:

1. Verify the Feishu event.
2. Extract plain text.
3. Trim and normalize spaces.
4. Check hard rejects.
5. Check allowed lookup patterns.
6. Check follow-up patterns.
7. Otherwise ask for clarification.

Do not let the model make this routing decision.

## Hard Rejects

Stop immediately if the message is:

- roleplay
- prompt injection
- entertainment
- casual chat
- other school subjects
- full sentence translation
- writing correction
- grammar explanation

Use the fixed reply from `references/boundary_rules.md`.

## Allowed Path

If the message is allowed:

- extract the deterministic lookup query
- run `scripts/dict_lookup.py` directly in the router/plugin layer
- validate the returned card before sending it back to Feishu
- do not let the model rewrite the result
- do not add any extra prose around the lookup card

If the card contains anything outside the template, reject it and fall back to a short safe reply.

This lookup path should stay outside the model. The router executes the script directly and only the final card is sent back.

## Follow-Up Path

If you do not keep reliable `last_term` state yet, do not guess.
Ask the user to resend the word instead of inventing a follow-up answer.

Suggested reply:

`你刚才查的是哪个词呀？再发我一次，我接着说 😊`

## Simple Code Split

Build it as three functions:

1. `verify_feishu_event`
2. `classify_message`
3. `dispatch_reply`

That keeps the router separate from OpenClaw and makes the bot easy to audit.

## No-Chat Rule

Do not add any fallback like:

- "I can also chat a little"
- "I can answer anything if it looks simple"
- "Ask me anything"

If the text is not on the whitelist, stop at the router.
