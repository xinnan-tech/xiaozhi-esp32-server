import os
import csv
import json
import time
import asyncio
import logging
import requests
import datetime
from zoneinfo import ZoneInfo
from typing import List, Dict, Any, Optional

from config.settings import load_config
from config.logger import setup_logging

TAG = "cgm_manager"
logger = setup_logging()

class CGMManager:
    def __init__(self, config=None):
        self.config = config or load_config()

    def _get_client_config(self, client_id: str) -> Optional[Dict]:
        """Load client specific config for secrets and TZ"""
        config_path = os.path.join("data", client_id, "config.json")
        if not os.path.exists(config_path):
            return None
        try:
            with open(config_path, "r") as f:
                return json.load(f).get("cgm", {})
        except Exception as e:
            logger.bind(tag=TAG).error(f"Failed to load config for {client_id}: {e}")
            return None

    def fetch_and_update(self, client_id: str):
        """Fetch new data and append to CSV"""
        cgm_config = self._get_client_config(client_id)
        if not cgm_config or "api_secret" not in cgm_config:
            # Client has not configured CGM
            return

        base_url = cgm_config.get("base_url")
        if not base_url:
            return

        api_secret = cgm_config["api_secret"]
        user_tz_str = cgm_config.get("user_tz", "US/Eastern")
        
        csv_path = os.path.join("data", client_id, "cgm.csv")
        
        # Determine start time
        start_ms = 0
        if os.path.exists(csv_path):
            try:
                with open(csv_path, "r") as f:
                    # Read last line to get last timestamp
                    # Using light-weight seek for large files could be better, but simple for now
                    lines = f.readlines()
                    if len(lines) > 1:
                        last_row = lines[-1].strip().split(',')
                        # Assuming unix_s column exists. Let's find its index from header
                        headers = lines[0].strip().split(',')
                        if "unix_s" in headers:
                            idx = headers.index("unix_s")
                            # +1000ms to avoid duplicate
                            start_ms = int(last_row[idx]) * 1000 + 1000 
            except Exception as e:
                logger.bind(tag=TAG).warning(f"Error reading last time for {client_id}: {e}")

        # If start_ms is 0 (new file), maybe default to 24h ago?
        # User prompt example used explicit dates. 
        # Let's default to 24h ago if empty to fetch recent history.
        if start_ms == 0:
             start_ms = int((datetime.datetime.now() - datetime.timedelta(days=1)).timestamp() * 1000)

        end_ms = int(datetime.datetime.now().timestamp() * 1000)
        
        # Determine string formats for API if needed differently?
        # User code used `find[date][$gte]` with MS.
        
        params = {
            "count": 1000,
            "find[date][$gte]": start_ms,
            "find[date][$lt]": end_ms,
            "sort$": "date"
        }
        
        try:
            r = requests.get(
                f"{base_url.rstrip('/')}/api/v1/entries.json", 
                params=params, 
                headers={"api-secret": api_secret},
                timeout=20
            )
            r.raise_for_status()
            entries = r.json()
        except Exception as e:
            logger.bind(tag=TAG).error(f"Fetch failed for {client_id}: {e}")
            return

        if not entries:
            return

        # Process entries
        tz = ZoneInfo(user_tz_str)
        processed_data = []
        for e in entries:
            if not e.get("sgv"): 
                continue
            
            # Helper for localized time string
            dt = datetime.datetime.fromtimestamp(e["date"]/1000, tz=datetime.timezone.utc).astimezone(tz)
            
            processed_data.append({
                "time": dt.strftime("%Y-%m-%d %H:%M:%S"),
                "sgv": e.get("sgv"),
                "direction": e.get("direction"),
                "unix_s": int(e["date"] / 1000),
                "hour": dt.hour,      # For analysis
                "weekday": dt.weekday() # For analysis (0=Mon)
            })

        # Ensure data is sorted oldest -> newest before appending
        processed_data.sort(key=lambda x: x["unix_s"])

        self._append_to_csv(processed_data, csv_path)
        logger.bind(tag=TAG).info(f"Fetched {len(processed_data)} new CGM entries for {client_id}")

    def _append_to_csv(self, data: List[Dict], filename: str):
        if not data:
            return
        
        file_exists = os.path.isfile(filename)
        with open(filename, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=data[0].keys())
            if not file_exists:
                writer.writeheader()
            writer.writerows(data)

    def get_latest_reading(self, client_id: str) -> Optional[Dict[str, Any]]:
        """Return the most recent CGM reading as a dict with 'glucose' and 'direction'."""
        csv_path = os.path.join("data", client_id, "cgm.csv")
        if not os.path.exists(csv_path):
            return None
        
        try:
            with open(csv_path, "r") as f:
                header_line = f.readline()
                if not header_line:
                    return None
                header = header_line.strip().split(",")
                
                # Seek to end to read last lines
                f.seek(0, os.SEEK_END)
                file_size = f.tell()
                seek_pos = max(0, file_size - 1024)
                f.seek(seek_pos)
                
                content = f.read()
                lines = content.splitlines()
                
                if seek_pos > 0 and len(lines) > 0:
                    lines.pop(0)
                    
                if not lines:
                    return None
                
                last_row_str = lines[-1]
                parts = last_row_str.split(",")
                
                if len(parts) != len(header) and len(lines) > 1:
                    last_row_str = lines[-2]
                    parts = last_row_str.split(",")
                
                if len(parts) != len(header):
                    return None
                
                last = dict(zip(header, parts))
                return {
                    "glucose": int(last.get("sgv", 0)),
                    "direction": last.get("direction", "Unknown"),
                    "unix_s": int(last.get("unix_s", 0))
                }
        except Exception as e:
            logger.bind(tag=TAG).error(f"Failed to get latest reading: {e}")
            return None

    def get_realtime_status(self, client_id: str) -> str:
        """Return a short string summary of current state"""
        csv_path = os.path.join("data", client_id, "cgm.csv")
        if not os.path.exists(csv_path):
            return ""
        
        try:
            with open(csv_path, "r") as f:
                # Read header
                header_line = f.readline()
                if not header_line: return ""
                header = header_line.strip().split(",")
                
                # Seek to end to read last lines
                f.seek(0, os.SEEK_END)
                file_size = f.tell()
                
                # Read last 1024 bytes (enough for several rows)
                seek_pos = max(0, file_size - 1024)
                f.seek(seek_pos)
                
                content = f.read()
                lines = content.splitlines()
                
                # If we started in middle of a line, discard first
                if seek_pos > 0 and len(lines) > 0:
                    lines.pop(0)
                    
                if not lines: return ""
                
                # Get last valid row
                last_row_str = lines[-1]
                parts = last_row_str.split(",")
                
                # Basic validation
                if len(parts) != len(header):
                    # fallback to previous line if last is incomplete
                    if len(lines) > 1:
                        last_row_str = lines[-2]
                        parts = last_row_str.split(",")
                    
                if len(parts) != len(header): return ""
                
                last = dict(zip(header, parts))
            # Time delta
            last_ts = int(last["unix_s"])
            now_ts = int(time.time())
            diff_min = (now_ts - last_ts) // 60
            
            return f"Current Glucose: {last['sgv']} mg/dL ({last.get('direction', 'Unknown')}), {diff_min} mins ago."
        except Exception as e:
            return ""

    def _read_all_rows(self, client_id: str) -> List[Dict[str, Any]]:
        csv_path = os.path.join("data", client_id, "cgm.csv")
        if not os.path.exists(csv_path):
            return []

        try:
            with open(csv_path, "r") as f:
                return list(csv.DictReader(f))
        except Exception as e:
            logger.bind(tag=TAG).error(f"Failed to read CGM rows: {e}")
            return []
    

    def analyze_daily_trends(self, client_id: str, days=14) -> List[str]:
        """Analyze last N days for hourly patterns"""
        # Load data (should optimize to not load all)
        csv_path = os.path.join("data", client_id, "cgm.csv")
        if not os.path.exists(csv_path): return []
        
        try:
            with open(csv_path, "r") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            
            if not rows: return []
            
            # Filter last N days
            cutoff_ts = int(time.time()) - (days * 86400)
            recent_rows = [r for r in rows if int(r["unix_s"]) >= cutoff_ts]
            
            if not recent_rows: return []

            # Bin by hour
            hourly_sum = {h: [] for h in range(24)}
            for r in recent_rows:
                h = int(r["hour"])
                hourly_sum[h].append(int(r["sgv"]))
            
            trends = []
            # Find Highs (>180) Hotspots
            high_hours = []
            for h in range(24):
                vals = hourly_sum[h]
                if vals:
                    avg = sum(vals) / len(vals)
                    if avg > 160: # Threshold for "High Pattern"
                        high_hours.append(h)
            
            if high_hours:
                # Group consecutive
                # Simplified representation
                trends.append(f"Daily Pattern: Tendency to be high around {high_hours} hours.")
            
            return trends
        except Exception:
            return []

    def analyze_weekly_trends(self, client_id: str, weeks=4) -> List[str]:
         # Similar logic for weekday (0-6)
         return []
    
    def analyze_long_term_control(self, client_id: str, days: int = 14) -> List[str]:
        rows = self._read_all_rows(client_id)
        if not rows:
            return []

        cutoff_ts = int(time.time()) - days * 86400
        recent = [
            r for r in rows 
            if r.get("unix_s") and int(r["unix_s"]) >= cutoff_ts
        ]

        values = [float(r["sgv"]) for r in recent if r.get("sgv")]
        if not values:
            return []

        total = len(values)
        mean_glucose = sum(values) / total

        tir = sum(70 <= v <= 180 for v in values) / total * 100
        tar = sum(v > 180 for v in values) / total * 100
        tbr = sum(v < 70 for v in values) / total * 100

        gmi = 3.31 + 0.02392 * mean_glucose

        return [
            f"TIR {tir:.1f}%, TAR {tar:.1f}%, TBR {tbr:.1f}%",
            f"Mean glucose {mean_glucose:.1f} mg/dL, GMI {gmi:.2f}%"
        ]

    def get_context_summary(self, client_id: str) -> str:
        """Full context block for LLM"""
        status = self.get_realtime_status(client_id)
        if not status: return ""
        
        daily = self.analyze_daily_trends(client_id)
        daily_str = " ".join(daily)

        long_term = self.analyze_long_term_control(client_id)
        daily_str += " " + " ".join(long_term)
        
        return f"[CGM Data]\n{status}\n{daily_str}"
    


async def cgm_background_task():
    """Periodic update task"""
    logger.bind(tag=TAG).info("CGM Scraper task started.")
    manager = CGMManager()
    
    while True:
        try:
            # Iterate active clients (directories in data/)
            data_dir = "data"
            if os.path.exists(data_dir):
                for client_id in os.listdir(data_dir):
                    if os.path.isdir(os.path.join(data_dir, client_id)):
                        # Check if config has cgm
                        if manager._get_client_config(client_id):
                            manager.fetch_and_update(client_id)
            
            # Wait 15 minutes
            await asyncio.sleep(900)
        except Exception as e:
            logger.bind(tag=TAG).error(f"Task error: {e}")
            await asyncio.sleep(60)
