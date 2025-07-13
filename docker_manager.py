"""
Docker-based virtual environment manager for Cappuccino agent.
Provides isolated execution environments for code execution and system operations.
"""

import docker
import logging
import os
import tempfile
import time
from typing import Any, Dict
from pathlib import Path

logger = logging.getLogger(__name__)


class DockerManager:
    """Manages Docker containers for isolated code execution and system operations."""
    
    def __init__(self, base_image: str = "cappuccino-env:latest"):
        """
        Initialize Docker manager.
        
        Args:
            base_image: Base Docker image to use for containers
        """
        self.base_image = base_image
        self.client = docker.from_env()
        self.containers: Dict[str, docker.models.containers.Container] = {}
        
        # Ensure base image exists
        self._ensure_base_image()
    
    def _ensure_base_image(self) -> None:
        """Ensure the base image exists, build if necessary."""
        try:
            self.client.images.get(self.base_image)
            logger.info(f"Base image {self.base_image} found")
        except docker.errors.ImageNotFound:
            logger.info(f"Base image {self.base_image} not found, building...")
            self._build_base_image()
    
    def _build_base_image(self) -> None:
        """Build the base Docker image with Ubuntu and Python."""
        dockerfile_content = """
FROM ubuntu:22.04

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    python3.10 \\
    python3-pip \\
    git \\
    curl \\
    vim \\
    nano \\
    wget \\
    unzip \\
    build-essential \\
    --no-install-recommends && \\
    rm -rf /var/lib/apt/lists/*

# Set up Python alternatives
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.10 1
RUN update-alternatives --install /usr/bin/pip pip /usr/bin/pip3 1

# Install common Python packages
RUN pip install --no-cache-dir \\
    requests \\
    beautifulsoup4 \\
    pandas \\
    numpy \\
    matplotlib \\
    seaborn \\
    jupyter \\
    ipython

# Create working directory
WORKDIR /workspace

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

CMD ["/bin/bash"]
"""
        
        # Create temporary directory for build context
        with tempfile.TemporaryDirectory() as temp_dir:
            dockerfile_path = Path(temp_dir) / "Dockerfile"
            dockerfile_path.write_text(dockerfile_content)
            
            logger.info("Building base image...")
            image, build_logs = self.client.images.build(
                path=temp_dir,
                tag=self.base_image,
                rm=True
            )
            
            for log in build_logs:
                if 'stream' in log:
                    logger.debug(log['stream'].strip())
            
            logger.info(f"Base image {self.base_image} built successfully")
    
    def create_container(self, container_name: str, **kwargs) -> Dict[str, Any]:
        """
        Create a new container.
        
        Args:
            container_name: Unique name for the container
            **kwargs: Additional arguments for container creation
            
        Returns:
            Dict containing container information
        """
        try:
            if container_name in self.containers:
                return {"error": f"Container {container_name} already exists"}
            
            # Default container configuration
            config = {
                "image": self.base_image,
                "name": container_name,
                "detach": True,
                "tty": True,
                "stdin_open": True,
                "working_dir": "/workspace",
                "mem_limit": "1g",  # Limit memory to 1GB
                "cpu_quota": 50000,  # Limit CPU to 50% of one core
                "network_mode": "bridge",  # Allow network access but isolated
                "remove": False,  # Don't auto-remove
            }
            
            # Update with user-provided kwargs
            config.update(kwargs)
            
            container = self.client.containers.create(**config)
            self.containers[container_name] = container
            
            logger.info(f"Container {container_name} created successfully")
            return {
                "success": True,
                "container_id": container.id,
                "container_name": container_name,
                "status": container.status
            }
            
        except Exception as e:
            logger.error(f"Failed to create container {container_name}: {e}")
            return {"error": str(e)}
    
    def start_container(self, container_name: str) -> Dict[str, Any]:
        """
        Start a container.
        
        Args:
            container_name: Name of the container to start
            
        Returns:
            Dict containing operation result
        """
        try:
            if container_name not in self.containers:
                return {"error": f"Container {container_name} not found"}
            
            container = self.containers[container_name]
            container.start()
            
            # Wait a moment for container to fully start
            time.sleep(1)
            container.reload()
            
            logger.info(f"Container {container_name} started successfully")
            return {
                "success": True,
                "container_name": container_name,
                "status": container.status
            }
            
        except Exception as e:
            logger.error(f"Failed to start container {container_name}: {e}")
            return {"error": str(e)}
    
    def stop_container(self, container_name: str) -> Dict[str, Any]:
        """
        Stop a container.
        
        Args:
            container_name: Name of the container to stop
            
        Returns:
            Dict containing operation result
        """
        try:
            if container_name not in self.containers:
                return {"error": f"Container {container_name} not found"}
            
            container = self.containers[container_name]
            container.stop()
            
            logger.info(f"Container {container_name} stopped successfully")
            return {
                "success": True,
                "container_name": container_name,
                "status": "stopped"
            }
            
        except Exception as e:
            logger.error(f"Failed to stop container {container_name}: {e}")
            return {"error": str(e)}
    
    def remove_container(self, container_name: str, force: bool = False) -> Dict[str, Any]:
        """
        Remove a container.
        
        Args:
            container_name: Name of the container to remove
            force: Whether to force removal of running container
            
        Returns:
            Dict containing operation result
        """
        try:
            if container_name not in self.containers:
                return {"error": f"Container {container_name} not found"}
            
            container = self.containers[container_name]
            container.remove(force=force)
            
            del self.containers[container_name]
            
            logger.info(f"Container {container_name} removed successfully")
            return {
                "success": True,
                "container_name": container_name,
                "status": "removed"
            }
            
        except Exception as e:
            logger.error(f"Failed to remove container {container_name}: {e}")
            return {"error": str(e)}
    
    def execute_command(self, container_name: str, command: str, 
                       working_dir: str = "/workspace") -> Dict[str, Any]:
        """
        Execute a command in a container.
        
        Args:
            container_name: Name of the container
            command: Command to execute
            working_dir: Working directory for command execution
            
        Returns:
            Dict containing command output and exit code
        """
        try:
            if container_name not in self.containers:
                return {"error": f"Container {container_name} not found"}
            
            container = self.containers[container_name]
            
            # Ensure container is running
            container.reload()
            if container.status != "running":
                return {"error": f"Container {container_name} is not running"}
            
            # Execute command
            exec_result = container.exec_run(
                cmd=command,
                workdir=working_dir,
                demux=True,
                tty=False
            )
            
            # Decode output
            stdout = exec_result.output[0].decode('utf-8') if exec_result.output[0] else ""
            stderr = exec_result.output[1].decode('utf-8') if exec_result.output[1] else ""
            
            logger.info(f"Command executed in {container_name}: {command}")
            return {
                "success": True,
                "exit_code": exec_result.exit_code,
                "stdout": stdout,
                "stderr": stderr,
                "command": command,
                "working_dir": working_dir
            }
            
        except Exception as e:
            logger.error(f"Failed to execute command in {container_name}: {e}")
            return {"error": str(e)}
    
    def put_file(self, container_name: str, local_path: str, 
                 container_path: str) -> Dict[str, Any]:
        """
        Copy a file from host to container.
        
        Args:
            container_name: Name of the container
            local_path: Path to file on host
            container_path: Destination path in container
            
        Returns:
            Dict containing operation result
        """
        try:
            if container_name not in self.containers:
                return {"error": f"Container {container_name} not found"}
            
            container = self.containers[container_name]
            
            if not os.path.exists(local_path):
                return {"error": f"Local file {local_path} not found"}
            
            # Create tar archive of the file
            with tempfile.NamedTemporaryFile() as tar_file:
                import tarfile
                with tarfile.open(tar_file.name, 'w') as tar:
                    tar.add(local_path, arcname=os.path.basename(container_path))
                
                tar_file.seek(0)
                tar_data = tar_file.read()
            
            # Extract to container
            container_dir = os.path.dirname(container_path)
            container.put_archive(container_dir, tar_data)
            
            logger.info(f"File copied to {container_name}: {local_path} -> {container_path}")
            return {
                "success": True,
                "local_path": local_path,
                "container_path": container_path
            }
            
        except Exception as e:
            logger.error(f"Failed to copy file to {container_name}: {e}")
            return {"error": str(e)}
    
    def get_file(self, container_name: str, container_path: str, 
                 local_path: str) -> Dict[str, Any]:
        """
        Copy a file from container to host.
        
        Args:
            container_name: Name of the container
            container_path: Path to file in container
            local_path: Destination path on host
            
        Returns:
            Dict containing operation result
        """
        try:
            if container_name not in self.containers:
                return {"error": f"Container {container_name} not found"}
            
            container = self.containers[container_name]
            
            # Get tar archive from container
            tar_stream, _ = container.get_archive(container_path)
            
            # Extract tar data
            tar_data = b''.join(tar_stream)
            
            # Extract file from tar
            with tempfile.NamedTemporaryFile() as tar_file:
                tar_file.write(tar_data)
                tar_file.seek(0)
                
                import tarfile
                with tarfile.open(tar_file.name, 'r') as tar:
                    tar.extractall(path=os.path.dirname(local_path))
            
            logger.info(f"File copied from {container_name}: {container_path} -> {local_path}")
            return {
                "success": True,
                "container_path": container_path,
                "local_path": local_path
            }
            
        except Exception as e:
            logger.error(f"Failed to copy file from {container_name}: {e}")
            return {"error": str(e)}
    
    def list_containers(self) -> Dict[str, Any]:
        """
        List all managed containers.
        
        Returns:
            Dict containing list of containers and their status
        """
        try:
            container_info = []
            for name, container in self.containers.items():
                container.reload()
                container_info.append({
                    "name": name,
                    "id": container.id,
                    "status": container.status,
                    "image": container.image.tags[0] if container.image.tags else "unknown"
                })
            
            return {
                "success": True,
                "containers": container_info
            }
            
        except Exception as e:
            logger.error(f"Failed to list containers: {e}")
            return {"error": str(e)}
    
    def get_container_logs(self, container_name: str, tail: int = 100) -> Dict[str, Any]:
        """
        Get logs from a container.
        
        Args:
            container_name: Name of the container
            tail: Number of lines to retrieve from the end
            
        Returns:
            Dict containing container logs
        """
        try:
            if container_name not in self.containers:
                return {"error": f"Container {container_name} not found"}
            
            container = self.containers[container_name]
            logs = container.logs(tail=tail).decode('utf-8')
            
            return {
                "success": True,
                "container_name": container_name,
                "logs": logs
            }
            
        except Exception as e:
            logger.error(f"Failed to get logs from {container_name}: {e}")
            return {"error": str(e)}
    
    def cleanup_all(self) -> Dict[str, Any]:
        """
        Stop and remove all managed containers.
        
        Returns:
            Dict containing cleanup results
        """
        try:
            results = []
            for container_name in list(self.containers.keys()):
                # Stop container
                stop_result = self.stop_container(container_name)
                # Remove container
                remove_result = self.remove_container(container_name, force=True)
                
                results.append({
                    "container_name": container_name,
                    "stop_result": stop_result,
                    "remove_result": remove_result
                })
            
            logger.info("All containers cleaned up")
            return {
                "success": True,
                "results": results
            }
            
        except Exception as e:
            logger.error(f"Failed to cleanup containers: {e}")
            return {"error": str(e)}

