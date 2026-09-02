"""Pump data manager for Nightscout treatment/profile sync.

This module is designed to be imported by the main server and run as a background
async task, similar to a CGM manager. It can:
1. load per-client pump config from `data/<client_id>/config.json`
2. fetch new Nightscout treatments and profile data
3. normalize and persist pump events to CSV/JSON
4. generate short text summaries for downstream prompt/context assembly
"""
from __future__ import annotations

import os
import csv
import json
import time
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Union, Optional
from collections import Counter

import requests
import pytz

TAG = "pump_manager"
EASTERN_TZ = pytz.timezone("US/Eastern")


class SimpleLogger:
    def info(self, msg: str) -> None:
        print(f"[INFO] {msg}")

    def warning(self, msg: str) -> None:
        print(f"[WARNING] {msg}")

    def error(self, msg: str) -> None:
        print(f"[ERROR] {msg}")


logger = SimpleLogger()


def create_pump_background_task(data_root: str = "data"):
    """Return the coroutine for the server to schedule.

    Example integration in an async server startup:
        asyncio.create_task(create_pump_background_task("data"))
    """
    return pump_background_task(data_root=data_root)


def to_utc_ms(value: Union[str, datetime]) -> int:
    if isinstance(value, datetime):
        dt = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
        return int(dt.astimezone(timezone.utc).timestamp() * 1000)

    if isinstance(value, str):
        s = value.strip()
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.astimezone(timezone.utc).timestamp() * 1000)

    raise TypeError("value must be str or datetime")


def parse_iso_to_dt(value: str) -> datetime:
    s = value.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


class PumpManager:
    def __init__(self, data_root: str = "data"):
        self.data_root = data_root

    def _get_client_config(self, client_id: str) -> Optional[Dict[str, Any]]:
        config_path = os.path.join(self.data_root, client_id, "config.json")
        if not os.path.exists(config_path):
            return None
        try:
            with open(config_path, "r") as f:
                payload = json.load(f)
            return payload.get("pump")
        except Exception as e:
            logger.error(f"Failed to load pump config for {client_id}: {e}")
            return None

    def _client_dir(self, client_id: str) -> str:
        return os.path.join(self.data_root, client_id)

    def _events_csv_path(self, client_id: str) -> str:
        return os.path.join(self._client_dir(client_id), "pump_events.csv")

    def _profile_json_path(self, client_id: str) -> str:
        return os.path.join(self._client_dir(client_id), "pump_profile.json")

    def _is_pump_treatment(self, row: Dict[str, Any]) -> bool:
        entered_by = str(row.get("enteredBy") or "").strip().lower()
        event_type = str(row.get("eventType") or "").strip().lower()
        pump_event_id = row.get("pump_event_id")

        if "tconnectsync" in entered_by:
            return True
        if entered_by.startswith("pump"):
            return True
        if pump_event_id not in (None, "", 0):
            return True
        if "bolus" in event_type or event_type == "temp basal":
            return True
        return False

    def _get_last_event_time_ms(self, client_id: str) -> int:
        csv_path = self._events_csv_path(client_id)
        if not os.path.exists(csv_path):
            return 0

        try:
            with open(csv_path, "r", newline="") as f:
                rows = list(csv.DictReader(f))
            if not rows:
                return 0

            for row in reversed(rows):
                unix_s = row.get("unix_s")
                if unix_s in (None, ""):
                    continue
                try:
                    return int(unix_s) * 1000
                except (TypeError, ValueError):
                    continue
            return 0
        except Exception as e:
            logger.warning(f"Failed to read last pump event time for {client_id}: {e}")
            return 0

    def _get_existing_event_keys(self, client_id: str) -> set:
        rows = self._read_all_events(client_id)
        keys = set()
        for row in rows:
            pump_event_id = str(row.get("pump_event_id") or "").strip()
            raw_id = ""
            try:
                raw_json = row.get("raw_json")
                if raw_json:
                    raw_payload = json.loads(raw_json)
                    raw_id = str(raw_payload.get("_id") or "").strip()
            except Exception:
                raw_id = ""

            if pump_event_id:
                keys.add(("pump_event_id", pump_event_id))
            elif raw_id:
                keys.add(("_id", raw_id))
            else:
                keys.add((
                    "fallback",
                    str(row.get("time") or ""),
                    str(row.get("event_type") or ""),
                    str(row.get("insulin_units") or ""),
                    str(row.get("rate_u_per_hr") or ""),
                ))
        return keys

    def _event_key_from_normalized(self, row: Dict[str, Any]) -> tuple:
        pump_event_id = str(row.get("pump_event_id") or "").strip()
        raw_id = ""
        try:
            raw_json = row.get("raw_json")
            if raw_json:
                raw_payload = json.loads(raw_json)
                raw_id = str(raw_payload.get("_id") or "").strip()
        except Exception:
            raw_id = ""

        if pump_event_id:
            return ("pump_event_id", pump_event_id)
        if raw_id:
            return ("_id", raw_id)
        return (
            "fallback",
            str(row.get("time") or ""),
            str(row.get("event_type") or ""),
            str(row.get("insulin_units") or ""),
            str(row.get("rate_u_per_hr") or ""),
        )

    def fetch_treatments(
        self,
        start: Union[str, datetime],
        end: Union[str, datetime],
        *,
        base_url: str,
        api_secret_sha1: str,
        page_size: int = 500,
        timeout: int = 20,
    ) -> List[Dict[str, Any]]:
        start_ms = to_utc_ms(start)
        end_ms = to_utc_ms(end)

        if end_ms < start_ms:
            raise ValueError("end must be >= start")

        headers = {"api-secret": api_secret_sha1}
        url = f"{base_url.rstrip('/')}/api/v1/treatments.json"

        all_rows: List[Dict[str, Any]] = []
        last_ms = start_ms - 1

        while True:
            gt_time = datetime.fromtimestamp(last_ms / 1000, tz=timezone.utc).isoformat().replace("+00:00", "Z")
            lte_time = datetime.fromtimestamp(end_ms / 1000, tz=timezone.utc).isoformat().replace("+00:00", "Z")
            params = {
                "count": page_size,
                "find[created_at][$gt]": gt_time,
                "find[created_at][$lte]": lte_time,
                "sort$created_at": 1,
            }

            r = requests.get(url, params=params, headers=headers, timeout=timeout)
            if not r.ok:
                raise RuntimeError(f"Nightscout error {r.status_code}: {r.text[:300]}")

            try:
                batch = r.json()
            except ValueError as e:
                logger.error(
                    f"Nightscout returned non-JSON treatments response. "
                    f"url={r.url} status={r.status_code} content_type={r.headers.get('content-type')} "
                    f"body={r.text[:300]!r}"
                )
                raise RuntimeError(f"Nightscout returned non-JSON treatments response: {e}")
            if not isinstance(batch, list):
                raise RuntimeError(f"Unexpected response type: {type(batch)}")

            if not batch:
                break

            batch.sort(key=lambda x: parse_iso_to_dt(x["created_at"]).timestamp() if "created_at" in x else 0)

            for row in batch:
                created_at = row.get("created_at")
                if not isinstance(created_at, str):
                    continue
                ms = int(parse_iso_to_dt(created_at).astimezone(timezone.utc).timestamp() * 1000)
                if start_ms <= ms <= end_ms:
                    all_rows.append(row)

            last_created_at = batch[-1].get("created_at")
            if not isinstance(last_created_at, str):
                break

            new_last_ms = int(parse_iso_to_dt(last_created_at).astimezone(timezone.utc).timestamp() * 1000)

            if new_last_ms <= last_ms:
                break

            last_ms = new_last_ms

            if last_ms >= end_ms:
                break

        seen = set()
        deduped: List[Dict[str, Any]] = []
        for row in sorted(all_rows, key=lambda x: x.get("created_at", "")):
            key = row.get("_id") or (
                row.get("created_at"),
                row.get("eventType"),
                row.get("pump_event_id"),
            )
            if key in seen:
                continue
            seen.add(key)
            deduped.append(row)

        return deduped

    def fetch_profile(self, *, base_url: str, api_secret_sha1: str, timeout: int = 20) -> Any:
        headers = {"api-secret": api_secret_sha1}
        url = f"{base_url.rstrip('/')}/api/v1/profile.json"

        r = requests.get(url, headers=headers, timeout=timeout)
        if not r.ok:
            raise RuntimeError(f"Nightscout profile error {r.status_code}: {r.text[:300]}")
        try:
            return r.json()
        except ValueError as e:
            logger.error(
                f"Nightscout returned non-JSON profile response. "
                f"url={r.url} status={r.status_code} content_type={r.headers.get('content-type')} "
                f"body={r.text[:300]!r}"
            )
            raise RuntimeError(f"Nightscout returned non-JSON profile response: {e}")

    def extract_active_profile(self, profile_payload: Any) -> Dict[str, Any]:
        if not isinstance(profile_payload, list) or not profile_payload:
            return {}

        first = profile_payload[0]
        if not isinstance(first, dict):
            return {}

        default_profile_name = first.get("defaultProfile")
        store = first.get("store", {})

        if not isinstance(store, dict):
            return {}

        if isinstance(default_profile_name, str) and default_profile_name in store:
            active_name = default_profile_name
        else:
            active_name = next(iter(store.keys()), None)

        if active_name is None:
            return {}

        profile = store.get(active_name, {})
        if not isinstance(profile, dict):
            return {}

        return {
            "active_profile_name": active_name,
            "timezone": profile.get("timezone"),
            "units": profile.get("units"),
            "dia_hours": profile.get("dia"),
            "basal_schedule": profile.get("basal", []),
            "carbratio_schedule": profile.get("carbratio", []),
            "sensitivity_schedule": profile.get("sens", []),
            "target_low_schedule": profile.get("target_low", []),
            "target_high_schedule": profile.get("target_high", []),
            "raw_profile": profile,
        }

    def _normalize_event(self, row: Dict[str, Any], tz=pytz.timezone("US/Eastern")) -> Optional[Dict[str, Any]]:
        created_at = row.get("created_at")
        if not isinstance(created_at, str):
            return None

        dt_utc = parse_iso_to_dt(created_at).astimezone(timezone.utc)
        dt_local = dt_utc.astimezone(tz)
        event_type = row.get("eventType", "UNKNOWN")

        if event_type == "Temp Basal":
            category = "temp_basal"
        elif "Bolus" in str(event_type):
            category = "bolus"
        else:
            category = "other"

        return {
            "time": created_at,
            "time_et": dt_local.isoformat(),
            "unix_s": int(dt_utc.timestamp()),
            "hour": dt_local.hour,
            "weekday": dt_local.weekday(),
            "event_type": event_type,
            "category": category,
            "entered_by": row.get("enteredBy"),
            "pump_event_id": row.get("pump_event_id"),
            "insulin_units": row.get("insulin"),
            "carbs_g": row.get("carbs"),
            "glucose_mgdl": row.get("glucose"),
            "rate_u_per_hr": row.get("absolute") if row.get("absolute") is not None else row.get("rate"),
            "duration_min": row.get("duration"),
            "reason": row.get("reason"),
            "notes": row.get("notes"),
            "raw_json": json.dumps(row, ensure_ascii=False),
        }

    def _append_to_csv(self, rows: List[Dict[str, Any]], filename: str) -> None:
        if not rows:
            return

        os.makedirs(os.path.dirname(filename), exist_ok=True)
        file_exists = os.path.isfile(filename)

        with open(filename, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            if not file_exists:
                writer.writeheader()
            writer.writerows(rows)

    def _write_profile_json(self, client_id: str, payload: Dict[str, Any]) -> None:
        path = self._profile_json_path(client_id)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(payload, f, indent=2)

    def _read_all_events(self, client_id: str) -> List[Dict[str, Any]]:
        csv_path = self._events_csv_path(client_id)
        if not os.path.exists(csv_path):
            return []

        try:
            with open(csv_path, "r", newline="") as f:
                return list(csv.DictReader(f))
        except Exception as e:
            logger.error(f"Failed to read pump events for {client_id}: {e}")
            return []

    def _safe_float(self, value: Any) -> Optional[float]:
        if value in (None, ""):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _fmt_number(self, value: Any, decimals: int = 2) -> str:
        number = self._safe_float(value)
        if number is None:
            return "unknown"
        return f"{number:.{decimals}f}"

    def _fmt_int_like(self, value: Any) -> str:
        number = self._safe_float(value)
        if number is None:
            return "unknown"
        if float(number).is_integer():
            return str(int(number))
        return f"{number:.1f}"
    

    def get_latest_bolus_event(self, client_id: str) -> Optional[Dict[str, Any]]:
        rows = self._read_all_events(client_id)
        if not rows:
            return None

        for row in reversed(rows):
            category = str(row.get("category") or "").strip().lower()
            event_type = str(row.get("event_type") or "").strip().lower()
            insulin = self._safe_float(row.get("insulin_units"))

            if category == "bolus":
                return row
            if "bolus" in event_type:
                return row
            if insulin is not None and insulin > 0:
                return row

        return None

    def format_latest_bolus_summary(self, client_id: str) -> str:
        bolus = self.get_latest_bolus_event(client_id)
        if not bolus:
            return ""

        try:
            now_ts = int(time.time())
            event_ts = int(float(bolus.get("unix_s", 0)))
            diff_min = max(0, (now_ts - event_ts) // 60)
        except Exception:
            diff_min = None

        event_type = bolus.get("event_type") or "Bolus"
        time_et = bolus.get("time_et") or bolus.get("time") or "unknown time"
        insulin = self._fmt_number(bolus.get("insulin_units"))
        carbs = self._fmt_int_like(bolus.get("carbs_g"))
        glucose = self._fmt_int_like(bolus.get("glucose_mgdl"))
        notes = str(bolus.get("notes") or "").strip()

        parts = [
            f"Last Bolus: {event_type} at {time_et}",
            f"insulin {insulin} U",
        ]

        if carbs != "unknown":
            parts.append(f"carbs {carbs} g")
        if glucose != "unknown":
            parts.append(f"glucose {glucose} mg/dL")
        if diff_min is not None:
            parts.append(f"{diff_min} mins ago")
        if notes:
            parts.append(f"notes: {notes}")

        return ", ".join(parts) + "."

    def fetch_and_update(self, client_id: str) -> None:
        pump_config = self._get_client_config(client_id)
        if not pump_config:
            return

        base_url = pump_config.get("base_url")
        api_secret = pump_config.get("api_secret")
        user_tz_str = pump_config.get("user_tz", "US/Eastern")

        if not base_url or not api_secret:
            return

        try:
            tz = pytz.timezone(user_tz_str)
        except Exception:
            tz = EASTERN_TZ

        last_ms = self._get_last_event_time_ms(client_id)
        end = datetime.now(timezone.utc)
        # Always look back to avoid missing delayed/out-of-order Nightscout uploads.
        # Existing rows are de-duplicated by pump_event_id, then Nightscout _id, then a fallback key.
        start = end - timedelta(hours=6)

        logger.info(
            f"Pump fetch window for {client_id}: start={start.isoformat()} end={end.isoformat()} last_ms={last_ms}"
        )

        try:
            treatments = self.fetch_treatments(
                start,
                end,
                base_url=base_url,
                api_secret_sha1=api_secret,
            )
            profile_payload = self.fetch_profile(
                base_url=base_url,
                api_secret_sha1=api_secret,
            )
        except Exception as e:
            logger.error(f"Pump fetch failed for {client_id}: {e}")
            return

        logger.info(f"Raw treatments fetched for {client_id}: {len(treatments)}")
        if treatments:
            sample_entered_by = [str(x.get("enteredBy")) for x in treatments[:10]]
            sample_event_types = [str(x.get("eventType")) for x in treatments[:10]]
            logger.info(f"Sample enteredBy values for {client_id}: {sample_entered_by}")
            logger.info(f"Sample eventType values for {client_id}: {sample_event_types}")

        pump_rows = [x for x in treatments if self._is_pump_treatment(x)]
        logger.info(f"Pump-like treatments after filter for {client_id}: {len(pump_rows)}")

        normalized_rows = []
        for row in pump_rows:
            normalized = self._normalize_event(row, tz=tz)
            if normalized is not None:
                normalized_rows.append(normalized)

        existing_keys = self._get_existing_event_keys(client_id)
        deduped_rows = []
        for normalized in normalized_rows:
            key = self._event_key_from_normalized(normalized)
            if key in existing_keys:
                continue
            existing_keys.add(key)
            deduped_rows.append(normalized)

        deduped_rows.sort(key=lambda x: int(float(x.get("unix_s", 0))))
        self._append_to_csv(deduped_rows, self._events_csv_path(client_id))

        active_profile = self.extract_active_profile(profile_payload)
        profile_output = {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "active_profile": active_profile,
            "raw_profile_payload": profile_payload,
        }
        self._write_profile_json(client_id, profile_output)

        logger.info(
            f"Fetched {len(deduped_rows)} new pump events for {client_id} "
            f"after de-dup from {len(normalized_rows)} pump-like rows; "
            f"profile saved to {self._profile_json_path(client_id)}"
        )

    def get_latest_event(self, client_id: str) -> Optional[Dict[str, Any]]:
        rows = self._read_all_events(client_id)
        if not rows:
            return None
        return rows[-1]

    def _format_rate_clean(self, value: Any) -> str:
        number = self._safe_float(value)
        if number is None:
            return "unknown"
        return f"{number:.2f}".rstrip("0").rstrip(".")

    def _load_active_profile(self, client_id: str) -> Dict[str, Any]:
        profile_path = self._profile_json_path(client_id)
        if not os.path.exists(profile_path):
            return {}
        try:
            with open(profile_path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            active_profile = payload.get("active_profile", {})
            return active_profile if isinstance(active_profile, dict) else {}
        except Exception as e:
            logger.warning(f"Failed to load active pump profile for {client_id}: {e}")
            return {}

    def _get_scheduled_basal_rate_at_event(self, client_id: str, event_row: Dict[str, Any]) -> Optional[float]:
        active_profile = self._load_active_profile(client_id)
        basal_schedule = active_profile.get("basal_schedule", [])
        if not isinstance(basal_schedule, list) or not basal_schedule:
            return None

        event_time = event_row.get("time_et") or event_row.get("time")
        if not event_time:
            return None

        try:
            event_dt = parse_iso_to_dt(str(event_time))
            seconds_since_midnight = event_dt.hour * 3600 + event_dt.minute * 60 + event_dt.second
        except Exception:
            return None

        selected_rate = None
        selected_start = -1
        for segment in basal_schedule:
            try:
                start_seconds = int(float(segment.get("timeAsSeconds", 0)))
                value = float(segment.get("value"))
            except Exception:
                continue

            if start_seconds <= seconds_since_midnight and start_seconds >= selected_start:
                selected_start = start_seconds
                selected_rate = value

        if selected_rate is None:
            for segment in reversed(basal_schedule):
                try:
                    return float(segment.get("value"))
                except Exception:
                    continue

        return selected_rate

    def get_realtime_status(self, client_id: str) -> str:
        latest = self.get_latest_event(client_id)
        if not latest:
            return ""

        try:
            now_ts = int(time.time())
            event_ts = int(float(latest.get("unix_s", 0)))
            diff_min = max(0, (now_ts - event_ts) // 60)
            event_type = latest.get("event_type", "UNKNOWN")
            category = latest.get("category", "other")

            if category == "temp_basal":
                raw_rate = latest.get("rate_u_per_hr")
                raw_duration = latest.get("duration_min")
                rate = self._format_rate_clean(raw_rate)
                duration = self._fmt_int_like(raw_duration)
                reason = str(latest.get("reason") or "").strip()

                scheduled_rate = self._get_scheduled_basal_rate_at_event(client_id, latest)
                event_rate = self._safe_float(raw_rate)

                if scheduled_rate is not None and event_rate is not None:
                    scheduled_text = self._format_rate_clean(scheduled_rate)
                    if abs(event_rate - scheduled_rate) < 0.01:
                        summary = (
                            f"Latest Pump Event: basal delivery matched scheduled profile rate "
                            f"({rate} U/hr), {diff_min} mins ago"
                        )
                    else:
                        summary = (
                            f"Latest Pump Event: Temp Basal {rate} U/hr for {duration} min, "
                            f"{diff_min} mins ago; scheduled profile basal was {scheduled_text} U/hr"
                        )
                else:
                    summary = f"Latest Pump Event: Temp Basal {rate} U/hr for {duration} min, {diff_min} mins ago"

                if reason:
                    summary += f" ({reason})"
                return summary + "."

            if category == "bolus":
                insulin = self._fmt_number(latest.get("insulin_units"))
                carbs = self._fmt_int_like(latest.get("carbs_g"))
                glucose = self._fmt_int_like(latest.get("glucose_mgdl"))
                parts = [
                    f"Latest Pump Event: {event_type}",
                    f"{insulin} U",
                ]
                if carbs != "unknown":
                    parts.append(f"{carbs} g carbs")
                if glucose != "unknown":
                    parts.append(f"glucose {glucose} mg/dL")
                parts.append(f"{diff_min} mins ago")
                return ", ".join(parts) + "."

            reason = str(latest.get("reason") or latest.get("notes") or "").strip()
            summary = f"Latest Pump Event: {event_type}, {diff_min} mins ago"
            if reason:
                summary += f" ({reason})"
            return summary + "."
        except Exception:
            return ""
        

    def get_authoritative_summary(self, client_id: str) -> str:
        """Force a fresh read and return an authoritative summary."""
        # fetch_and_update should be called by the caller before this if needed
        rows = self._read_all_events(client_id)
        if not rows:
            return "[No Pump Data Available]"
        
        # Sort by unix_s to ensure absolute latest
        try:
            rows.sort(key=lambda x: int(float(x.get("unix_s", 0))))
        except Exception:
            pass
            
        latest = rows[-1]
        
        # Build authoritative status
        status_text = self.get_realtime_status(client_id)
        bolus_summary = self.format_latest_bolus_summary(client_id)
        
        return (
            f"--- FRESH PUMP STATUS (AUTHORITATIVE) ---\n"
            f"{status_text}\n"
            f"{bolus_summary}\n"
            f"Interpretation rule: For Temp Basal events, compare event rate with scheduled pump profile basal rate. If they match or nearly match, do not describe it as a separate temp basal intervention; describe it as basal delivery matching the scheduled profile.\n"
            f"--- END FRESH DATA ---"
        )

    def analyze_recent_patterns(self, client_id: str, days: int = 3) -> List[str]:
        rows = self._read_all_events(client_id)
        if not rows:
            return []

        try:
            cutoff_ts = int(time.time()) - days * 86400
            recent_rows = [
                r for r in rows
                if int(float(r.get("unix_s", 0))) >= cutoff_ts
            ]
            if not recent_rows:
                return []

            counts = Counter(r.get("event_type", "UNKNOWN") for r in recent_rows)
            trends: List[str] = []

            if counts:
                top_name, top_count = counts.most_common(1)[0]
                trends.append(
                    f"Pump Pattern: Most frequent recent event is {top_name} ({top_count} times in last {days} days)."
                )

            bolus_rows = [
                r for r in recent_rows
                if str(r.get("category") or "").strip().lower() == "bolus"
                or "bolus" in str(r.get("event_type") or "").strip().lower()
            ]

            hourly_bolus = Counter(int(float(r.get("hour", 0))) for r in bolus_rows)
            if hourly_bolus:
                top_hour, top_hour_count = hourly_bolus.most_common(1)[0]
                trends.append(
                    f"Pump Pattern: Bolus events most often happen around hour {top_hour:02d}:00 ({top_hour_count} times)."
                )

            bolus_with_amount = [
                self._safe_float(r.get("insulin_units"))
                for r in bolus_rows
                if self._safe_float(r.get("insulin_units")) is not None
            ]
            if bolus_with_amount:
                avg_bolus = sum(bolus_with_amount) / len(bolus_with_amount)
                trends.append(
                    f"Pump Pattern: Average recent bolus size is {avg_bolus:.2f} U across {len(bolus_with_amount)} bolus events."
                )

            return trends
        except Exception as e:
            logger.warning(f"Failed to analyze recent pump patterns for {client_id}: {e}")
            return []

    def get_context_summary(self, client_id: str) -> str:
        status = self.get_realtime_status(client_id)
        latest_bolus = self.format_latest_bolus_summary(client_id)
        patterns = self.analyze_recent_patterns(client_id)

        sections = ["[Pump Data]"]
        if status:
            sections.append(status)
        if latest_bolus:
            sections.append(latest_bolus)
        if patterns:
            sections.extend(patterns)

        if len(sections) == 1:
            return ""
        return "\n".join(sections)

    def has_pump_config(self, client_id: str) -> bool:
        pump_config = self._get_client_config(client_id)
        return bool(pump_config and pump_config.get("base_url") and pump_config.get("api_secret"))

    def analyze_insulin_effectiveness(self, client_id: str) -> List[str]:
        pump_rows = self._read_all_events(client_id)
        cgm_path = os.path.join(self._client_dir(client_id), "cgm.csv")

        if not os.path.exists(cgm_path):
            return []

        with open(cgm_path, "r") as f:
            cgm_rows = list(csv.DictReader(f))

        if not pump_rows or not cgm_rows:
            return []

        results = []

        for row in pump_rows[-10:]:  # 看最近10次
            if row.get("category") != "bolus":
                continue

            ts = int(float(row["unix_s"]))

            before = [
                float(r["sgv"])
                for r in cgm_rows
                if ts - 1800 <= int(r["unix_s"]) <= ts
            ]

            after = [
                float(r["sgv"])
                for r in cgm_rows
                if ts + 3600 <= int(r["unix_s"]) <= ts + 4*3600
            ]

            if not before or not after:
                continue

            delta = sum(after)/len(after) - sum(before)/len(before)
            results.append(delta)

        if not results:
            return []

        avg_delta = sum(results)/len(results)

        direction = "decreased" if avg_delta < 0 else "increased"

        return [
            f"After recent boluses, glucose {direction} by {abs(avg_delta):.1f} mg/dL on average"
        ]

    def detect_pump_anomalies(self, client_id: str) -> List[str]:
        rows = self._read_all_events(client_id)
        if not rows:
            return []

        recent = rows[-100:]
        bolus_count = sum(1 for r in recent if r.get("category") == "bolus")

        insights = []

        if bolus_count > 20:
            insights.append("High frequency of bolus events detected recently")

        overnight_temp = [
            r for r in recent
            if r.get("category") == "temp_basal" and int(r.get("hour", 0)) < 6
        ]

        if len(overnight_temp) > 5:
            insights.append("Frequent overnight temp basal usage")

        return insights

async def pump_background_task(data_root: str = "data") -> None:
    logger.info("Pump scraper task started.")
    manager = PumpManager(data_root=data_root)

    while True:
        try:
            if os.path.exists(data_root):
                for client_id in os.listdir(data_root):
                    client_path = os.path.join(data_root, client_id)
                    if os.path.isdir(client_path) and manager.has_pump_config(client_id):
                        manager.fetch_and_update(client_id)
            await asyncio.sleep(900)
        except Exception as e:
            logger.error(f"Pump background task error: {e}")
            await asyncio.sleep(60)


if __name__ == "__main__":
    manager = PumpManager(data_root="data")
    demo_client = "demo_client"
    print("Pump manager module loaded.")
    print(manager.get_context_summary(demo_client))
