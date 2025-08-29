import random
import os
import shlex
import subprocess
import time
import argparse
import yaml
import logging


#scmd = shlex.split(command)

scmd = ['docker exec docker-geo_service_container-1 /bin/sh -c \"cd /anomaly ; stress-ng --cpu 2 --timeout 30s --metrics-brief\"']
print(scmd)
subprocess.Popen(scmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
