#!/usr/bin/env python3
from __future__ import annotations

import argparse
import textwrap
from pathlib import Path


DEFAULT_PATH = (
    Path.home()
    / ".openclaw"
    / "extensions"
    / "openclaw-lark"
    / "src"
    / "messaging"
    / "inbound"
    / "dispatch.js"
)

COMMENT_START = "async function dispatchCommentMessage(dc, ctxPayload, skillFilter) {"
NORMAL_START = (
    "async function dispatchNormalMessage(dc, ctxPayload, chatHistories, historyKey, "
    "historyLimit, replyToMessageId, skillFilter, skipTyping) {"
)
LOOKUP_ANCHOR = "const lookupRoute = await classifyLookupMessage(dc.ctx.content ?? '', undefined);"
END_MARKER = "    const effectiveSessionKey = dc.threadSessionKey ?? dc.route.sessionKey;"
COMPLETE_CARD_START = "        const completeCard = builder_1.buildCardContent('complete', {"
COMPLETE_CARD_ELAPSED = "            elapsedMs: Date.now() - startedAt,"


def patch_complete_card(text: str) -> tuple[str, bool]:
    start = text.find(COMPLETE_CARD_START)
    if start == -1:
        raise RuntimeError("complete card block not found")
    end = text.index("        });", start)
    block = text[start:end]
    if "showToolUse:" in block:
        return text, False
    if COMPLETE_CARD_ELAPSED not in block:
        raise RuntimeError("complete card elapsed line not found")
    block = block.replace(
        COMPLETE_CARD_ELAPSED,
        COMPLETE_CARD_ELAPSED + "\n            showToolUse: false,",
        1,
    )
    return text[:start] + block + text[end:], True


def patch_dispatch_text(text: str) -> tuple[str, bool]:
    lookup_changed = False
    comment_start = text.index(COMMENT_START)
    normal_start = text.index(NORMAL_START)

    comment_block = text[comment_start:normal_start]
    if LOOKUP_ANCHOR in comment_block:
        lookup_idx = text.find(LOOKUP_ANCHOR, comment_start, normal_start)
        if lookup_idx == -1:
            raise RuntimeError("misplaced lookup anchor not found")

        end_idx = text.index(END_MARKER, lookup_idx, normal_start)
        misplaced_block = text[lookup_idx:end_idx]
        text = text[:lookup_idx] + text[end_idx:]

        normal_start = text.index(NORMAL_START)
        insert_idx = text.index(END_MARKER, normal_start)
        lookup_block = textwrap.indent(textwrap.dedent(misplaced_block).rstrip("\n"), "    ") + "\n"

        if LOOKUP_ANCHOR not in text[normal_start:insert_idx]:
            text = text[:insert_idx] + lookup_block + text[insert_idx:]
            lookup_changed = True
    elif LOOKUP_ANCHOR not in text[normal_start:]:
        raise RuntimeError("lookup anchor not found in normal function")

    text, card_changed = patch_complete_card(text)
    return text, lookup_changed or card_changed


def main() -> int:
    parser = argparse.ArgumentParser(description="Patch the openclaw-lark lookup router and card chrome")
    parser.add_argument("--path", type=Path, default=DEFAULT_PATH)
    args = parser.parse_args()

    path = args.path.expanduser()
    text = path.read_text(encoding="utf-8")
    patched, changed = patch_dispatch_text(text)
    if changed:
        path.write_text(patched, encoding="utf-8")
        print(f"patched {path}")
    else:
        print(f"already patched: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
