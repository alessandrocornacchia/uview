#!/usr/bin/env python3
# thread_verification.py

" Demonstrates CPU affinity and thread ID verification in Python. "

import os
import threading
import time
import subprocess
import sys

def verify_thread_id(cpu_core):
    """Verify thread ID and pin to specific CPU core"""
    # Get Python's thread ID
    python_thread_id = threading.get_native_id()
    
    # Get process ID
    pid = os.getpid()

    print(f"Thread {cpu_core} PID: {pid}")
    
    print(f"Thread Python ID: {threading.current_thread().name}")
    print(f"Thread Native ID from Python: {python_thread_id}")

    # Pin to specified CPU core
    os.sched_setaffinity(0, {cpu_core})

    time.sleep(5)  # Sleep to simulate work
    
    
def main():
    # Get the number of available CPU cores
    num_cores = os.cpu_count()
    print(f"System has {num_cores} CPU cores available")
    print(f"Main process ID: {os.getpid()}")
    print(f"Main thread native ID: {threading.get_native_id()}")
    print("-" * 50)
    
    # Create threads and assign each to a different CPU core
    threads = []
    for i in range(min(4, num_cores)):  # Create up to 4 threads
        t = threading.Thread(
            target=verify_thread_id,
            args=(i,),
            name=f"Thread-{i}"
        )
        threads.append(t)
        t.daemon = True
        t.start()
    
    os.system(f"ps -mo pid,tid,%cpu,psr -p {os.getpid()}")
    
    # Wait for all threads to complete
    for t in threads:
        t.join()
        
    print("\nVerification complete!")
    
if __name__ == "__main__":
    main()