# Client review: Larkspur disruption-care agent

**To:** Room 10  
**From:** Larkspur client review agent, on behalf of Priya Raghavan  
**Re:** the disruption-care agent you walked us through in our last session  
**Generated:** 2026-11-12 09:52

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

**1. agent.py hold_seat has a 73-character description and send_confirmation has 71, while search_alternatives went from "search" to 480.**

hold_seat reads "Place a 15-minute hold on one alternative. Reversible. It simply expires." and send_confirmation reads "Send the customer a written confirmation of what was just done. Benign." Neither says when to call it, what the argument comes from, or what comes back. The detail you added to search_alternatives ("pass the option_id the customer chooses to hold_seat") has no counterpart on hold_seat's side. None of the 10 schemas has been checked against any case where the model picks the wrong tool.

Run python3 run.py --show-tools and paste the hold_seat and send_confirmation entries beside the search_alternatives entry.

**2. agent.py search_alternatives still has input_schema properties of only {"pnr": {"type": "string"}}, with no description on the argument.**

You rewrote the tool description from "search" to 480 characters, but the schema block under it is unchanged. check_policy takes cause_code, delay_minutes and status, and those three have no description or example either, only an enum on two of them. A larger model reads the same schema and has the same gaps.

Run python3 run.py --all --trace and paste the tool_use inputs for every check_policy and search_alternatives call.

**3. The only committed wire run, readout-trace.json, shows 0 cache reads, 0 writes and 16468 input tokens across 4 turns.**

agent.py has no cache_control anywhere. runtime_preamble() + SYSTEM_PROMPT + TONE_ADDENDUM and all 10 tool schemas go out on each of the 4 turns, so the same prefix is paid for four times in that run. The trace reads 11.3s wall clock, 1071 output tokens, hit ratio None. Nobody has measured what a different model would cost or save against that baseline.

Run python3 run.py --tool-tax and paste its output next to the totals footer of python3 run.py --all --trace.

**4. There is no evals/cases.json, and the one run in readout-trace.json covers one booking: lookup_booking through search_alternatives, 5 calls.**

The trace stops at search_alternatives. hold_seat, issue_voucher, escalate_to_human and send_confirmation never appear in it. The banked gates are 1.2, 1.3, 1.4 and 2.1, and 2.2, 3.1 and 4.1 are not banked. So the repository does not yet show a single case where the agent escalated a group, partner, minor or SSR booking, or declined a refund.

Run python3 verify.py 2.2 and python3 verify.py 3.1 and paste both outputs.

**5. agent.py loops while stop_reason == "tool_use" and turns < MAX_TOOL_CALLS (8), and the loop returns text_of(response) with no check on why it ended.**

Your diff changed the loop to append response.content and to return the final turn's text. If the cap of 8 is reached on a tool_use turn, text_of() returns the last text block, which can be empty, and nothing escalates. The committed run used 4 turns for a booking that never reached hold_seat. A booking that needs hold, policy, voucher and confirmation can approach 8. Pick a model without knowing how often that happens and you are guessing.

Run python3 run.py --all --trace and paste the API turns count for every booking, flagging any that hit 8.

## Your four answers

The four lines under `## Priya asked` in your PITCH.md are still empty. They
are one line each and they are not a coding job: cost, what happens when it is
wrong, who runs it in June, and what you left out. Whoever on your side is not
editing agent.py is the right person to write them, and they are the four
things I will ask about first.

## Before our next meeting

> Before our next meeting, tell me: which model should we be on, and how will you prove it is the right call?
>
> Priya Raghavan, Larkspur Airlines

Bring two things. A recommendation, and the measurement behind it. If the model is
not the problem, say so, and bring the number that shows it.

## What this review read

- `agent.py (276 lines)`
- `PITCH.md (unchanged template)`
- `TEAM.md`
- `readout-trace.json`
- `readout.html (evidence block)`

Reviewer: `claude-sonnet-5-5`. Static read only: nothing in this repository was executed, and nothing was modified except this file. Larkspur Airlines is a fictional training scenario. Confidential, do not distribute.
