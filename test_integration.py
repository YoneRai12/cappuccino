"""
Integration test script for Cappuccino agent with Docker and Discord features.
Tests the new virtual environment and Discord integration capabilities.
"""

import os
import sys
import time
import logging
from typing import Dict, Any

import pytest

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

docker = pytest.importorskip("docker")
discord = pytest.importorskip("discord")

try:
    docker.from_env()
except docker.errors.DockerException:
    pytest.skip("Docker daemon not available")

from docker_tools import DOCKER_TOOLS
from discord_tools import DISCORD_TOOLS

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IntegrationTester:
    """Integration tester for new Cappuccino features."""
    
    def __init__(self):
        self.test_results = []
        self.container_name = "test-cappuccino-env"
    
    def log_test_result(self, test_name: str, success: bool, message: str = ""):
        """Log test result."""
        result = {
            "test": test_name,
            "success": success,
            "message": message,
            "timestamp": time.time()
        }
        self.test_results.append(result)
        
        status = "PASS" if success else "FAIL"
        logger.info(f"[{status}] {test_name}: {message}")
    
    def test_docker_functionality(self) -> bool:
        """Test Docker container management functionality."""
        logger.info("=== Testing Docker Functionality ===")
        
        try:
            # Test 1: Container creation
            result = DOCKER_TOOLS["container_create"](container_name=self.container_name)
            if "error" in result:
                self.log_test_result("Docker Container Creation", False, result["error"])
                return False
            self.log_test_result("Docker Container Creation", True, "Container created successfully")
            
            # Test 2: Container start
            result = DOCKER_TOOLS["container_start"](self.container_name)
            if "error" in result:
                self.log_test_result("Docker Container Start", False, result["error"])
                return False
            self.log_test_result("Docker Container Start", True, "Container started successfully")
            
            # Wait for container to be ready
            time.sleep(2)
            
            # Test 3: Command execution
            result = DOCKER_TOOLS["container_exec"](
                self.container_name, 
                "python --version"
            )
            if "error" in result:
                self.log_test_result("Docker Command Execution", False, result["error"])
                return False
            
            if result.get("exit_code") == 0:
                self.log_test_result("Docker Command Execution", True, 
                                   f"Python version: {result.get('stdout', '').strip()}")
            else:
                self.log_test_result("Docker Command Execution", False, 
                                   f"Command failed: {result.get('stderr', '')}")
                return False
            
            # Test 4: File operations
            # Create a test file on host
            test_file_content = "Hello from Cappuccino agent!"
            test_file_path = "/tmp/test_cappuccino.txt"
            
            with open(test_file_path, "w") as f:
                f.write(test_file_content)
            
            # Copy file to container
            result = DOCKER_TOOLS["container_put_file"](
                self.container_name,
                test_file_path,
                "/workspace/test_file.txt"
            )
            if "error" in result:
                self.log_test_result("Docker File Upload", False, result["error"])
                return False
            self.log_test_result("Docker File Upload", True, "File uploaded successfully")
            
            # Read file in container
            result = DOCKER_TOOLS["container_exec"](
                self.container_name,
                "cat /workspace/test_file.txt"
            )
            if "error" in result or result.get("exit_code") != 0:
                self.log_test_result("Docker File Read", False, "Failed to read file in container")
                return False
            
            if test_file_content in result.get("stdout", ""):
                self.log_test_result("Docker File Read", True, "File content verified")
            else:
                self.log_test_result("Docker File Read", False, "File content mismatch")
                return False
            
            # Test 5: Python code execution
            python_code = """
import sys
import os
print(f"Python version: {sys.version}")
print(f"Current directory: {os.getcwd()}")
print(f"Available packages:")
import pkg_resources
for pkg in sorted(pkg_resources.working_set, key=lambda x: x.project_name):
    print(f"  {pkg.project_name}: {pkg.version}")
"""
            
            # Write Python code to file
            code_file_path = "/tmp/test_code.py"
            with open(code_file_path, "w") as f:
                f.write(python_code)
            
            # Copy to container
            DOCKER_TOOLS["container_put_file"](
                self.container_name,
                code_file_path,
                "/workspace/test_code.py"
            )
            
            # Execute Python code
            result = DOCKER_TOOLS["container_exec"](
                self.container_name,
                "python /workspace/test_code.py"
            )
            
            if "error" in result or result.get("exit_code") != 0:
                self.log_test_result("Docker Python Execution", False, 
                                   f"Python execution failed: {result.get('stderr', '')}")
                return False
            
            self.log_test_result("Docker Python Execution", True, 
                               "Python code executed successfully")
            
            # Test 6: Container listing
            result = DOCKER_TOOLS["container_list"]()
            if "error" in result:
                self.log_test_result("Docker Container Listing", False, result["error"])
                return False
            
            containers = result.get("containers", [])
            test_container_found = any(c["name"] == self.container_name for c in containers)
            
            if test_container_found:
                self.log_test_result("Docker Container Listing", True, 
                                   f"Found {len(containers)} containers")
            else:
                self.log_test_result("Docker Container Listing", False, 
                                   "Test container not found in list")
                return False
            
            return True
            
        except Exception as e:
            self.log_test_result("Docker Functionality", False, f"Exception: {str(e)}")
            return False
    
    def test_discord_functionality(self) -> bool:
        """Test Discord integration functionality."""
        logger.info("=== Testing Discord Functionality ===")
        
        # Check if Discord token is available
        discord_token = os.getenv('DISCORD_BOT_TOKEN')
        if not discord_token:
            self.log_test_result("Discord Token Check", False, 
                               "DISCORD_BOT_TOKEN environment variable not set")
            logger.warning("Skipping Discord tests - no token provided")
            return True  # Not a failure, just skipped
        
        try:
            # Test 1: Discord status check (before starting)
            result = DISCORD_TOOLS["discord_get_status"]()
            if "error" in result:
                self.log_test_result("Discord Status Check", False, result["error"])
                return False
            
            status = result.get("status", {})
            if not status.get("is_running"):
                self.log_test_result("Discord Status Check", True, "Bot not running (expected)")
            else:
                self.log_test_result("Discord Status Check", True, "Bot already running")
            
            # Test 2: Start Discord bot
            result = DISCORD_TOOLS["discord_start_bot"]()
            if "error" in result:
                self.log_test_result("Discord Bot Start", False, result["error"])
                return False
            
            self.log_test_result("Discord Bot Start", True, "Bot start initiated")
            
            # Wait for bot to connect
            time.sleep(5)
            
            # Test 3: Check bot status after start
            result = DISCORD_TOOLS["discord_get_status"]()
            if "error" in result:
                self.log_test_result("Discord Bot Status After Start", False, result["error"])
                return False
            
            status = result.get("status", {})
            if status.get("is_running"):
                self.log_test_result("Discord Bot Status After Start", True, 
                                   f"Bot running as {status.get('bot_user')}")
            else:
                self.log_test_result("Discord Bot Status After Start", False, 
                                   "Bot failed to start")
                return False
            
            # Test 4: Get events (should be empty initially)
            result = DISCORD_TOOLS["discord_get_events"](max_events=5)
            if "error" in result:
                self.log_test_result("Discord Event Retrieval", False, result["error"])
                return False
            
            events = result.get("events", [])
            self.log_test_result("Discord Event Retrieval", True, 
                               f"Retrieved {len(events)} events")
            
            # Test 5: Stop Discord bot
            result = DISCORD_TOOLS["discord_stop_bot"]()
            if "error" in result:
                self.log_test_result("Discord Bot Stop", False, result["error"])
                return False
            
            self.log_test_result("Discord Bot Stop", True, "Bot stopped successfully")
            
            return True
            
        except Exception as e:
            self.log_test_result("Discord Functionality", False, f"Exception: {str(e)}")
            return False
    
    def cleanup_docker_resources(self):
        """Clean up Docker test resources."""
        logger.info("=== Cleaning up Docker resources ===")
        
        try:
            # Stop and remove test container
            DOCKER_TOOLS["container_stop"](self.container_name)
            result = DOCKER_TOOLS["container_remove"](self.container_name, force=True)
            
            if "error" not in result:
                logger.info("Test container cleaned up successfully")
            else:
                logger.warning(f"Container cleanup warning: {result['error']}")
                
        except Exception as e:
            logger.warning(f"Cleanup exception: {e}")
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all integration tests."""
        logger.info("Starting Cappuccino integration tests...")
        
        start_time = time.time()
        
        # Run Docker tests
        docker_success = self.test_docker_functionality()
        
        # Run Discord tests
        discord_success = self.test_discord_functionality()
        
        # Cleanup
        self.cleanup_docker_resources()
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Calculate results
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r["success"])
        failed_tests = total_tests - passed_tests
        
        overall_success = docker_success and discord_success
        
        summary = {
            "overall_success": overall_success,
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "duration_seconds": duration,
            "docker_tests_passed": docker_success,
            "discord_tests_passed": discord_success,
            "detailed_results": self.test_results
        }
        
        logger.info("=== Test Summary ===")
        logger.info(f"Overall: {'PASS' if overall_success else 'FAIL'}")
        logger.info(f"Tests: {passed_tests}/{total_tests} passed")
        logger.info(f"Duration: {duration:.2f} seconds")
        logger.info(f"Docker: {'PASS' if docker_success else 'FAIL'}")
        logger.info(f"Discord: {'PASS' if discord_success else 'FAIL'}")
        
        return summary


def main():
    """Main test function."""
    tester = IntegrationTester()
    results = tester.run_all_tests()
    
    # Exit with appropriate code
    exit_code = 0 if results["overall_success"] else 1
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

