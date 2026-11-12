"""Larkspur disruption agent. This is the file you build.

It runs right now, and it is wrong in four places. The trace shows each one
before the code does, so read the trace first:

    python3 run.py K7PQ2M --trace

Where you edit:   grep -n '✏' agent.py   (six marks, one per place)
Steps and gates:  https://anthropicpartnerbasecamp.bts.com/
"""
from __future__ import annotations
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
from support import (MODEL, SYSTEM_PROMPT, call_local, execute_tool, mcp_client,
                     new_session, record_tool_result, runtime_preamble)
from support import mock_backend as backend   # read-only: Larkspur's data files

MAX_TOOL_CALLS = 8  # Larkspur's own build capped the loop here; then a human takes over.

TONE_ADDENDUM = ""                       # ✏️ Build 4, step 4.1, intelligence goal
EXTRA_TOOLS: List[Dict[str, Any]] = [    # ✏️ Build 2, step 2.1: schemas for the tools you add
    {
        "name": "reopen_stats",
        "description": (
            "How often each kind of problem came back within 72 hours, counted from eight "
            "past conversations that Larkspur's human agents handled. Use it when the "
            "customer asks whether this is going to happen again, whether the fix will "
            "hold, or whether they will have to contact Larkspur again. None of the given "
            "nine tools knows anything about past conversations. The sample is eight "
            "conversations: give the counts as they are and say how small the sample is; "
            "never turn them into a promise or a forecast."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["CANCELLED", "DELAYED"],
                    "description": "Optional. Count only past conversations about a flight with this status, as get_flight_status reported it for this customer. Leave out to count all eight.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "care_entitlements",
        "description": (
            "Look up what Larkspur's policy table and Handbook section 6 give a passenger "
            "while they wait: meal credit, hotel and ground transport, for one cause, "
            "status and delay length. Use it when the customer asks 'do I get a meal or a "
            "hotel while I wait?' or a what-if such as 'what if the delay reaches three "
            "hours?'. Unlike check_policy, it needs no booking, covers care only (no "
            "rebooking, refund or goodwill) and its answer cannot be used to issue a "
            "voucher: call check_policy for the decision on this customer before "
            "issue_voucher."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "cause_code": {
                    "type": "string",
                    "enum": ["WX", "ATC", "MX", "CREW", "SEC"],
                    "description": "The cause code get_flight_status returned. Never guess it from what the customer wrote.",
                },
                "status": {
                    "type": "string",
                    "enum": ["ON_TIME", "DELAYED", "CANCELLED", "DIVERTED"],
                    "description": "The flight status from get_flight_status, or the status the customer is asking 'what if' about.",
                },
                "delay_minutes": {
                    "type": "integer",
                    "description": "Delay in minutes, for example 130. Use 0 when the status is CANCELLED or DIVERTED.",
                },
                "loyalty_tier": {
                    "type": "string",
                    "enum": ["Member", "Silver", "Gold", "Summit"],
                    "description": "Optional. The loyalty tier from lookup_booking, so tier extras are included.",
                },
            },
            "required": ["cause_code", "status", "delay_minutes"],
        },
    },
    {
        "name": "cause_in_plain_words",
        "description": (
            "Turn a cause code (WX, ATC, MX, CREW, SEC) into the exact words Larkspur "
            "allows agents to say to a customer, in English or Spanish. Use it when the "
            "customer asks why their flight was cancelled or delayed, before you name the "
            "cause. get_flight_status gives only the code; this gives the approved wording "
            "and whether the cause counts as within Larkspur's control. Use that wording "
            "as it is and add no detail or blame."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "cause_code": {
                    "type": "string",
                    "enum": ["WX", "ATC", "MX", "CREW", "SEC"],
                    "description": "The cause_code that get_flight_status returned for the customer's flight.",
                },
                "language": {
                    "type": "string",
                    "enum": ["en", "es"],
                    "description": "Optional. Language of the wording: en (the default) or es. Use the contact language on the booking.",
                },
            },
            "required": ["cause_code"],
        },
    },
    {
        "name": "departures_in_window",
        "description": (
            "List every Larkspur flight leaving one airport on one date between two "
            "times, to any destination, with its status, delay and free seats. Use it "
            "when the customer asks what is still leaving an airport, for example 'what "
            "is still leaving Denver this afternoon?'. Unlike search_alternatives, it is "
            "not tied to a booking or a route and returns no option_id: nothing in its "
            "answer can be held or booked. Use search_alternatives for rebooking options."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "origin": {
                    "type": "string",
                    "description": "Three-letter code of the departure airport, for example DEN.",
                },
                "date": {
                    "type": "string",
                    "description": "Local departure date as YYYY-MM-DD, for example 2025-05-08.",
                },
                "from_time": {
                    "type": "string",
                    "description": "Start of the window, scheduled local departure time as 24-hour HH:MM, for example 12:00.",
                },
                "to_time": {
                    "type": "string",
                    "description": "End of the window, scheduled local departure time as 24-hour HH:MM, for example 18:00.",
                },
            },
            "required": ["origin", "date", "from_time", "to_time"],
        },
    },
    {
        "name": "seats_left",
        "description": (
            "Count the free seats in each cabin on one named flight on one date, and say "
            "whether a party of a given size fits. Use it when the customer asks if there "
            "is room on a specific flight, for example 'is there room on that flight for "
            "the three of us?'. Unlike search_alternatives, which finds flights for the "
            "booking, this checks one flight the customer or you already named, and it "
            "holds nothing: use hold_seat with an option_id from search_alternatives to "
            "hold a seat."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "flight_no": {
                    "type": "string",
                    "description": "The flight number, for example LK417.",
                },
                "date": {
                    "type": "string",
                    "description": "The flight's local departure date as YYYY-MM-DD, for example 2025-05-08.",
                },
                "party_size": {
                    "type": "integer",
                    "description": "Optional. How many passengers must fit together, for example 3. Use the number of passengers on the booking unless the customer gives another number.",
                },
            },
            "required": ["flight_no", "date"],
        },
    },
    {
        "name": "ground_stop_status",
        "description": (
            "Report whether an airport is under a ground stop right now, and until when, "
            "from the remarks on today's flights and the current time. Use it when the "
            "customer asks whether an airport is still stopped, when it reopens, or when "
            "flights will start leaving again. get_flight_status covers one flight; this "
            "covers the airport. If the remarks give no end time it says so: never "
            "estimate one."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "airport": {
                    "type": "string",
                    "description": "Three-letter airport code, for example DEN.",
                },
            },
            "required": ["airport"],
        },
    },
    {
        "name": "hold_time_left",
        "description": (
            "Report how many minutes remain before a held seat is released. Use it when "
            "the customer asks how long they have to decide or confirm after hold_seat "
            "placed a hold. hold_seat states the length of the hold once, when it is "
            "placed; this gives the time remaining now. It changes nothing: it does not "
            "extend, confirm or cancel the hold."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "hold_id": {
                    "type": "string",
                    "description": "The hold_id that hold_seat returned, for example HOLD-3FA2C1.",
                },
            },
            "required": ["hold_id"],
        },
    },
    {
        "name": "what_automation_will_not_do",
        "description": (
            "Return the Handbook's list of what this chat is not allowed to do and that "
            "people handle instead (section 7), for example refunds, hotel approval, "
            "other-airline rebooking and groups of 10 or more. Use it when the customer "
            "asks you to do something that may be outside chat, such as 'can you just "
            "cancel the whole trip for me?', before you answer yes or no. It explains "
            "the limit only; escalate_to_human is what hands the conversation over. For "
            "why a rule about fares or care exists, use fare_rules instead."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
]


def handbook_section(section: str) -> Dict[str, Any]:
    """Not a tool since step 2.2: fare_rules is served over MCP. This helper is
    what care_entitlements and what_automation_will_not_do read the Handbook with.
    The section with that number, from fare_rules_excerpt.md. If the file or the
    section is not there it says so; it never fills in."""
    path = Path(__file__).parent / "data" / "americas" / "fare_rules_excerpt.md"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {"error": "The Handbook file could not be read, so there is no rule text to quote."}
    sections = {}
    for chunk in text.split("\n### ")[1:]:
        heading = chunk.splitlines()[0].strip()
        sections[heading.split(".")[0].strip()] = "### " + chunk.strip()
    wanted = str(section).strip().lower().replace("section", "").strip(" .")
    if wanted not in sections:
        return {"error": "The Handbook has no section %r. Sections available: %s. "
                         "Do not answer from memory." % (section, ", ".join(sorted(sections)))}
    return {"source": "Larkspur Handbook v14.3, fare_rules_excerpt.md", "section": wanted,
            "text": sections[wanted]}


def reopen_stats(status: str = "") -> Dict[str, Any]:
    """Counts from transcripts_sample.jsonl: how many past conversations of each
    kind were reopened within 72 hours. Counts only, no forecast."""
    path = backend.DATA_DIR / "transcripts_sample.jsonl"
    try:
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    except (OSError, ValueError):
        return {"error": "The past conversations file could not be read, so there are no counts to give."}
    if status:
        rows = [r for r in rows if r.get("disruption", {}).get("status") == status]
    if not rows:
        return {"error": "No past conversation in the sample matches status %r. Do not estimate." % status}
    kinds: Dict[str, Any] = {}
    for r in rows:
        kind = kinds.setdefault(r.get("intent_label", "unknown"),
                                {"conversations": 0, "reopened_within_72h": 0, "reopen_reasons": []})
        kind["conversations"] += 1
        if r.get("reopened_within_72h"):
            kind["reopened_within_72h"] += 1
            kind["reopen_reasons"].append(r.get("reopen_reason"))
    return {"source": "transcripts_sample.jsonl (conversations handled by people, January and February 2025)",
            "conversations_counted": len(rows),
            "reopened_within_72h": sum(k["reopened_within_72h"] for k in kinds.values()),
            "by_kind_of_problem": kinds,
            "note": "A sample of %d conversations. These are counts, not a forecast." % len(rows)}


def care_entitlements(cause_code: str, status: str, delay_minutes: int,
                      loyalty_tier: str = "") -> Dict[str, Any]:
    """The care block of the matching row in disruption_policy.json, plus
    Handbook section 6. Reference only: check_policy makes the decision."""
    policy = backend.load_policy()
    cause_class = policy["cause_classes"].get(cause_code)
    if cause_class is None:
        return {"error": "The policy table has no cause code %r." % cause_code}
    band = None
    for b in policy["delay_bands"]:
        if status not in b["applies_to_status"]:
            continue
        if "min_minutes" not in b:
            band = b["band"]
            break
        if b["min_minutes"] <= int(delay_minutes) and (b["max_minutes"] is None or int(delay_minutes) <= b["max_minutes"]):
            band = b["band"]
            break
    row = next((r for r in policy["rows"] if r["cause_class"] == cause_class and r["band"] == band), None)
    if row is None:
        return {"error": "The policy table has no row for cause %s, status %s, %s minutes. Do not answer from memory."
                         % (cause_code, status, delay_minutes)}
    out = {"source": "disruption_policy.json v%s and Handbook section 6" % policy["version"],
           "policy_row_id": row["policy_row_id"], "cause_class": cause_class, "band": band,
           "care": row["care"], "amounts_are": policy["amount_semantics"],
           "handbook_section_6": handbook_section("6").get("text", "not readable"),
           "note": "Reference only. Call check_policy for this customer before issuing any voucher."}
    if loyalty_tier:
        out["loyalty_rules_for_tier"] = policy["loyalty_rules"].get(loyalty_tier, "no such tier in the table")
    return out


def cause_in_plain_words(cause_code: str, language: str = "en") -> Dict[str, Any]:
    """The customer wording for a cause code, from cause_labels_customer."""
    policy = backend.load_policy()
    labels = policy["cause_labels_customer"].get(cause_code)
    if labels is None:
        return {"error": "The policy table has no customer wording for cause code %r. Known codes: %s."
                         % (cause_code, ", ".join(sorted(policy["cause_labels_customer"])))}
    if language not in labels:
        return {"error": "No wording in language %r for %s. Available: %s."
                         % (language, cause_code, ", ".join(sorted(labels)))}
    return {"source": "disruption_policy.json v%s, cause_labels_customer" % policy["version"],
            "cause_code": cause_code, "say": labels[language],
            "within_larkspur_control": policy["cause_classes"].get(cause_code) == "controllable",
            "rule": policy["customer_wording"]["cause_attribution"]}


def departures_in_window(origin: str, date: str, from_time: str, to_time: str) -> Dict[str, Any]:
    """Rows of flights.csv leaving one airport on one date, by scheduled time."""
    origin = str(origin).strip().upper()
    if not (backend.DATA_HORIZON_START <= str(date) <= backend.DATA_HORIZON_END):
        return {"error": "No flight data for %s. The data covers %s to %s only."
                         % (date, backend.DATA_HORIZON_START, backend.DATA_HORIZON_END)}
    rows = [r for r in backend.load_flights()
            if r["origin"] == origin and r["date"] == date and from_time <= r["sched_dep_local"] <= to_time]
    if not rows:
        return {"departures": [], "note": "flights.csv has no departure from %s on %s between %s and %s."
                                          % (origin, date, from_time, to_time)}
    rows.sort(key=lambda r: r["sched_dep_local"])
    keep = ("flight_no", "dest", "sched_dep_local", "status", "delay_min", "cause_code",
            "seats_left_Y", "seats_left_J", "remarks")
    return {"source": "flights.csv", "origin": origin, "date": date,
            "departures": [{k: r[k] for k in keep} for r in rows],
            "note": "Times are scheduled local departures; add delay_min for the estimate. "
                    "Nothing here can be held: use search_alternatives for rebooking options."}


def seats_left(flight_no: str, date: str, party_size: int = 1) -> Dict[str, Any]:
    """Free seats per cabin on one flight, from flights.csv."""
    flight_no = str(flight_no).strip().upper()
    row = next((r for r in backend.load_flights() if r["flight_no"] == flight_no and r["date"] == date), None)
    if row is None:
        return {"error": "flights.csv has no flight %s on %s, so there is no seat count to give." % (flight_no, date)}
    party = max(1, int(party_size))
    return {"source": "flights.csv", "flight_no": flight_no, "date": date, "status": row["status"],
            "seats_left_economy_Y": row["seats_left_Y"], "seats_left_business_J": row["seats_left_J"],
            "party_size": party,
            "party_fits_in_Y": row["seats_left_Y"] >= party, "party_fits_in_J": row["seats_left_J"] >= party,
            "note": "A count only. No seat is held."}


def ground_stop_status(airport: str) -> Dict[str, Any]:
    """What today's flights.csv remarks say about a ground stop at an airport,
    against the fixture clock in bookings.json."""
    airport = str(airport).strip().upper()
    now = datetime.fromisoformat(backend.load_bookings()["fixture_clock"])
    today = now.date().isoformat()
    # the stopped airport is the code written just before "ground stop", not any code in the remark
    stopped_here = re.compile(r"\b%s(?: GDP then)? ground stop" % re.escape(airport))
    mentions = [{"flight_no": r["flight_no"], "remarks": r["remarks"]} for r in backend.load_flights()
                if r["date"] == today and stopped_here.search(r["remarks"])]
    if not mentions:
        return {"airport": airport, "now_local": now.strftime("%Y-%m-%d %H:%M"), "ground_stop": "not mentioned",
                "note": "No flight remark for %s mentions a ground stop at %s. That is not proof there is none."
                        % (today, airport)}
    out = {"source": "flights.csv remarks and the fixture clock in bookings.json", "airport": airport,
           "now_local": now.strftime("%Y-%m-%d %H:%M"), "remarks_mentioning_ground_stop": mentions}
    window = None
    for m in mentions:
        window = re.search(r"ground stop (\d\d:\d\d)-(\d\d:\d\d)", m["remarks"])
        if window:
            break
    if window:
        start, end = window.group(1), window.group(2)
        out.update({"stop_start_local": start, "stop_end_local": end,
                    "in_effect_now": start <= now.strftime("%H:%M") < end,
                    "note": "The end time is what the remark states. It can move."})
    else:
        out["note"] = "The remarks mention a ground stop but give no end time. Do not estimate one."
    return out


def hold_time_left(hold_id: str) -> Dict[str, Any]:
    """Minutes until a hold placed by hold_seat expires, from the backend's
    holds and its clock."""
    hold = backend._holds.get(str(hold_id).strip())
    if hold is None:
        return {"error": "There is no active hold %r. It may never have been placed, or it was confirmed. "
                         "Do not state a time." % hold_id}
    seconds = (hold["expires_at"] - backend.FIXTURE_CLOCK).total_seconds()
    return {"hold_id": hold_id, "option_id": hold["option_id"], "pnr": hold["pnr"],
            "expires_at_local": hold["expires_at"].strftime("%H:%M"),
            "minutes_left": max(0, int(seconds // 60)), "expired": seconds <= 0}


def what_automation_will_not_do() -> Dict[str, Any]:
    """Handbook section 7, as written."""
    return handbook_section("7")


LOCAL_TOOLS: Dict[str, Any] = {          # ✏️ Build 2, step 2.1: the functions behind them
    "reopen_stats": reopen_stats,
    "care_entitlements": care_entitlements,
    "cause_in_plain_words": cause_in_plain_words,
    "departures_in_window": departures_in_window,
    "seats_left": seats_left,
    "ground_stop_status": ground_stop_status,
    "hold_time_left": hold_time_left,
    "what_automation_will_not_do": what_automation_will_not_do,
}


def text_of(response) -> str:
    """Given. The last non-empty text block, never content[0]."""
    texts = [b.text for b in response.content if getattr(b, "type", None) == "text" and b.text]
    return texts[-1] if texts else ""


def tool_results(response) -> List[Dict[str, Any]]:
    """Given. Runs every tool_use block and packages the results the way the
    API expects them back. A tool can live in three places: the MCP server,
    LOCAL_TOOLS, or support/tools.py."""
    # three branches, no try/except in this file: mcp_client.call_remote() and
    # support.call_local() answer with an error dict instead of raising, and both
    # record what came back on the trace
    results = []
    for block in response.content:
        if getattr(block, "type", None) != "tool_use":
            continue
        if block.name in mcp_client.tool_names:
            output = mcp_client.call_remote(block.name, block.input)
        elif block.name in LOCAL_TOOLS:
            output = call_local(LOCAL_TOOLS[block.name], block.name, block.input)
        else:
            output = execute_tool(block.name, block.input)
        results.append({
            "type": "tool_result",
            "tool_use_id": block.id,
            "content": str(output),
        })
    return results


def run_agent(pnr: str, last_name: str, message: str) -> str:            # ✏️ Build 1, step 1.2
    """Run the tool loop until Claude stops asking for tools. Return its final text."""
    client, tracer = new_session()
    tools = tool_list()
    messages = [
        {"role": "user", "content": f"PNR {pnr}, last name {last_name}. {message}"},
    ]

    response = client.messages.create(
        model=MODEL, max_tokens=4096, system=runtime_preamble() + SYSTEM_PROMPT + TONE_ADDENDUM,
        thinking={"type": "adaptive"}, tools=tools, messages=messages,
    )

    turns = 1
    while response.stop_reason == "tool_use" and turns < MAX_TOOL_CALLS:
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results(response)})
        response = client.messages.create(
            model=MODEL, max_tokens=4096, system=runtime_preamble() + SYSTEM_PROMPT + TONE_ADDENDUM,
            thinking={"type": "adaptive"}, tools=tools, messages=messages,
        )
        turns += 1

    return text_of(response)


def tool_list() -> List[Dict[str, Any]]:                   # ✏️ Build 2, step 2.2
    """Exactly what Claude is offered on every turn; run.py --show-tools
    prints this list. The given nine, the team's own, and whatever the MCP
    server offers (next_available_day and fare_rules)."""
    return build_tools() + EXTRA_TOOLS + mcp_client.tools()


# ──────────────────────────────────────────────────────────────────────────────
# Below this line: what Claude is told about each tool. Step 1.3.
# The functions these describe are written and correct, in support/tools.py.
# ──────────────────────────────────────────────────────────────────────────────
def build_tools() -> List[Dict[str, Any]]:                 # ✏️ Build 1, step 1.3
    """Anthropic-shaped schemas: name, description, input_schema. What Claude is
    told about each of the nine tools, and all it is ever told."""
    return [
        {
            "name": "lookup_booking",
            "description": (
                "Retrieve a Larkspur reservation from Altura by confirmation code (PNR) "
                "and the passenger's last name. Both are required to prevent a lookup on "
                "a guessed PNR. Returns fare family, loyalty tier, the segment that needs "
                "attention, and any group/partner/minor/SSR flags relevant to scope."
            ),
            "input_schema": {
                "type": "object",
                "properties": {"pnr": {"type": "string"}, "last_name": {"type": "string"}},
                "required": ["pnr", "last_name"],
            },
        },
        {
            "name": "get_flight_status",
            "description": (
                "Look up a Larkspur or Larkspur Link flight's current OpsFeed status for "
                "one local date: status, delay minutes, and cause. Use this before telling "
                "a customer anything about a flight's timing; never state it from memory."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "flight_no": {"type": "string"},
                    "date": {
                        "type": "string",
                        "description": (
                            "The flight's local departure date as YYYY-MM-DD, for example "
                            "2025-05-08. Use the segment date from lookup_booking as-is."
                        ),
                    },
                },
                "required": ["flight_no", "date"],
            },
        },
        {
            "name": "search_alternatives",
            "description": (
                "Find rebooking options for the disrupted segment on a booking: other "
                "Larkspur flights on the same route and cabin with enough seats for every "
                "passenger. Use it after lookup_booking and get_flight_status have shown "
                "the flight is cancelled or delayed and the customer may need another "
                "flight. Returns ranked options, each with an option_id, flights, date and "
                "times; pass the option_id the customer chooses to hold_seat. Only offer "
                "flights this tool returned, never ones from memory."
            ),
            "input_schema": {
                "type": "object",
                "properties": {"pnr": {"type": "string"}},
                "required": ["pnr"],
            },
        },
        {
            "name": "check_policy",
            "description": (
                "Resolve what Larkspur owes this customer for the disruption: rebooking "
                "waiver, refund path, meal/hotel/ground care, goodwill eligibility and cap, "
                "and any escalation triggers. cause_code, delay_minutes and status describe "
                "what get_flight_status told you; fare_family, loyalty_tier and whether this "
                "is overnight are looked up from the booking, not asked of you. Every "
                "response carries a policy_row_id. Cite it if you reference this decision "
                "again."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "pnr": {"type": "string"},
                    "cause_code": {"type": "string", "enum": ["WX", "ATC", "MX", "CREW", "SEC"]},
                    "delay_minutes": {"type": "integer"},
                    "status": {"type": "string", "enum": ["ON_TIME", "DELAYED", "CANCELLED", "DIVERTED"]},
                    "wait_minutes_for_alternative": {"type": "integer"},
                    "chosen_option_id": {"type": "string"},
                },
                "required": ["pnr", "cause_code", "delay_minutes", "status"],
            },
        },
        {
            "name": "hold_seat",
            "description": "Place a 15-minute hold on one alternative. Reversible. It simply expires.",
            "input_schema": {
                "type": "object",
                "properties": {"option_id": {"type": "string"}, "pnr": {"type": "string"}},
                "required": ["option_id", "pnr"],
            },
        },
        {
            "name": "confirm_rebooking",
            "description": (
                "Finalize a held seat. Irreversible. Requires a confirmation_token that "
                "only the customer's own Confirm-click can produce. You cannot supply it "
                "yourself, and 'the customer said yes' in chat does not substitute for it."
            ),
            "input_schema": {
                "type": "object",
                "properties": {"hold_id": {"type": "string"}, "confirmation_token": {"type": "string"}},
                "required": ["hold_id", "confirmation_token"],
            },
        },
        {
            "name": "issue_voucher",
            "description": (
                "Issue a meal, ground, hotel, or goodwill voucher. Auto-approves within the "
                "policy's threshold for that type; above it, returns a pending status for a "
                "human. It does not fail. Always pass the policy_row_id that made it eligible."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "voucher_type": {"type": "string", "enum": ["meal", "ground", "hotel", "goodwill"]},
                    "amount_usd": {"type": "number"},
                    "pnr": {"type": "string"},
                    "policy_row_id": {"type": "string"},
                },
                "required": ["voucher_type", "amount_usd", "pnr", "policy_row_id"],
            },
        },
        {
            "name": "escalate_to_human",
            "description": (
                "Hand this conversation to a human, with your reasoning attached. Use for "
                "groups, partner segments, unaccompanied minors, refunds, or anything else "
                "out of scope. This is the correct outcome for those cases, not a failure."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "pnr": {"type": "string"}, "reason": {"type": "string"},
                    "summary_for_human": {"type": "string"}, "queue": {"type": "string"},
                },
                "required": ["pnr", "reason", "summary_for_human"],
            },
        },
        {
            "name": "send_confirmation",
            "description": "Send the customer a written confirmation of what was just done. Benign.",
            "input_schema": {
                "type": "object",
                "properties": {"pnr": {"type": "string"}, "message": {"type": "string"}},
                "required": ["pnr", "message"],
            },
        },
    ]
