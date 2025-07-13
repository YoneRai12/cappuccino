import aio_pika
from typing import AsyncIterator, Optional


class QueueManager:
    """Simple RabbitMQ wrapper for distributed task handling."""

    def __init__(self, url: str = "amqp://guest:guest@localhost/") -> None:
        self.url = url
        self.connection: Optional[aio_pika.RobustConnection] = None
        self.channel: Optional[aio_pika.abc.AbstractChannel] = None

    async def connect(self) -> None:
        """Establish connection and channel."""
        self.connection = await aio_pika.connect_robust(self.url)
        self.channel = await self.connection.channel()

    async def close(self) -> None:
        """Close connection if open."""
        if self.connection:
            await self.connection.close()
            self.connection = None
            self.channel = None

    async def publish(self, queue_name: str, message: str) -> None:
        """Publish a message to the queue."""
        if not self.channel:
            raise RuntimeError("QueueManager not connected")
        await self.channel.default_exchange.publish(
            aio_pika.Message(body=message.encode()), routing_key=queue_name
        )

    async def consume(self, queue_name: str) -> AsyncIterator[str]:
        """Yield messages from the queue."""
        if not self.channel:
            raise RuntimeError("QueueManager not connected")
        queue = await self.channel.declare_queue(queue_name, durable=True)
        async with queue.iterator() as it:
            async for msg in it:
                async with msg.process():
                    yield msg.body.decode()
