# Patient Voice Tester

A Python voice bot that acts as a fictional patient and calls a test receptionist.
I built it to test appointment requests, insurance questions, medication refill requests,
and changes in what the caller asks for.

# How it works

The Patient voice bot uses LiveKit Agents with separate speech-to-text (STT), language model (LLM),
and text-to-speech (TTS) components:

- AssemblyAI transcribes the receptionist.
- Gemma generates the patient's responses.
- Fish Audio turns those responses into speech.
- Twilio connects the LiveKit session to the phone line.

`scenarios.py` contains the shared patient instructions and the individual test scenarios.
`make_call.py` selects a scenario, creates a room, dispatches the patient agent, and places the call.
`patient_agent.py` runs the conversation and saves a JSON session report when it ends.

I separated the scenarios from the agent and call setup so I could change
the test case without rewriting the conversation code. The call script waits
for the patient agent to be ready before dialing so it can hear the opening
greeting. The agent uses LiveKit inference to transcribe the receptionist,
generate the patient's reply, and turn that reply into speech.

Turn-taking required the most adjustment. In early tests, the patient bot
sometimes interrupted the greeting or ended the call before the receptionist
finished. I reviewed recordings and transcripts, then adjusted the greeting
checks and patient instructions. The phrase-based checks depend on the transcription
matching expected wording, so they can miss variations. I focused on listening for delays
and interruptions rather than measuring latency.

# Files

- `patient_agent.py` - patient behavior and conversation handling
- `make_call.py` - outbound call setup and cleanup
- `scenarios.py` - patient identity and scenario instructions
- `check_connection.py` - checks LiveKit API access
- `requirements.txt` - Python dependencies
- `results.md` - demo steps / checklist for testing whether the patient declines to book an appointment
- `transcripts/` - created locally when the agent saves a session report

# Testing

The patient simulator includes scenarios for scheduling, rescheduling,
cancellations, refill requests, insurance questions, and office hours.

For a first demo, try `do_not_book_yet`. Offer the patient an appointment
and ask whether to book it. The patient should ask about availability
and decline to authorize a booking. See [the demo checklist](results.md)
for the steps and space to record what actually happened.

To review your own test call, open its JSON report in `transcripts/`

# Setup

I developed this project on macOS using Python 3.13

You need a LiveKit Cloud project and an outbound SIP trunk connected
to Twilio. The trunk must allow the Twilio number you set as
`OUTBOUND_CALLER_NUMBER` in your local `.env`.

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Create your local configuration:

```bash
cp .env.example .env
```

Fill in `.env` with your LiveKit URL, API key, API secret, and
LiveKit outbound trunk ID. Do not commit this file.

Check the connection:

```bash
python check_connection.py
```

# Run a call

In one terminal, activate the environment and start the agent:

```bash
source .venv/bin/activate
python patient_agent.py dev
```

Wait for the worker to register. Then in a second terminal,
from the same project folder, run:

```bash
source .venv/bin/activate
python make_call.py --scenario office_hours
```

To list the available scenarios:

```bash
python make_call.py --help
```

Set `OUTBOUND_CALLER_NUMBER` in your local `.env` to your Twilio number.
Set `TEST_DESTINATION_NUMBER` to a number you control, such as your own
cell phone. When you run a scenario, answer that phone and play the
receptionist.

Running a call incurs API and telephony charges.

The installed SDK warns that `dev` is deprecated, but this is the
command used for these tests. Restart the agent after changing code
or scenario instructions.

# Reviewing a call

After a session ends, `patient_agent.py` saves a JSON report in
`transcripts/`. Open the report and compare what the patient actually
said with the instructions for that scenario in `scenarios.py`