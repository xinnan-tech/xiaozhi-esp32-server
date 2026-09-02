import unittest
import csv
import os
import shutil
import time
from datetime import datetime, timezone, timedelta

# SIMULATED CLASS (Copy of logic from cgm_manager.py)
class SimulatedCGMManager:
    def __init__(self):
        self.data_dir = "test_data_sim"
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

    def _append_to_csv(self, data, filename):
        if not data:
            return
        
        file_exists = os.path.isfile(filename)
        with open(filename, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=data[0].keys())
            if not file_exists:
                writer.writeheader()
            writer.writerows(data)

    def process_and_store(self, raw_entries):
        # Determine user TZ (Mocking)
        # Using UTC for simplicity in test
        
        processed_data = []
        for e in raw_entries:
            # Logic from cgm_manager.py
            # dt = datetime.fromtimestamp(e["date"]/1000, tz=timezone.utc).astimezone(tz) ...
            # Simplified for test:
            unix_s = int(e["date"] / 1000)
            processed_data.append({
                "time": str(unix_s),
                "sgv": e.get("sgv"),
                "direction": e.get("direction"),
                "unix_s": unix_s,
                "hour": 0,
                "weekday": 0
            })

        # --- THE FIX ---
        # Ensure data is sorted oldest -> newest before appending
        processed_data.sort(key=lambda x: x["unix_s"])
        # ----------------

        csv_path = os.path.join(self.data_dir, "cgm.csv")
        self._append_to_csv(processed_data, csv_path)

class TestCGMSorting(unittest.TestCase):
    def setUp(self):
        self.manager = SimulatedCGMManager()

    def tearDown(self):
        if os.path.exists(self.manager.data_dir):
            shutil.rmtree(self.manager.data_dir)

    def test_sorting_logic(self):
        # Input: Unsorted (Middle, Newest, Oldest)
        raw_input = [
            {"date": 1700000002000, "sgv": 2, "direction": "Flat"},
            {"date": 1700000003000, "sgv": 3, "direction": "Flat"},
            {"date": 1700000001000, "sgv": 1, "direction": "Flat"}
        ]
        
        self.manager.process_and_store(raw_input)
        
        csv_path = os.path.join(self.manager.data_dir, "cgm.csv")
        with open(csv_path, "r") as f:
            lines = f.readlines()
            
        # Header + 3 rows
        self.assertEqual(len(lines), 4)
        
        # Parse rows
        rows = [line.strip().split(',') for line in lines[1:]]
        # index 3 is unix_s (based on keys order, usually dict preserves insertion order in py3.7+, 
        # but let's be safe. Keys are: time, sgv, direction, unix_s, hour, weekday)
        # However, DictWriter uses keys from first dict.
        # My dict creation: time, sgv, direction, unix_s ...
        # So unix_s is index 3.
        
        ts1 = int(rows[0][3])
        ts2 = int(rows[1][3])
        ts3 = int(rows[2][3])
        
        print(f"Sorted TS: {ts1}, {ts2}, {ts3}")
        
        self.assertEqual(ts1, 1700000001)
        self.assertEqual(ts2, 1700000002)
        self.assertEqual(ts3, 1700000003)

if __name__ == "__main__":
    unittest.main()
