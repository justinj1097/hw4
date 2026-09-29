"""The PydanticAI shopping agent: tools from tools.py, output ChatReply, with code-level honesty checks."""

from __future__ import annotations

import itertools
import time
from datetime import datetime, timezone
import os
import re

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

from openai import AsyncOpenAI
from pydantic_ai import Agent, CallToolsNode, ModelRequestNode, ModelRetry, RunContext
from pydantic_ai.exceptions import ModelHTTPError, UnexpectedModelBehavior, UsageLimitExceeded
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, RetryPromptPart, TextPart, ToolCallPart, ToolReturnPart, UserPromptPart
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.usage import UsageLimits

import db
from config import MODEL_NAME, PORTKEY_API_KEY, PORTKEY_BASE_URL, PORTKEY_PROVIDER, PROMPT_PATH
from models import ChatReply, ChatResponse, ChatTurn, Checks, CurrentPage, PublicUser
from audit import TurnAudit, summarize
from safety import redact
from tools import TOOLS, ChatDeps

MAX_MODEL_REQUESTS = 8  # model round trips per chat turn (tool calls + retries + the answer)
OUTPUT_RETRIES = 2  # times the honesty validator may send a draft back
MONEY = re.compile(r"\$\s?(\d{1,4}(?:,\d{3})*(?:\.\d{1,2})?)")
# Stock counts stated in a reply: "only 2 left", "15 in stock", "12 available", "5 units".
STOCK_COUNT = re.compile(r"\b(\d{1,4})\s+(?:left|in stock|available|units?|remaining)\b", re.I)
# Turns that need planning or arithmetic get more reasoning effort (the "smarter" setting of the same model).
HARD_TURN = re.compile(r"\b(budget|total|combined|altogether|compare|comparison|difference|cheaper|cheapest|most expensive|"
                       r"outfit|gift|gifts|bundle|each|both|under \$|over \$|between|recommend|which (one|is) better|family)\b", re.I)


def _client() -> AsyncOpenAI:
    if not PORTKEY_API_KEY:
        raise RuntimeError("PORTKEY_API_KEY is not set (put it in the workspace .env).")
    return AsyncOpenAI(api_key=PORTKEY_API_KEY, base_url=PORTKEY_BASE_URL,
                       default_headers={"x-portkey-api-key": PORTKEY_API_KEY, "x-portkey-provider": PORTKEY_PROVIDER})


def _amount(text: str) -> float:
    return float(text.replace(",", ""))


def allowed_amounts(deps: ChatDeps) -> set[float]:
    """Dollar figures the reply may state: a seen price, a small multiple of one, a sum of up to 3 seen items, or a number the shopper typed."""
    prices = sorted(set(deps.prices.values()))
    ok = set(deps.user_amounts)
    for p in prices:
        ok.update(round(p * k, 2) for k in range(1, 11))
    for combo in itertools.combinations_with_replacement(prices[:40], 2):
        ok.add(round(sum(combo), 2))
    for combo in itertools.combinations_with_replacement(prices[:25], 3):
        ok.add(round(sum(combo), 2))
    return ok


def honesty_problems(deps: ChatDeps, out: ChatReply) -> list[str]:
    """Reasons a draft reply can't be trusted: unknown products, or prices or stock counts no tool returned this turn."""
    problems = []
    unknown = [p.product_id for p in out.picks if p.product_id not in deps.seen_ids]
    if unknown:
        problems.append(f"picks {unknown} were not returned by a tool in this turn; search or look them up first, or remove them.")
    if out.picks and not out.showcase_title:
        problems.append("Give the cards a short showcase_title, e.g. 'Hoodies we carry'.")
    text = " ".join([out.reply, *(p.highlight for p in out.picks)])  # highlights are checked like the reply
    stated = {_amount(m) for m in MONEY.findall(text)}
    unverified = sorted(a for a in stated if a not in allowed_amounts(deps))
    if unverified:
        problems.append(f"The reply states ${', $'.join(f'{a:g}' for a in unverified)} but no tool result supports it. Use only prices from tool results.")
    counts = sorted({int(n) for n in STOCK_COUNT.findall(text)} - deps.quantities)
    if counts:
        problems.append(f"The reply states stock count(s) {counts} that no check_stock or search result returned. Call check_stock and use its numbers.")
    return problems


def build_agent(client: AsyncOpenAI) -> Agent[ChatDeps, ChatReply]:
    model = OpenAIResponsesModel(MODEL_NAME, provider=OpenAIProvider(openai_client=client))
    agent = Agent(model, deps_type=ChatDeps, output_type=ChatReply, instructions=PROMPT_PATH.read_text(), tools=TOOLS, retries=OUTPUT_RETRIES)

    @agent.instructions
    def who_is_shopping(ctx: RunContext[ChatDeps]) -> str:
        """Written by code on every turn from ChatDeps.user (the users table), never from anything the shopper typed."""
        u = ctx.deps.user
        if not u:
            return "## Who is chatting\nA guest (not signed in). Don't ask for their email. They can create an account to save their chats."
        return (f"## Who is chatting\nSigned in as {u.first_name} {u.last_name}, email {u.email}, member since {u.created_at[:10]}. "
                "Greet them by first name. Their chat is saved, so earlier turns may be from a previous visit. "
                "Only mention their email or account details if they ask about their own account (use get_my_account).")

    @agent.instructions
    def where_they_are(ctx: RunContext[ChatDeps]) -> str:
        """Page context, verified by the server: lets 'this' / 'it' resolve to the product on screen."""
        page = ctx.deps.page
        if not page:
            return "## Where they are\nUnknown page."
        text = f"## Where they are\nRight now the shopper is on the {page.describe()}."
        if page.saved:
            names = "; ".join(f"{s['name']} ({s['product_id']})" for s in page.saved)
            text += f" They have {len(page.saved)} saved item(s) on their wishlist: {names}. 'My saved items' means these."
        if page.kind == "product":
            text += (f" When they say 'this', 'it', 'this one', or ask about a color or size without naming a product, they mean "
                     f"**{page.product_name}** (product_id `{page.product_id}`). Look it up with the tools before answering.")
        return text

    @agent.output_validator
    def honest(ctx: RunContext[ChatDeps], out: ChatReply) -> ChatReply:
        if problems := honesty_problems(ctx.deps, out):
            raise ModelRetry(" ".join(problems))
        return out

    return agent


def to_history(turns: list[ChatTurn]) -> list[ModelMessage]:
    messages: list[ModelMessage] = []
    for t in turns[-12:]:
        if t.role == "user":
            messages.append(ModelRequest(parts=[UserPromptPart(content=t.content)]))
        else:
            messages.append(ModelResponse(parts=[TextPart(content=t.content)]))
    return messages


def history_for_user(user_id: int) -> list[ChatTurn]:
    """The last 12 saved messages, each annotated with the page it was sent from and the cards shown."""
    turns = []
    for m in db.chat_history(user_id, limit=12):
        text = m.content
        if m.role == "user" and m.page:
            text = f"[Sent from the {m.page.describe()}] {text}"
        if m.role == "assistant" and m.showcase:
            text += "\n\n[Cards shown: " + ", ".join(f"{c.name} ({c.product_id})" for c in m.showcase.items) + "]"
        turns.append(ChatTurn(role=m.role, content=text[:4000]))
    return turns


def choose_effort(message: str) -> str:
    return "high" if HARD_TURN.search(message) or len(message) > 240 else "low"


async def chat(message: str, user: PublicUser | None, history: list[ChatTurn], page: CurrentPage | None = None) -> ChatResponse:
    """Run one turn step by step (agent.iter) so every tool call is written to the append-only audit trail."""
    deps = ChatDeps(user=user, page=page, user_amounts={_amount(m) for m in MONEY.findall(message)})
    effort = choose_effort(message)
    trail = TurnAudit(user, page, effort)
    trail.add("turn_started", result_summary=f"message: {redact(message, 200)}")
    started = time.perf_counter()
    pending: dict[str, tuple[str, dict]] = {}
    stop, usage = "error", None
    try:
        async with _client() as client:  # one client per turn, closed afterwards: its connections belong to this event loop
            async with build_agent(client).iter(message, deps=deps, message_history=to_history(history),
                                                model_settings={"openai_reasoning_effort": effort},
                                                usage_limits=UsageLimits(request_limit=MAX_MODEL_REQUESTS)) as run:
                async for node in run:
                    if isinstance(node, CallToolsNode):
                        for part in node.model_response.parts:
                            if isinstance(part, ToolCallPart):
                                pending[part.tool_call_id] = (part.tool_name, part.args_as_dict())
                    elif isinstance(node, ModelRequestNode):
                        for part in node.request.parts:
                            if isinstance(part, (ToolReturnPart, RetryPromptPart)) and part.tool_call_id in pending:
                                name, args = pending.pop(part.tool_call_id)
                                if isinstance(part, RetryPromptPart):
                                    trail.add("validation_retry", tool_name=name, result_summary=redact(part.model_response()))
                                else:
                                    trail.add("tool_call", tool_name=name, tool_args={k: str(v) for k, v in args.items()},
                                              result_summary=summarize(part.content))
                usage = run.usage
                reply = run.result.output
        stop = "completed"
        trail.add("final_answer", result_summary=redact(f"{len(reply.picks)} card(s) '{reply.showcase_title or '-'}' · {reply.reply}"))
    except UsageLimitExceeded:
        stop = "usage_limit"
        raise
    except UnexpectedModelBehavior:
        stop = "validation_failed"
        raise
    except ModelHTTPError as error:
        stop = "content_filter" if "content_filter" in str(error.body) else "error"
        raise
    finally:
        trail.add("run_stopped", stop_reason=stop, duration_ms=int((time.perf_counter() - started) * 1000),
                  model_requests=usage.requests if usage else None,
                  tokens_in=usage.input_tokens if usage else None, tokens_out=usage.output_tokens if usage else None)
        trail.flush()
    showcase = db.build_showcase(reply.showcase_title, [(p.product_id, p.highlight) for p in reply.picks], reply.browse)
    checks = Checks(checked_at=datetime.now(timezone.utc).isoformat(timespec="seconds"), items=deps.checks) if deps.checks else None
    return ChatResponse(reply=reply.reply, showcase=showcase, checks=checks, effort=effort)
