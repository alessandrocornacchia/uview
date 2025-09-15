"""
    This script distributes commands coming from standard input to all available cores
    on the machine. It is useful to run experiments for different parameters in parallel.

    Author: Alessandro Cornacchia
"""

import subprocess
from multiprocessing import Pool
import sys

def run_command(command):
    subprocess.run(command, shell=True)

# Read commands from standard input
commands = sys.stdin.read().splitlines()

# Run commands in parallel using multiple cores
with Pool() as pool:
    pool.map(run_command, commands)
