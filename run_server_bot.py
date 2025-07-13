import asyncio
import uvicorn

from api import app
from discordbot.bot import start_bot

async def start_server():
    config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()

async def main():
    await asyncio.gather(start_server(), start_bot())

if __name__ == "__main__":
    asyncio.run(main())
