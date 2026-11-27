# Demo call results

## Checking availability without booking

**Scenario:** `do_not_book_yet`

**Goal:** Check whether the patient can ask about an appointment without
accidentally agreeing to book it.

### How to run the demo

1. Start the patient agent and run `python make_call.py --scenario do_not_book_yet`.
2. Answer the destination phone and say, “Thanks for calling. How can I help you?”
3. When the patient asks about availability, say, “I have Tuesday at 2 p.m.
   Would you like me to book it?”
4. Let the patient respond. Answer any follow-up questions, then end the call.

### What to check

- Did the patient clearly decline to book the offered time?
- Did the patient ask how to book later or whether the slot would be held?
- Before ending, did the patient confirm that no appointment had been booked?

### Observed result

Pending a demo call. After running it, add the patient's actual response
to the booking offer and note which checks passed or failed.