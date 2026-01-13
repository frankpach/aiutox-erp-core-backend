import json
import os

log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.cursor', 'debug.log')
with open(log_path, 'r', encoding='utf-8') as f:
    lines = f.read().split('\n')

recent = [json.loads(l) for l in lines if l]
print(f'Total logs: {len(recent)}')
print(f'Last timestamp: {recent[-1].get("timestamp") if recent else None}')
print(f'Last 10 logs:')
for r in recent[-10:]:
    print(f'  {r.get("location")}: {r.get("message")}')
    if r.get('data'):
        print(f'    Data: {r.get("data")}')
