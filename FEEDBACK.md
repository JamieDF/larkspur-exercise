# Client review: Larkspur disruption-care agent

**To:** Room 10  
**From:** Larkspur client review agent, on behalf of Priya Raghavan  
**Re:** the disruption-care agent you walked us through in our last session  
**Generated:** 2026-11-12 09:56

## Priya's note

> Our vendor says we should just be using your best model.
>
> Why aren't we?
>
> Priya Raghavan, Larkspur Airlines

She sent that before this session opened. She means it. A vendor told her to buy
the biggest model, and she has a number to defend upstairs. Her four questions from
day one are still open. Naming a model answers none of them.

## Still open from day one

| Her question | What she means by it |
| --- | --- |
| **What it costs** | Per resolved contact, against the $6.90 a human contact costs us. |
| **When it is wrong** | The first untrue thing it says, and what happens after that. |
| **Who runs it** | In June, after you have left. |
| **What you left out** | The scope you cut, and why. |

## What the review agent found

Larkspur pointed a review agent at your repository. It read the
code. It did not run your agent, and the only file it changed is this one. Each
item below names the file and the line it is about.

**1. agent.py EXTRA_TOOLS declares eight schemas on top of the shipped nine, and readout-trace.json shows a 5-call run using none of them.**

The scan counts 17 tool schemas. The committed run in readout-trace.json called lookup_booking, get_flight_status, next_available_day, check_policy, search_alternatives. Every turn carries all 17 descriptions, and PITCH.md puts the tool list alone at 5,479 tokens on every turn. Nothing in the repository shows any of the eight added tools firing on any booking.

Run python3 run.py --all --trace and paste the totals footer, so the tools called per ticket can be counted against the eight you added.

**2. agent.py hold_seat has a 73-character description and send_confirmation 71, the two shortest of the 17 schemas.**

Your eight added tools run 331 to 528 characters each. hold_seat is the step that reserves inventory and send_confirmation is the last message the customer sees. A larger model reads the same 73 characters.

Run python3 run.py --show-tools and paste the hold_seat and send_confirmation entries.

**3. agent.py TONE_ADDENDUM is 0 characters, and PITCH.md says ticket R8KD3F ran as a normal resolution.**

The system prompt is SYSTEM_PROMPT plus an empty string, so the angry customer who threatens legal action gets the same instructions as everyone else. Your PITCH.md names this under Still broken. A bigger model reading an empty addendum has no tone instruction to follow, so Priya's model question does not touch this gap.

Run python3 run.py --all --trace and paste the R8KD3F section showing the final reply.

**4. PITCH.md reports 76,770 to 143,703 tokens in across five tickets, and the committed readout-trace.json shows 0 cache reads and 0 cache writes.**

The cost answer cites $0.0961 before caching and $0.0324 after, each over 15 conversations. The last committed wire run has 27,869 tokens in, a cache hit ratio of None, and 4 API turns. The input total nearly doubled when the eight tools were added, and the spend per ticket now sits on the tool list.

Run python3 bench.py --compare on your before and after labels and paste the output.

**5. The repository has no evals/cases.json, and the banked gates in readout.html stop at 4.1 with 3.1 missing.**

Banked gates are 1.2, 1.3, 1.4, 2.1, 2.2, 4.1, banked by Jamie Fraser. Gate 3.1 is not banked. Without eval cases, nothing in the repository can show that the three-flight listing for K7PQ2M or the group handover on G2HL9V holds on a rerun, and nothing can compare one model against another.

Run python3 eval_harness.py and paste the summary line.

## Your four answers

Four of the lines in your PITCH.md are answers to me rather than to your
verifier, and somebody on your side wrote them between our sessions. I read
those beside the code, not instead of it. Where an answer is carrying a number,
I have said whether the repository backs it.

| My question | Your answer | My read |
| --- | --- | --- |
| **What it costs** | About $0.03 per conversation, against $6.90 for a person. That is the model cost only, at list price: $0.0961 before we turned on prompt caching and $0.0324 after, each measured over 15 conversations. It leaves out hosting and testing, so the full cost is higher. | **Thin.** The $0.0961 and $0.0324 figures over 15 conversations are specific, but they sit in bench files that never reach the repository, and the $6.90 human figure has no source in the material. Paste the python3 bench.py --compare output, and the committed readout-trace.json shows a 0 cache hit ratio on its single run. |
| **When it is wrong** | Today a person finds out by reading the trace, which shows every tool the agent called and what came back. We have no automatic test cases yet, so nothing flags a wrong sentence by itself. The customer is protected on the steps that cannot be undone: a booking needs their own Confirm click, and refunds, hotels and groups go to a person. Ticket G2HL9V went to the group queue in our run. | **Answered.** "We have no automatic test cases yet" matches the repository, which has no evals/cases.json. The G2HL9V group handover claim is checkable from python3 run.py --all --trace. |
| **Who runs it** | Not decided. Nobody is named yet to watch, fix or update the agent after our team leaves. What they would own is one file, agent.py, with the loop and seventeen tool descriptions; next_available_day and fare_rules live in Larkspur's own MCP server. | **Answered.** "Not decided. Nobody is named yet" is honest, and the scope you name is accurate: agent.py holds 17 tool schemas and the other two tools come from the MCP server. TEAM.md would be where an owner gets written down. |
| **What you left out** | Refunds, hotel approval and groups of 10 or more, because the Handbook keeps them with people, so the agent hands over. Special handling for angry customers, because we have not written the tone instructions. | **Answered.** Refunds, hotel approval and groups of 10 or more line up with the what_automation_will_not_do description, and the missing angry-customer handling matches TONE_ADDENDUM at 0 characters. |

All four answered. Bring the artifact behind each one to our next meeting, not the sentence.

## Before our next meeting

> Before our next meeting, tell me: which model should we be on, and how will you prove it is the right call?
>
> Priya Raghavan, Larkspur Airlines

Bring two things. A recommendation, and the measurement behind it. If the model is
not the problem, say so, and bring the number that shows it.

## What this review read

- `agent.py (656 lines)`
- `PITCH.md`
- `TEAM.md`
- `readout-trace.json`
- `readout.html (evidence block)`
- `PITCH.md (4 of 4 answers to Priya)`
- given files that differ from the shipped pack: `verify.py`, `eval_harness.py`, `bench.py`, `readout.py`, `setup.py`, `pod_sync.py`, `run.py`, `review.py`, `support/__init__.py`, `support/client.py`, `support/data.py`, `support/models.py`, `support/tools.py`, `support/trace.py`, `support/offline.py`, `support/mock_backend.py`, `support/mcp_client.py`, `support/mcp_server.py`, `support/mcp_selftest.py`, `support/access.py`, `support/keyscan.py`, `support/review.py`

Reviewer: `claude-sonnet-5-5`. Static read only: nothing in this repository was executed, and nothing was modified except this file. Larkspur Airlines is a fictional training scenario. Confidential, do not distribute.
