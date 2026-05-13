from datetime import datetime

def get_run_timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")