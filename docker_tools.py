"""
Docker tools for Cappuccino agent.
Provides tools for managing Docker containers through the ToolManager.
"""

from typing import Any, Dict
from docker_manager import DockerManager
import logging

logger = logging.getLogger(__name__)

# Global Docker manager instance
try:
    docker_manager = DockerManager()
except Exception as exc:  # pragma: no cover - environment without Docker
    docker_manager = None
    logging.warning(f"DockerManager unavailable: {exc}")


def container_create(image_name: str = None, container_name: str = "cappuccino-env", 
                    **kwargs) -> Dict[str, Any]:
    """
    Create a new Docker container.
    
    Args:
        image_name: Docker image to use (defaults to base image)
        container_name: Name for the container
        **kwargs: Additional container configuration
        
    Returns:
        Dict containing creation result
    """
    try:
        if image_name:
            kwargs['image'] = image_name
        
        result = docker_manager.create_container(container_name, **kwargs)
        logger.info(f"Container creation tool called: {container_name}")
        return result
    except Exception as e:
        logger.error(f"Container creation failed: {e}")
        return {"error": str(e)}


def container_start(container_name: str) -> Dict[str, Any]:
    """
    Start a Docker container.
    
    Args:
        container_name: Name of the container to start
        
    Returns:
        Dict containing start result
    """
    try:
        result = docker_manager.start_container(container_name)
        logger.info(f"Container start tool called: {container_name}")
        return result
    except Exception as e:
        logger.error(f"Container start failed: {e}")
        return {"error": str(e)}


def container_stop(container_name: str) -> Dict[str, Any]:
    """
    Stop a Docker container.
    
    Args:
        container_name: Name of the container to stop
        
    Returns:
        Dict containing stop result
    """
    try:
        result = docker_manager.stop_container(container_name)
        logger.info(f"Container stop tool called: {container_name}")
        return result
    except Exception as e:
        logger.error(f"Container stop failed: {e}")
        return {"error": str(e)}


def container_remove(container_name: str, force: bool = False) -> Dict[str, Any]:
    """
    Remove a Docker container.
    
    Args:
        container_name: Name of the container to remove
        force: Whether to force removal of running container
        
    Returns:
        Dict containing removal result
    """
    try:
        result = docker_manager.remove_container(container_name, force)
        logger.info(f"Container remove tool called: {container_name}")
        return result
    except Exception as e:
        logger.error(f"Container removal failed: {e}")
        return {"error": str(e)}


def container_exec(container_name: str, command: str, 
                  working_dir: str = "/workspace") -> Dict[str, Any]:
    """
    Execute a command in a Docker container.
    
    Args:
        container_name: Name of the container
        command: Command to execute
        working_dir: Working directory for command execution
        
    Returns:
        Dict containing command execution result
    """
    try:
        result = docker_manager.execute_command(container_name, command, working_dir)
        logger.info(f"Container exec tool called: {container_name} - {command}")
        return result
    except Exception as e:
        logger.error(f"Container command execution failed: {e}")
        return {"error": str(e)}


def container_put_file(container_name: str, local_path: str, 
                      container_path: str) -> Dict[str, Any]:
    """
    Copy a file from host to container.
    
    Args:
        container_name: Name of the container
        local_path: Path to file on host
        container_path: Destination path in container
        
    Returns:
        Dict containing file copy result
    """
    try:
        result = docker_manager.put_file(container_name, local_path, container_path)
        logger.info(f"Container put file tool called: {local_path} -> {container_name}:{container_path}")
        return result
    except Exception as e:
        logger.error(f"Container file copy failed: {e}")
        return {"error": str(e)}


def container_get_file(container_name: str, container_path: str, 
                      local_path: str) -> Dict[str, Any]:
    """
    Copy a file from container to host.
    
    Args:
        container_name: Name of the container
        container_path: Path to file in container
        local_path: Destination path on host
        
    Returns:
        Dict containing file copy result
    """
    try:
        result = docker_manager.get_file(container_name, container_path, local_path)
        logger.info(f"Container get file tool called: {container_name}:{container_path} -> {local_path}")
        return result
    except Exception as e:
        logger.error(f"Container file copy failed: {e}")
        return {"error": str(e)}


def container_list() -> Dict[str, Any]:
    """
    List all managed containers.
    
    Returns:
        Dict containing list of containers
    """
    try:
        result = docker_manager.list_containers()
        logger.info("Container list tool called")
        return result
    except Exception as e:
        logger.error(f"Container listing failed: {e}")
        return {"error": str(e)}


def container_logs(container_name: str, tail: int = 100) -> Dict[str, Any]:
    """
    Get logs from a container.
    
    Args:
        container_name: Name of the container
        tail: Number of lines to retrieve from the end
        
    Returns:
        Dict containing container logs
    """
    try:
        result = docker_manager.get_container_logs(container_name, tail)
        logger.info(f"Container logs tool called: {container_name}")
        return result
    except Exception as e:
        logger.error(f"Container logs retrieval failed: {e}")
        return {"error": str(e)}


def container_cleanup_all() -> Dict[str, Any]:
    """
    Stop and remove all managed containers.
    
    Returns:
        Dict containing cleanup results
    """
    try:
        result = docker_manager.cleanup_all()
        logger.info("Container cleanup all tool called")
        return result
    except Exception as e:
        logger.error(f"Container cleanup failed: {e}")
        return {"error": str(e)}


# Tool registration for ToolManager
DOCKER_TOOLS = {
    "container_create": container_create,
    "container_start": container_start,
    "container_stop": container_stop,
    "container_remove": container_remove,
    "container_exec": container_exec,
    "container_put_file": container_put_file,
    "container_get_file": container_get_file,
    "container_list": container_list,
    "container_logs": container_logs,
    "container_cleanup_all": container_cleanup_all,
}

