#!/usr/bin/env python3
"""
GPU Monitor - Real-time GPU status monitoring
"""

import subprocess
import time
import json
import os
import sys
from datetime import datetime
from typing import Dict, Any, List

def get_gpu_status() -> Dict[str, Any]:
    """Get current GPU status using nvidia-smi"""
    try:
        # Check if nvidia-smi is available
        result = subprocess.run(['nvidia-smi', '--version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode != 0:
            return {"error": "nvidia-smi not available"}
        
        # Get GPU info
        gpu_info = subprocess.run(['nvidia-smi', '--query-gpu=index,name,memory.used,memory.total,utilization.gpu,temperature.gpu', 
                                  '--format=csv,noheader,nounits'], 
                                 capture_output=True, text=True, timeout=5)
        
        if gpu_info.returncode != 0:
            return {"error": "Failed to get GPU info"}
        
        gpu_data = []
        for line in gpu_info.stdout.strip().split('\n'):
            if line.strip():
                parts = line.split(', ')
                if len(parts) >= 6:
                    gpu_data.append({
                        "index": parts[0],
                        "name": parts[1],
                        "memory_used_mb": int(parts[2]),
                        "memory_total_mb": int(parts[3]),
                        "utilization_percent": int(parts[4]),
                        "temperature_c": int(parts[5]),
                        "memory_usage_percent": round((int(parts[2]) / int(parts[3])) * 100, 1)
                    })
        
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "gpu_count": len(gpu_data),
            "gpu_info": gpu_data
        }
        
    except Exception as e:
        return {"error": str(e)}


def get_gpu_processes() -> Dict[str, Any]:
    """Get processes using GPU"""
    try:
        result = subprocess.run(['nvidia-smi', 'pmon', '-c', '1'], 
                              capture_output=True, text=True, timeout=5)
        
        if result.returncode != 0:
            return {"error": "Failed to get processes"}
        
        return {
            "status": "success",
            "processes": result.stdout
        }
        
    except Exception as e:
        return {"error": str(e)}


def clear_screen():
    """Clear the terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')


def print_gpu_status(gpu_status: Dict[str, Any]):
    """Print GPU status in a formatted way"""
    if "error" in gpu_status:
        print(f"❌ Error: {gpu_status['error']}")
        return
    
    print("=" * 80)
    print(f"🖥️  GPU Status Monitor - {gpu_status.get('timestamp', 'Unknown')}")
    print("=" * 80)
    
    for gpu in gpu_status.get('gpu_info', []):
        print(f"\n🎮 GPU {gpu['index']}: {gpu['name']}")
        print(f"   💾 Memory: {gpu['memory_used_mb']}MB / {gpu['memory_total_mb']}MB ({gpu['memory_usage_percent']}%)")
        print(f"   ⚡ Utilization: {gpu['utilization_percent']}%")
        print(f"   🌡️  Temperature: {gpu['temperature_c']}°C")
        
        # Memory usage bar
        bar_length = 30
        used_length = int((gpu['memory_usage_percent'] / 100) * bar_length)
        bar = "█" * used_length + "░" * (bar_length - used_length)
        print(f"   📊 [{bar}] {gpu['memory_usage_percent']}%")


def print_processes(processes_data: Dict[str, Any]):
    """Print GPU processes"""
    if "error" in processes_data:
        print(f"❌ Process Error: {processes_data['error']}")
        return
    
    print("\n" + "=" * 80)
    print("🔄 GPU Processes")
    print("=" * 80)
    
    lines = processes_data.get('processes', '').strip().split('\n')
    if len(lines) <= 2:
        print("   No processes using GPU")
    else:
        for line in lines[2:]:  # Skip header lines
            if line.strip():
                print(f"   {line}")


def main():
    """Main monitoring loop"""
    print("🚀 Starting GPU Monitor...")
    print("Press Ctrl+C to exit")
    
    try:
        while True:
            clear_screen()
            
            # Get GPU status
            gpu_status = get_gpu_status()
            print_gpu_status(gpu_status)
            
            # Get processes
            processes_data = get_gpu_processes()
            print_processes(processes_data)
            
            print(f"\n⏰ Last updated: {datetime.now().strftime('%H:%M:%S')}")
            print("🔄 Refreshing in 5 seconds... (Ctrl+C to exit)")
            
            time.sleep(5)
            
    except KeyboardInterrupt:
        print("\n👋 GPU Monitor stopped.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 