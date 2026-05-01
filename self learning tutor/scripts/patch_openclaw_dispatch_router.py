#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
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
SEND_LOOKUP_CARD_START = "async function sendDirectLookupCardReply"
LEARNING_GUIDE_HELPER_MARKER = "async function runDirectLookupJson(query) {"
LEARNING_GUIDE_CALL_MARKER = "sendLookupLearningGuideReply(dc, ctxPayload, replyToMessageId, lookupQuery"
LOG_ALIAS_ANCHOR = "const log = (0, lark_logger_1.larkLogger)('inbound/dispatch');"
LOG_ALIAS_LINE = "const logger = log;"


LEARNING_GUIDE_HELPERS = r"""
async function runDirectLookupJson(query) {
    try {
        const { stdout, stderr } = await execFileAsync(LOOKUP_PYTHON, [LOOKUP_SCRIPT_PATH, '--format', 'json', '--style', 'strict', '--db', LOOKUP_DB_PATH, query], {
            cwd: LOOKUP_WORKSPACE_DIR,
            maxBuffer: 1024 * 1024,
        });
        if (stderr) {
            logger.info('lookup json stderr: ' + String(stderr).trim());
        }
        const parsed = JSON.parse(stdout);
        if (parsed?.error === 'not_found') {
            return null;
        }
        return parsed;
    }
    catch (err) {
        logger.warn('lookup json failed; skipping learning guide', { error: String(err), query });
        return null;
    }
}

function buildLookupLearningGuidePrompt(query, lookupJson) {
    return [
        'mode: LEARNING_GUIDE',
        '',
        '请基于 lookup_result 生成第二阶段学习指导。第一阶段词典卡已经发给用户，不要重复完整词典卡。',
        '必须遵守 self-learning-tutor 技能里的 LEARNING_GUIDE 规则。',
        '',
        'query: ' + query,
        '',
        'lookup_result:',
        JSON.stringify(lookupJson, null, 2),
    ].join('\n');
}

async function sendLookupLearningGuideReply(dc, ctxPayload, replyToMessageId, query, lookupJsonPromise, skillFilter, skipTyping) {
    try {
        const lookupJson = await lookupJsonPromise;
        if (!lookupJson) {
            return;
        }
        const guideBody = buildLookupLearningGuidePrompt(query, lookupJson);
        const guidePayload = {
            ...ctxPayload,
            Body: guideBody,
            BodyForAgent: guideBody,
            RawBody: guideBody,
            CommandBody: guideBody,
            InboundHistory: undefined,
        };
        const effectiveSessionKey = (dc.threadSessionKey ?? dc.route.sessionKey) + ':lookup-guide';
        const toolUseDisplay = {
            mode: 'off',
            showToolUse: false,
            showToolResultDetails: false,
            showFullPaths: false,
        };
        const { dispatcher, replyOptions, markDispatchIdle, markFullyComplete } = (0, reply_dispatcher_1.createFeishuReplyDispatcher)({
            cfg: dc.accountScopedCfg,
            agentId: dc.route.agentId,
            chatId: dc.ctx.chatId,
            sessionKey: effectiveSessionKey,
            replyToMessageId: replyToMessageId ?? dc.ctx.messageId,
            accountId: dc.account.accountId,
            chatType: dc.ctx.chatType,
            skipTyping,
            replyInThread: dc.isThread,
            toolUseDisplay,
        });
        const guideSkillFilter = Array.isArray(skillFilter) && skillFilter.length ? skillFilter : ['self-learning-tutor'];
        await dc.core.channel.reply.dispatchReplyFromConfig({
            ctx: guidePayload,
            cfg: dc.accountScopedCfg,
            dispatcher,
            replyOptions: {
                ...replyOptions,
                skillFilter: guideSkillFilter,
            },
        });
        await dispatcher.waitForIdle();
        markFullyComplete();
        markDispatchIdle();
        logger.info('lookup learning guide sent', { query });
    }
    catch (err) {
        logger.warn('lookup learning guide failed', { error: String(err), query });
    }
}
"""


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


def patch_logger_alias(text: str) -> tuple[str, bool]:
    if LOG_ALIAS_LINE in text:
        return text, False
    if LOG_ALIAS_ANCHOR not in text:
        raise RuntimeError("lark logger anchor not found")
    return text.replace(LOG_ALIAS_ANCHOR, LOG_ALIAS_ANCHOR + "\n" + LOG_ALIAS_LINE, 1), True


def patch_learning_guide_helpers(text: str) -> tuple[str, bool]:
    if LEARNING_GUIDE_HELPER_MARKER in text:
        return text, False
    insert_idx = text.find(SEND_LOOKUP_CARD_START)
    if insert_idx == -1:
        raise RuntimeError("sendDirectLookupCardReply function not found")
    helper_block = LEARNING_GUIDE_HELPERS.strip("\n") + "\n\n"
    return text[:insert_idx] + helper_block + text[insert_idx:], True


def patch_learning_guide_call(text: str) -> tuple[str, bool]:
    if LEARNING_GUIDE_CALL_MARKER in text:
        return text, False
    old = """            const lookupStart = Date.now();
            const lookupPromise = runDirectLookup(lookupQuery);
            const cardSent = await sendDirectLookupCardReply({"""
    new = """            const lookupStart = Date.now();
            const lookupPromise = runDirectLookup(lookupQuery);
            const lookupJsonPromise = runDirectLookupJson(lookupQuery);
            const cardSent = await sendDirectLookupCardReply({"""
    if old not in text:
        raise RuntimeError("lookup promise block not found")
    text = text.replace(old, new, 1)
    pattern = re.compile(
        r"""(            if \(!cardSent\) \{\n"""
        r"""                const lookupText = await lookupPromise;\n"""
        r"""                await \(0, send_1\.sendMessageFeishu\)\(\{\n"""
        r"""                    cfg: dc\.accountScopedCfg,\n"""
        r"""                    to: dc\.ctx\.chatId,\n"""
        r"""                    text: lookupText,\n"""
        r"""                    replyToMessageId: replyToMessageId \?\? dc\.ctx\.messageId,\n"""
        r"""                    accountId: dc\.account\.accountId,\n"""
        r"""                    replyInThread: dc\.isThread,\n"""
        r"""                \}\);\n"""
        r"""            \}\n)"""
    )
    match = pattern.search(text)
    if not match:
        raise RuntimeError("lookup fallback block not found")
    call = """            void sendLookupLearningGuideReply(dc, ctxPayload, replyToMessageId, lookupQuery, lookupJsonPromise, skillFilter, skipTyping);
"""
    text = text[:match.end()] + call + text[match.end():]
    return text, True


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

    text, logger_changed = patch_logger_alias(text)
    text, card_changed = patch_complete_card(text)
    text, helper_changed = patch_learning_guide_helpers(text)
    text, call_changed = patch_learning_guide_call(text)
    return text, lookup_changed or logger_changed or card_changed or helper_changed or call_changed


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
