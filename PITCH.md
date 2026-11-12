# PITCH.md

Six lines and a lever. Your words. The last two are scored.

Built: A support agent for disrupted flights. It uses Larkspur's nine tools, eight more that we wrote over Larkspur's own files (for example seats_left and cause_in_plain_words), and two served by Larkspur's MCP server: next_available_day and fare_rules.
Does: It finds the booking, checks what happened to the flight and what Larkspur's policy owes the customer, lists the flights that still have seats, and explains the rule in the Handbook's own words when the customer asks why.
Number: 76,770 to 143,703 tokens in, total of the five tickets. The first run had the nine tools; the second had our ten tools added, and the tool list alone is 5,479 tokens on every turn.
Safety check: It never books a new flight by itself. In the trace for K7PQ2M it listed three flights, called neither hold_seat nor confirm_rebooking, and told the customer that only their own Confirm click finalizes a booking.
Next: Make next_available_day count everyone on the booking. Today it answers for one passenger, so the date it gives may not work for a family or a group.
Still broken: The agent does nothing different for an angry customer who threatens legal action (ticket R8KD3F). Our tone instructions are empty, and that ticket ran as a normal resolution.
Lever: cost

## Priya asked

Costs: About $0.03 per conversation, against $6.90 for a person. That is the model cost only, at list price: $0.0961 before we turned on prompt caching and $0.0324 after, each measured over 15 conversations. It leaves out hosting and testing, so the full cost is higher.
Wrong: Today a person finds out by reading the trace, which shows every tool the agent called and what came back. We have no automatic test cases yet, so nothing flags a wrong sentence by itself. The customer is protected on the steps that cannot be undone: a booking needs their own Confirm click, and refunds, hotels and groups go to a person. Ticket G2HL9V went to the group queue in our run.
Runs it: Not decided. Nobody is named yet to watch, fix or update the agent after our team leaves. What they would own is one file, agent.py, with the loop and seventeen tool descriptions; next_available_day and fare_rules live in Larkspur's own MCP server.
Left out: Refunds, hotel approval and groups of 10 or more, because the Handbook keeps them with people, so the agent hands over. Special handling for angry customers, because we have not written the tone instructions.
