# PITCH.md

Six lines and a lever. Your words. The last two are scored.

Built: A support agent for disrupted flights. It uses Larkspur's nine tools, eight more that we wrote over Larkspur's own files (for example seats_left and cause_in_plain_words), and two served by Larkspur's MCP server: next_available_day and fare_rules.
Does: It finds the booking, checks what happened to the flight and what Larkspur's policy owes the customer, lists the flights that still have seats, and explains the rule in the Handbook's own words when the customer asks why.
Number: 76,770 to 143,703 tokens in, total of the five tickets. The first run had the nine tools; the second had our ten tools added, and the tool list alone is 5,479 tokens on every turn.
Safety check: It never books a new flight by itself. In the trace for K7PQ2M it listed three flights, called neither hold_seat nor confirm_rebooking, and told the customer that only their own Confirm click finalizes a booking.
Next: Make next_available_day count everyone on the booking. Today it answers for one passenger, so the date it gives may not work for a family or a group.
Still broken: The agent does nothing different for an angry customer who threatens legal action (ticket R8KD3F). Our tone instructions are empty, and that ticket ran as a normal resolution.
Lever: <cost | speed | intelligence>

## Priya asked

Costs:
Wrong:
Runs it:
Left out:
