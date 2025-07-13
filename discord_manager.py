"""
Discord manager for Cappuccino agent.
Provides Discord integration for autonomous agent interactions.
"""

import discord
from discord.ext import commands
import asyncio
import logging
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
import threading
import queue

logger = logging.getLogger(__name__)


class DiscordManager:
    """Manages Discord bot interactions for Cappuccino agent."""
    
    def __init__(self, bot_token: str, command_prefix: str = "!"):
        """
        Initialize Discord manager.
        
        Args:
            bot_token: Discord bot token
            command_prefix: Command prefix for bot commands
        """
        self.bot_token = bot_token
        self.command_prefix = command_prefix
        
        # Set up intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.guild_messages = True
        intents.direct_messages = True
        
        # Create bot instance
        self.bot = commands.Bot(command_prefix=command_prefix, intents=intents)
        
        # Event queue for agent processing
        self.event_queue = queue.Queue()
        
        # Message handlers
        self.message_handlers: List[Callable] = []
        
        # Bot status
        self.is_running = False
        self.bot_thread = None
        
        # Setup event handlers
        self._setup_event_handlers()
    
    def _setup_event_handlers(self):
        """Set up Discord event handlers."""
        
        @self.bot.event
        async def on_ready():
            logger.info(f'Discord bot logged in as {self.bot.user} (ID: {self.bot.user.id})')
            self.is_running = True
            
            # Add ready event to queue
            self.event_queue.put({
                "type": "bot_ready",
                "user": str(self.bot.user),
                "user_id": self.bot.user.id,
                "timestamp": datetime.now().isoformat()
            })
        
        @self.bot.event
        async def on_message(message):
            # Ignore messages from the bot itself
            if message.author.id == self.bot.user.id:
                return
            
            # Create message event
            message_event = {
                "type": "message",
                "content": message.content,
                "author": str(message.author),
                "author_id": message.author.id,
                "channel": str(message.channel),
                "channel_id": message.channel.id,
                "guild": str(message.guild) if message.guild else None,
                "guild_id": message.guild.id if message.guild else None,
                "timestamp": message.created_at.isoformat(),
                "message_id": message.id
            }
            
            # Add to event queue
            self.event_queue.put(message_event)
            
            # Call registered message handlers
            for handler in self.message_handlers:
                try:
                    await handler(message_event)
                except Exception as e:
                    logger.error(f"Message handler error: {e}")
            
            # Process commands
            await self.bot.process_commands(message)
        
        @self.bot.event
        async def on_reaction_add(reaction, user):
            if user.id == self.bot.user.id:
                return
            
            reaction_event = {
                "type": "reaction_add",
                "emoji": str(reaction.emoji),
                "user": str(user),
                "user_id": user.id,
                "message_id": reaction.message.id,
                "channel_id": reaction.message.channel.id,
                "timestamp": datetime.now().isoformat()
            }
            
            self.event_queue.put(reaction_event)
        
        @self.bot.event
        async def on_member_join(member):
            join_event = {
                "type": "member_join",
                "user": str(member),
                "user_id": member.id,
                "guild": str(member.guild),
                "guild_id": member.guild.id,
                "timestamp": datetime.now().isoformat()
            }
            
            self.event_queue.put(join_event)
        
        @self.bot.event
        async def on_member_remove(member):
            leave_event = {
                "type": "member_leave",
                "user": str(member),
                "user_id": member.id,
                "guild": str(member.guild),
                "guild_id": member.guild.id,
                "timestamp": datetime.now().isoformat()
            }
            
            self.event_queue.put(leave_event)
    
    def add_message_handler(self, handler: Callable):
        """
        Add a message handler function.
        
        Args:
            handler: Async function to handle message events
        """
        self.message_handlers.append(handler)
    
    def start_bot(self):
        """Start the Discord bot in a separate thread."""
        if self.is_running:
            logger.warning("Bot is already running")
            return
        
        def run_bot():
            try:
                asyncio.run(self.bot.start(self.bot_token))
            except Exception as e:
                logger.error(f"Bot startup failed: {e}")
                self.is_running = False
        
        self.bot_thread = threading.Thread(target=run_bot, daemon=True)
        self.bot_thread.start()
        logger.info("Discord bot started in background thread")
    
    def stop_bot(self):
        """Stop the Discord bot."""
        if not self.is_running:
            logger.warning("Bot is not running")
            return
        
        asyncio.run_coroutine_threadsafe(self.bot.close(), self.bot.loop)
        self.is_running = False
        logger.info("Discord bot stopped")
    
    def get_events(self, max_events: int = 10) -> List[Dict[str, Any]]:
        """
        Get events from the event queue.
        
        Args:
            max_events: Maximum number of events to retrieve
            
        Returns:
            List of event dictionaries
        """
        events = []
        for _ in range(max_events):
            try:
                event = self.event_queue.get_nowait()
                events.append(event)
            except queue.Empty:
                break
        
        return events
    
    async def send_message(self, channel_id: int, content: str, 
                          embed: Optional[discord.Embed] = None) -> Dict[str, Any]:
        """
        Send a message to a Discord channel.
        
        Args:
            channel_id: ID of the channel to send message to
            content: Message content
            embed: Optional embed object
            
        Returns:
            Dict containing send result
        """
        try:
            channel = self.bot.get_channel(channel_id)
            if not channel:
                return {"error": f"Channel {channel_id} not found"}
            
            message = await channel.send(content=content, embed=embed)
            
            return {
                "success": True,
                "message_id": message.id,
                "channel_id": channel_id,
                "content": content
            }
            
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return {"error": str(e)}
    
    async def get_channel_messages(self, channel_id: int, 
                                  limit: int = 10) -> Dict[str, Any]:
        """
        Get recent messages from a channel.
        
        Args:
            channel_id: ID of the channel
            limit: Number of messages to retrieve
            
        Returns:
            Dict containing messages
        """
        try:
            channel = self.bot.get_channel(channel_id)
            if not channel:
                return {"error": f"Channel {channel_id} not found"}
            
            messages = []
            async for message in channel.history(limit=limit):
                messages.append({
                    "id": message.id,
                    "content": message.content,
                    "author": str(message.author),
                    "author_id": message.author.id,
                    "timestamp": message.created_at.isoformat(),
                    "attachments": [att.url for att in message.attachments]
                })
            
            return {
                "success": True,
                "channel_id": channel_id,
                "messages": messages
            }
            
        except Exception as e:
            logger.error(f"Failed to get messages: {e}")
            return {"error": str(e)}
    
    async def get_channel_info(self, channel_id: int) -> Dict[str, Any]:
        """
        Get information about a channel.
        
        Args:
            channel_id: ID of the channel
            
        Returns:
            Dict containing channel information
        """
        try:
            channel = self.bot.get_channel(channel_id)
            if not channel:
                return {"error": f"Channel {channel_id} not found"}
            
            channel_info = {
                "id": channel.id,
                "name": channel.name,
                "type": str(channel.type),
                "guild": str(channel.guild) if hasattr(channel, 'guild') else None,
                "guild_id": channel.guild.id if hasattr(channel, 'guild') else None,
                "topic": getattr(channel, 'topic', None),
                "member_count": len(channel.members) if hasattr(channel, 'members') else None
            }
            
            return {
                "success": True,
                "channel_info": channel_info
            }
            
        except Exception as e:
            logger.error(f"Failed to get channel info: {e}")
            return {"error": str(e)}
    
    async def get_user_info(self, user_id: int) -> Dict[str, Any]:
        """
        Get information about a user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            Dict containing user information
        """
        try:
            user = self.bot.get_user(user_id)
            if not user:
                # Try to fetch user
                user = await self.bot.fetch_user(user_id)
            
            if not user:
                return {"error": f"User {user_id} not found"}
            
            user_info = {
                "id": user.id,
                "name": user.name,
                "display_name": user.display_name,
                "discriminator": user.discriminator,
                "avatar_url": str(user.avatar.url) if user.avatar else None,
                "bot": user.bot,
                "created_at": user.created_at.isoformat()
            }
            
            return {
                "success": True,
                "user_info": user_info
            }
            
        except Exception as e:
            logger.error(f"Failed to get user info: {e}")
            return {"error": str(e)}
    
    async def add_reaction(self, channel_id: int, message_id: int, 
                          emoji: str) -> Dict[str, Any]:
        """
        Add a reaction to a message.
        
        Args:
            channel_id: ID of the channel
            message_id: ID of the message
            emoji: Emoji to add as reaction
            
        Returns:
            Dict containing reaction result
        """
        try:
            channel = self.bot.get_channel(channel_id)
            if not channel:
                return {"error": f"Channel {channel_id} not found"}
            
            message = await channel.fetch_message(message_id)
            if not message:
                return {"error": f"Message {message_id} not found"}
            
            await message.add_reaction(emoji)
            
            return {
                "success": True,
                "channel_id": channel_id,
                "message_id": message_id,
                "emoji": emoji
            }
            
        except Exception as e:
            logger.error(f"Failed to add reaction: {e}")
            return {"error": str(e)}
    
    async def get_guild_info(self, guild_id: int) -> Dict[str, Any]:
        """
        Get information about a guild (server).
        
        Args:
            guild_id: ID of the guild
            
        Returns:
            Dict containing guild information
        """
        try:
            guild = self.bot.get_guild(guild_id)
            if not guild:
                return {"error": f"Guild {guild_id} not found"}
            
            guild_info = {
                "id": guild.id,
                "name": guild.name,
                "description": guild.description,
                "member_count": guild.member_count,
                "owner": str(guild.owner),
                "owner_id": guild.owner_id,
                "created_at": guild.created_at.isoformat(),
                "channels": [{"id": ch.id, "name": ch.name, "type": str(ch.type)} 
                           for ch in guild.channels],
                "roles": [{"id": role.id, "name": role.name} for role in guild.roles]
            }
            
            return {
                "success": True,
                "guild_info": guild_info
            }
            
        except Exception as e:
            logger.error(f"Failed to get guild info: {e}")
            return {"error": str(e)}
    
    def get_bot_status(self) -> Dict[str, Any]:
        """
        Get current bot status.
        
        Returns:
            Dict containing bot status information
        """
        return {
            "is_running": self.is_running,
            "bot_user": str(self.bot.user) if self.bot.user else None,
            "bot_id": self.bot.user.id if self.bot.user else None,
            "guild_count": len(self.bot.guilds) if self.is_running else 0,
            "latency": self.bot.latency if self.is_running else None
        }

