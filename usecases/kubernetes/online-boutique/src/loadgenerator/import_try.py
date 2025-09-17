import json

with open('conf.json', 'r') as f:
    data = json.load(f)
    print(data['tasks'])