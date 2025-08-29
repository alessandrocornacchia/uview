import time
from locust import HttpUser, task, between, constant
import os
import logging

class QuickstartUser(HttpUser):
    wt = float(os.environ.get('USER_WAIT_TIME', 0.5))
    wait_time = constant(wt)

    @task
    def hello_world(self):
        url = os.environ.get('URL', "/")
        self.client.get(url)