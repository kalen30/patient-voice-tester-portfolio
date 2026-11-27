from dotenv import load_dotenv

from livekit import agents
from livekit.agents import AgentServer, AgentSession, Agent, inference, room_io, TurnHandlingOptions, JobContext
from livekit.agents import RunContext, get_job_context
from livekit.agents.llm import ChatContext, ChatMessage, StopResponse
from scenarios import build_instructions

import json
from datetime import datetime, timezone
from pathlib import Path

load_dotenv(".env")

class Patient(Agent):
        def __init__(self, scenario_name: str) -> None:
            self._greeting_finished = False
            self._greeting_text = ""

            super().__init__(
            instructions=build_instructions(scenario_name),
            )

        async def end_call(self, ctx: RunContext) -> None:
            """End the call only after the receptionist has finished,
            the patient's goal or next steps are clear, and all
            outstanding questions have been answered.
            This tool speaks the goodbye; do not say one separately.
            """
            if ctx.session.user_state == "speaking":
                return
            
            await ctx.wait_for_playout()
            
            goodbye = ctx.session.say(
                "Thank you for your help. Goodbye.",
                allow_interruptions=False,
            )

            await goodbye.wait_for_playout()

            await get_job_context().delete_room()

        async def on_user_turn_completed(
            self,
            turn_ctx: ChatContext,
            new_message: ChatMessage,
        ) -> None:
            print(
                "GREETING GATE:",
                self._greeting_finished,
                repr(new_message.text_content),
                flush=True
            )

            incoming = " ".join(
                (new_message.text_content or "").lower().split()
            )

            if self._greeting_finished:
                waiting_phrases = (
                    "let me check",
                    "let me look",
                    "i'm checking",
                    "i am checking",
                    "please hold",
                    "one moment",
                    "just a moment",
                )

                asks_question = (
                    "?" in incoming
                    or "may i have" in incoming
                    or "could you" in incoming
                    or "can you" in incoming
                    or "please provide" in incoming
                )

                if (
                    any(phrase in incoming for phrase in waiting_phrases)
                    and not asks_question
                ):
                    print("Office is checking; patient stays silent.")
                    raise StopResponse()
                
                return 
            
            self._greeting_text += " " + incoming
            text = " ".join(self._greeting_text.split())

            greeting_phrases = (
                "how can i help",
                "how may i help",
                "how can we help",
                "how may we help",
                "how can i assist",
                "how may i assist",
            )

            if any(phrase in text for phrase in greeting_phrases):
                self._greeting_finished = True
                print("Receptionist greeting detected, patient can respond.")
                return
                
            print("Waiting for receptionist; opening reply succeeded.")
            raise StopResponse()

server = AgentServer()

async def on_session_end(ctx: JobContext) -> None:
    report = ctx.make_session_report()
    report_dict = report.to_dict()
    metadata = json.loads(ctx.job.metadata or "{}")
    scenario_name = metadata.get("scenario", "office_hours")

    report_dict["test_context"] = {
        "scenario": scenario_name,
        "room_name": ctx.room.name,
        "instructions": build_instructions(scenario_name),
    }

    output_dir = Path(__file__).resolve().parent / "transcripts"
    output_dir.mkdir(parents=True, exist_ok = True)

    current_date = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = output_dir / f"{scenario_name}_{current_date}.json"

    with open(filename, 'w', encoding="utf-8") as f:
        json.dump(report_dict, f, indent=2, ensure_ascii=False)

    print(f"Session report for {ctx.room.name} saved to {filename}")


@server.rtc_session(agent_name="patient_simulator", on_session_end=on_session_end)
async def my_agent(ctx: agents.JobContext):
    metadata = json.loads(ctx.job.metadata or "{}")
    scenario_name = metadata.get("scenario", "office_hours")

    build_instructions(scenario_name)
    print(f"Starting patient scenarios : {scenario_name}")
    session = AgentSession(
        stt=inference.STT(model="assemblyai/universal-3-6-pro", language="en"),
        llm=inference.LLM(model="google/gemma-4-31b-it"),
        tts=inference.TTS(
            model="fishaudio/s2.1-pro",
            voice="fa4c9eb3dccc4806b382b40d61c6b10a",
        ),
        turn_handling=TurnHandlingOptions(
            turn_detection=inference.TurnDetector(),
        ),
    )

    await session.start(
        room=ctx.room,
        agent=Patient(scenario_name),
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=None,
            ),
        ),
    )

    if ctx.room.isconnected():
        await ctx.room.local_participant.set_attributes(
            {"patient.ready" : "true"}
        )

if __name__ == "__main__":
    agents.cli.run_app(server)