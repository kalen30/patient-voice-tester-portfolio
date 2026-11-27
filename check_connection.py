import asyncio
from livekit import api
from dotenv import dotenv_values

config = dotenv_values(".env")

async def main():
    lkapi = api.LiveKitAPI(
        url=config["LIVEKIT_URL"],
        api_key=config["LIVEKIT_API_KEY"],
        api_secret=config["LIVEKIT_API_SECRET"],
    )

    try:    
        results = await lkapi.room.list_rooms(api.ListRoomsRequest())
        print(f"Connection successful. Active rooms: {len(results.rooms)}")
    finally:
        await lkapi.aclose()

asyncio.run(main())