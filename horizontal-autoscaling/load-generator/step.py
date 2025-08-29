import math
from locust import HttpUser, TaskSet, task, constant
from locust import LoadTestShape
import os

# read envionment variables

class UserTasks(TaskSet):
    @task
    def get_root(self):
        url = os.environ.get('URL', "/")
        self.client.get(url)


class WebsiteUser(HttpUser):
    wt = float(os.environ.get('USER_WAIT_TIME', 0.5))
    wait_time = constant(wt)
    tasks = [UserTasks]


class StepLoadShape(LoadTestShape):
    """
    A step load shape

    Keyword arguments:

        step_time -- Time between steps
        step_load -- User increase amount at each step
        spawn_rate -- Users to stop/start per second at every step
        time_limit -- Time limit in seconds

    """

    step_time = float(os.environ.get('STEP_TIME', 10))
    step_load = float(os.environ.get('STEP_LOAD', 2))
    spawn_rate = float(os.environ.get('SPAWN_RATE', 1))
    time_limit = float(os.environ.get('TIME_LIMIT', 600))

    def tick(self):
        run_time = self.get_run_time()

        if run_time > self.time_limit:
            return None

        current_step = math.floor(run_time / self.step_time) + 1
        return (current_step * self.step_load, self.spawn_rate)