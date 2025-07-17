import time
import json
import orjson
import ujson

def benchmark(name, dumps, loads):
    start = time.time()
    for i in range(10000000):
        result = dumps(m)
        loads(result)
    print(name, time.time() - start)

if __name__ == "__main__":
    m = {
        "timestamp": 1556283673.1523004,
        "task_uuid": "0ed1a1c3-050c-4fb9-9426-a7e72d0acfc7",
        "task_level": [1, 2, 1],
        "action_status": "started",
        "action_type": "main",
        "key": "value",
        "another_key": 123,
        "and_another": ["a", "b"],
    }

    benchmark("Python", json.dumps, json.loads)
    benchmark("ujson", ujson.dumps, ujson.loads)

    # orjson only outputs bytes, but often we need unicode:
    benchmark("orjson", lambda s: str(orjson.dumps(s), "utf-8"), orjson.loads)

# OUTPUT:
# Python 12.502133846282959
# ujson 4.428200960159302
# orjson 2.3136467933654785
