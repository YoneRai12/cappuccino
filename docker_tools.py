"""
Docker tools for Cappuccino agent.
Provides tools for managing Docker containers through the ToolManager.
"""

from typing import Any, Dict, Optional
from docker_manager import DockerManager
import logging
import subprocess
import json
import os

logger = logging.getLogger(__name__)

# Global Docker manager instance
try:
    docker_manager = DockerManager()
except Exception as exc:  # pragma: no cover - environment without Docker
    docker_manager = None
    logging.warning(f"DockerManager unavailable: {exc}")


def nvidia_smi_status() -> Dict[str, Any]:
    """
    Get NVIDIA GPU status using nvidia-smi.
    
    Returns:
        Dict containing GPU status information
    """
    try:
        # Check if nvidia-smi is available
        result = subprocess.run(['nvidia-smi', '--version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            return {"error": "nvidia-smi not available or NVIDIA drivers not installed"}
        
        # Get basic GPU info
        gpu_info = subprocess.run(['nvidia-smi', '--query-gpu=index,name,memory.used,memory.total,utilization.gpu,temperature.gpu', 
                                  '--format=csv,noheader,nounits'], 
                                 capture_output=True, text=True, timeout=10)
        
        # Get running processes
        processes = subprocess.run(['nvidia-smi', 'pmon', '-c', '1'], 
                                 capture_output=True, text=True, timeout=10)
        
        # Parse GPU info
        gpu_data = []
        if gpu_info.returncode == 0:
            for line in gpu_info.stdout.strip().split('\n'):
                if line.strip():
                    parts = line.split(', ')
                    if len(parts) >= 6:
                        gpu_data.append({
                            "index": parts[0],
                            "name": parts[1],
                            "memory_used_mb": parts[2],
                            "memory_total_mb": parts[3],
                            "utilization_percent": parts[4],
                            "temperature_c": parts[5]
                        })
        
        return {
            "status": "success",
            "gpu_count": len(gpu_data),
            "gpu_info": gpu_data,
            "processes": processes.stdout if processes.returncode == 0 else "Failed to get processes"
        }
        
    except subprocess.TimeoutExpired:
        return {"error": "nvidia-smi command timed out"}
    except Exception as e:
        logger.error(f"nvidia_smi_status failed: {e}")
        return {"error": str(e)}


def nvidia_smi_memory_usage() -> Dict[str, Any]:
    """
    Get detailed GPU memory usage information.
    
    Returns:
        Dict containing memory usage details
    """
    try:
        result = subprocess.run(['nvidia-smi', '--query-gpu=index,name,memory.used,memory.total,memory.free', 
                               '--format=csv,noheader,nounits'], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode != 0:
            return {"error": "Failed to get memory usage"}
        
        memory_data = []
        for line in result.stdout.strip().split('\n'):
            if line.strip():
                parts = line.split(', ')
                if len(parts) >= 5:
                    memory_data.append({
                        "gpu_index": parts[0],
                        "name": parts[1],
                        "used_mb": int(parts[2]),
                        "total_mb": int(parts[3]),
                        "free_mb": int(parts[4]),
                        "usage_percent": round((int(parts[2]) / int(parts[3])) * 100, 1)
                    })
        
        return {
            "status": "success",
            "memory_usage": memory_data
        }
        
    except Exception as e:
        logger.error(f"nvidia_smi_memory_usage failed: {e}")
        return {"error": str(e)}


def nvidia_smi_processes() -> Dict[str, Any]:
    """
    Get detailed information about processes using GPU.
    
    Returns:
        Dict containing process information
    """
    try:
        result = subprocess.run(['nvidia-smi', 'pmon', '-c', '1'], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode != 0:
            return {"error": "Failed to get process information"}
        
        return {
            "status": "success",
            "processes": result.stdout
        }
        
    except Exception as e:
        logger.error(f"nvidia_smi_processes failed: {e}")
        return {"error": str(e)}


def nvidia_smi_kill_process(pid: int) -> Dict[str, Any]:
    """
    Kill a process using GPU by PID.
    
    Args:
        pid: Process ID to kill
        
    Returns:
        Dict containing kill result
    """
    try:
        result = subprocess.run(['taskkill', '/PID', str(pid), '/F'], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            return {"status": "success", "message": f"Process {pid} killed successfully"}
        else:
            return {"error": f"Failed to kill process {pid}: {result.stderr}"}
        
    except Exception as e:
        logger.error(f"nvidia_smi_kill_process failed: {e}")
        return {"error": str(e)}


def nvidia_smi_clear_memory() -> Dict[str, Any]:
    """
    Attempt to clear GPU memory by killing processes that might be holding it.
    
    Returns:
        Dict containing clear result
    """
    try:
        # Get processes using GPU
        processes_result = nvidia_smi_processes()
        if "error" in processes_result:
            return processes_result
        
        killed_processes = []
        lines = processes_result["processes"].strip().split('\n')
        
        # Skip header lines
        for line in lines[2:]:  # Skip first two header lines
            if line.strip():
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        pid = int(parts[1])
                        # Try to kill the process
                        kill_result = nvidia_smi_kill_process(pid)
                        if "status" in kill_result and kill_result["status"] == "success":
                            killed_processes.append(pid)
                    except ValueError:
                        continue
        
        return {
            "status": "success",
            "killed_processes": killed_processes,
            "message": f"Attempted to kill {len(killed_processes)} processes"
        }
        
    except Exception as e:
        logger.error(f"nvidia_smi_clear_memory failed: {e}")
        return {"error": str(e)}


def container_create(image_name: Optional[str] = None, container_name: str = "cappuccino-env", 
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
        if docker_manager is None:
            return {"error": "Docker manager not available"}
        
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
        if docker_manager is None:
            return {"error": "Docker manager not available"}
        
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
        if docker_manager is None:
            return {"error": "Docker manager not available"}
        
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
        if docker_manager is None:
            return {"error": "Docker manager not available"}
        
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
        if docker_manager is None:
            return {"error": "Docker manager not available"}
        
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
        if docker_manager is None:
            return {"error": "Docker manager not available"}
        
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
        if docker_manager is None:
            return {"error": "Docker manager not available"}
        
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
        if docker_manager is None:
            return {"error": "Docker manager not available"}
        
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
        if docker_manager is None:
            return {"error": "Docker manager not available"}
        
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
        if docker_manager is None:
            return {"error": "Docker manager not available"}
        
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
    # NVIDIA GPU monitoring tools
    "nvidia_smi_status": nvidia_smi_status,
    "nvidia_smi_memory_usage": nvidia_smi_memory_usage,
    "nvidia_smi_processes": nvidia_smi_processes,
    "nvidia_smi_kill_process": nvidia_smi_kill_process,
    "nvidia_smi_clear_memory": nvidia_smi_clear_memory,
}

