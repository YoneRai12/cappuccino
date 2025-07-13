"""
Discord tools for Cappuccino agent.
Provides tools for Discord interactions through the ToolManager.
"""

import asyncio
from typing import Any, Dict, Optional
from discord_manager import DiscordManager
import logging
import os

logger = logging.getLogger(__name__)

# Global Discord manager instance
discord_manager: Optional[DiscordManager] = None


def _ensure_discord_manager():
    """Ensure Discord manager is initialized."""
    global discord_manager
    if discord_manager is None:
        bot_token = os.getenv('DISCORD_BOT_TOKEN')
        if not bot_token:
            raise ValueError("DISCORD_BOT_TOKEN environment variable not set")
        discord_manager = DiscordManager(bot_token)
    return discord_manager


def _run_async(coro):
    """Run async function in sync context."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If loop is already running, create a new task
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, coro)
                return future.result()
        else:
            return loop.run_until_complete(coro)
    except RuntimeError:
        # No event loop, create new one
        return asyncio.run(coro)


def discord_start_bot() -> Dict[str, Any]:
    """
    Start the Discord bot.
    
    Returns:
        Dict containing start result
    """
    try:
        manager = _ensure_discord_manager()
        manager.start_bot()
        
        logger.info("Discord bot start tool called")
        return {
            "success": True,
            "message": "Discord bot started successfully"
        }
    except Exception as e:
        logger.error(f"Discord bot start failed: {e}")
        return {"error": str(e)}


def discord_stop_bot() -> Dict[str, Any]:
    """
    Stop the Discord bot.
    
    Returns:
        Dict containing stop result
    """
    try:
        if discord_manager:
            discord_manager.stop_bot()
        
        logger.info("Discord bot stop tool called")
        return {
            "success": True,
            "message": "Discord bot stopped successfully"
        }
    except Exception as e:
        logger.error(f"Discord bot stop failed: {e}")
        return {"error": str(e)}


def discord_get_status() -> Dict[str, Any]:
    """
    Get Discord bot status.
    
    Returns:
        Dict containing bot status
    """
    try:
        if discord_manager:
            status = discord_manager.get_bot_status()
            logger.info("Discord status tool called")
            return {
                "success": True,
                "status": status
            }
        else:
            return {
                "success": True,
                "status": {
                    "is_running": False,
                    "bot_user": None,
                    "bot_id": None,
                    "guild_count": 0,
                    "latency": None
                }
            }
    except Exception as e:
        logger.error(f"Discord status check failed: {e}")
        return {"error": str(e)}


def discord_send_message(channel_id: int, content: str) -> Dict[str, Any]:
    """
    Send a message to a Discord channel.
    
    Args:
        channel_id: ID of the channel to send message to
        content: Message content
        
    Returns:
        Dict containing send result
    """
    try:
        manager = _ensure_discord_manager()
        result = _run_async(manager.send_message(channel_id, content))
        
        logger.info(f"Discord send message tool called: channel {channel_id}")
        return result
    except Exception as e:
        logger.error(f"Discord send message failed: {e}")
        return {"error": str(e)}


def discord_get_channel_messages(channel_id: int, limit: int = 10) -> Dict[str, Any]:
    """
    Get recent messages from a Discord channel.
    
    Args:
        channel_id: ID of the channel
        limit: Number of messages to retrieve
        
    Returns:
        Dict containing messages
    """
    try:
        manager = _ensure_discord_manager()
        result = _run_async(manager.get_channel_messages(channel_id, limit))
        
        logger.info(f"Discord get messages tool called: channel {channel_id}")
        return result
    except Exception as e:
        logger.error(f"Discord get messages failed: {e}")
        return {"error": str(e)}


def discord_get_channel_info(channel_id: int) -> Dict[str, Any]:
    """
    Get information about a Discord channel.
    
    Args:
        channel_id: ID of the channel
        
    Returns:
        Dict containing channel information
    """
    try:
        manager = _ensure_discord_manager()
        result = _run_async(manager.get_channel_info(channel_id))
        
        logger.info(f"Discord get channel info tool called: channel {channel_id}")
        return result
    except Exception as e:
        logger.error(f"Discord get channel info failed: {e}")
        return {"error": str(e)}


def discord_get_user_info(user_id: int) -> Dict[str, Any]:
    """
    Get information about a Discord user.
    
    Args:
        user_id: ID of the user
        
    Returns:
        Dict containing user information
    """
    try:
        manager = _ensure_discord_manager()
        result = _run_async(manager.get_user_info(user_id))
        
        logger.info(f"Discord get user info tool called: user {user_id}")
        return result
    except Exception as e:
        logger.error(f"Discord get user info failed: {e}")
        return {"error": str(e)}


def discord_add_reaction(channel_id: int, message_id: int, emoji: str) -> Dict[str, Any]:
    """
    Add a reaction to a Discord message.
    
    Args:
        channel_id: ID of the channel
        message_id: ID of the message
        emoji: Emoji to add as reaction
        
    Returns:
        Dict containing reaction result
    """
    try:
        manager = _ensure_discord_manager()
        result = _run_async(manager.add_reaction(channel_id, message_id, emoji))
        
        logger.info(f"Discord add reaction tool called: message {message_id}")
        return result
    except Exception as e:
        logger.error(f"Discord add reaction failed: {e}")
        return {"error": str(e)}


def discord_get_guild_info(guild_id: int) -> Dict[str, Any]:
    """
    Get information about a Discord guild (server).
    
    Args:
        guild_id: ID of the guild
        
    Returns:
        Dict containing guild information
    """
    try:
        manager = _ensure_discord_manager()
        result = _run_async(manager.get_guild_info(guild_id))
        
        logger.info(f"Discord get guild info tool called: guild {guild_id}")
        return result
    except Exception as e:
        logger.error(f"Discord get guild info failed: {e}")
        return {"error": str(e)}


def discord_get_events(max_events: int = 10) -> Dict[str, Any]:
    """
    Get recent Discord events from the event queue.
    
    Args:
        max_events: Maximum number of events to retrieve
        
    Returns:
        Dict containing events
    """
    try:
        if discord_manager:
            events = discord_manager.get_events(max_events)
            logger.info(f"Discord get events tool called: {len(events)} events")
            return {
                "success": True,
                "events": events,
                "event_count": len(events)
            }
        else:
            return {
                "success": True,
                "events": [],
                "event_count": 0
            }
    except Exception as e:
        logger.error(f"Discord get events failed: {e}")
        return {"error": str(e)}


# Tool registration for ToolManager
DISCORD_TOOLS = {
    "discord_start_bot": discord_start_bot,
    "discord_stop_bot": discord_stop_bot,
    "discord_get_status": discord_get_status,
    "discord_send_message": discord_send_message,
    "discord_get_channel_messages": discord_get_channel_messages,
    "discord_get_channel_info": discord_get_channel_info,
    "discord_get_user_info": discord_get_user_info,
    "discord_add_reaction": discord_add_reaction,
    "discord_get_guild_info": discord_get_guild_info,
    "discord_get_events": discord_get_events,
}

