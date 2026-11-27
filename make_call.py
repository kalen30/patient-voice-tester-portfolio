import asyncio
import os
import argparse
import json
from scenarios import SCENARIOS

from datetime import datetime, timezone
from aiohttp import ClientTimeout
from google.protobuf.duration_pb2 import Duration

from dotenv import load_dotenv
from livekit import api
from livekit.api.twirp_client import ServerError

load_dotenv(".env")

AGENT_NAME = "patient_simulator"
MAX_CALL_SECONDS = 300


async def wait_for_patient(lkapi, room_name):
    async with asyncio.timeout(30):
        while True:
            result = await lkapi.room.list_participants(
                api.ListParticipantsRequest(room=room_name)
            )

            for participant in result.participants:
                if participant.attributes.get("patient.ready") == "true":
                    print("Patient session is ready.")
                    return

            await asyncio.sleep(1)


async def main(scenario_name: str):
    trunk_id = os.environ["SIP_OUTBOUND_TRUNK_ID"]
    caller_number = os.getenv("OUTBOUND_CALLER_NUMBER", "").strip()
    destination_number = os.getenv("TEST_DESTINATION_NUMBER", "").strip()

    if not caller_number or not destination_number:
        raise ValueError(
            "Set OUTBOUND_CALLER_NUMBER and TEST_DESTINATION_NUMBER "
            "in your local .env file before placing a call."
        )

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    room_name = f"patient-call-{scenario_name}-{timestamp}"
    room_created = False

    async with api.LiveKitAPI(
        timeout=ClientTimeout(total=60)
    ) as lkapi: 
        try:
            await lkapi.room.create_room(
                api.CreateRoomRequest(name=room_name)
            )
            room_created = True
            print(f"Created room:  {room_name}")

            await lkapi.agent_dispatch.create_dispatch(
                api.CreateAgentDispatchRequest(
                    agent_name=AGENT_NAME,
                    room=room_name,
                    metadata=json.dumps({"scenario": scenario_name}),
                )
            )
            print(f"Requested agent: {AGENT_NAME}")

            await wait_for_patient(lkapi, room_name)

            print("Calling the configured test number")

            await lkapi.sip.create_sip_participant(
                api.CreateSIPParticipantRequest(
                    sip_trunk_id=trunk_id,
                    sip_call_to=destination_number,
                    sip_number=caller_number,
                    room_name=room_name,
                    participant_identity="clinic",
                    participant_name="Demo receptionist",
                    wait_until_answered=True,
                    ringing_timeout=Duration(seconds=45),
                    max_call_duration=Duration(seconds=MAX_CALL_SECONDS)
                )
            )

            print(f"Call answered. Watching for the call to end.")

            deadline = asyncio.get_running_loop().time() + MAX_CALL_SECONDS

            while asyncio.get_running_loop().time() < deadline:
                try:
                    participants = await lkapi.room.list_participants(
                        api.ListParticipantsRequest(room=room_name)
                    )
                except ServerError as error:
                    if error.code == "not_found":
                        print("Room already closed; call ended.")
                        break
                    raise

                clinic_present = any(
                    participant.identity == "clinic"
                    for participant in participants.participants
                )

                if not clinic_present:
                    print(f"Clinic disconnected.")
                    break

                await asyncio.sleep(1)

        finally: 
            if room_created:
                try:
                    await lkapi.room.delete_room(
                        api.DeleteRoomRequest(room=room_name)
                    )
                    print("Room closed.")
                except ServerError as error:
                    if error.code != "not_found":
                        raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run one patient test call."
    )
    parser.add_argument(
        "--scenario",
        required=True,
        choices=sorted(SCENARIOS),
        help="Patient scenarios to run.",
    )
    args = parser.parse_args()

    asyncio.run(main(args.scenario))