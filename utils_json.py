import json
import os
import shutil
import threading

_locks = {}

def read_json(path, default=None):
    lock = _locks.setdefault(path, threading.Lock())
    with lock:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return default if default is not None else {}

def write_json(path, data):
    lock = _locks.setdefault(path, threading.Lock())
    with lock:
        tmp = path + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            shutil.move(tmp, path)
        except:
            try:
                os.remove(tmp)
            except:
                pass
            raise
