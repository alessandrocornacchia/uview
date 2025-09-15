import os
import subprocess

def get_env():
    try:
        services = os.environ['APP']
        print(services)
    except KeyError:
        pass

    return

if __name__ == '__main__':
    get_env()



