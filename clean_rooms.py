import os
import asyncio
from dotenv import load_dotenv
import aiohttp

load_dotenv(override=True)

async def cleanup():
    daily_api_key = os.getenv("DAILY_API_KEY", "")
    daily_api_url = os.getenv("DAILY_API_URL", "https://api.daily.co/v1")

    headers = {
        "Authorization": f"Bearer {daily_api_key}",
        "Content-Type": "application/json"
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(f"{daily_api_url}/rooms") as response:
            if response.status == 200:
                rooms_response = await response.json()
                rooms = rooms_response.get("data", [])
                print("Rooms found:", rooms)
                for room in rooms:
                    room_name = room.get("name")
                    if room_name:
                        print(f"Deleting room: {room_name}")
                        async with session.delete(f"{daily_api_url}/rooms/{room_name}") as delete_response:
                            if delete_response.status == 204:
                                print(f"Room '{room_name}' deleted successfully.")
                            else:
                                print(f"Failed to delete room '{room_name}'. Status code: {delete_response.status}")
            else:
                print(f"Failed to list rooms. Status code: {response.status}")

asyncio.run(cleanup())
