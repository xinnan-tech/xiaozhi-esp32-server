import sys
import os
import shutil
import unittest
from unittest.mock import MagicMock, patch

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock requests before importing cgm_manager
from unittest.mock import MagicMock
sys.modules["requests"] = MagicMock()

from core.utils.cgm_manager import CGMManager

class TestCGMManager(unittest.TestCase):
    def setUp(self):
        self.test_client_id = "test_client_debug"
        self.data_dir = os.path.join("data", self.test_client_id)
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Create dummy config
        with open(os.path.join(self.data_dir, "config.json"), "w") as f:
            f.write('{"cgm": {"api_secret": "test_secret"}}')
            
        self.manager = CGMManager(config={"CGM": {"base_url": "http://mock"}})

    def tearDown(self):
        if os.path.exists(self.data_dir):
            shutil.rmtree(self.data_dir)

    @patch("requests.get")
    def test_fetch_and_sort(self, mock_get):
        # Mock Response with UNSORTED data
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"date": 1700000002000, "sgv": 150, "direction": "Flat"}, # Middle
            {"date": 1700000001000, "sgv": 140, "direction": "Flat"}, # Oldest
            {"date": 1700000003000, "sgv": 160, "direction": "Flat"}  # Newest
        ]
        mock_get.return_value = mock_response

        self.manager.fetch_and_update(self.test_client_id)

        # Verify CSV content
        csv_path = os.path.join(self.data_dir, "cgm.csv")
        with open(csv_path, "r") as f:
            lines = f.readlines()
        
        # Header + 3 rows = 4 lines
        self.assertEqual(len(lines), 4)
        
        # Verify Order (unix_s is 4th column)
        # Headers: time,sgv,direction,unix_s,hour,weekday
        
        row1 = lines[1].strip().split(",")
        row2 = lines[2].strip().split(",")
        row3 = lines[3].strip().split(",")
        
        ts1 = int(row1[3])
        ts2 = int(row2[3])
        ts3 = int(row3[3])
        
        print(f"Timestamps: {ts1}, {ts2}, {ts3}")
        
        self.assertTrue(ts1 < ts2 < ts3, "Data was not sorted correctly!")
        self.assertEqual(ts1, 1700000001)
        self.assertEqual(ts3, 1700000003)

if __name__ == "__main__":
    unittest.main()
