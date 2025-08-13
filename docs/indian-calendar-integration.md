# Indian Calendar Integration Guide

## Overview

This document provides a comprehensive guide for implementing Indian calendar systems (Panchang) in the Xiaozhi server, similar to the existing Chinese lunar calendar functionality. The implementation will support multiple Indian calendar systems including Panchang, Vikram Samvat, and regional calendars.

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Required Dependencies](#required-dependencies)
3. [Calendar Systems Overview](#calendar-systems-overview)
4. [Implementation Plan](#implementation-plan)
5. [Code Structure](#code-structure)
6. [API Design](#api-design)
7. [Configuration](#configuration)
8. [Testing Strategy](#testing-strategy)
9. [Deployment Guide](#deployment-guide)
10. [Maintenance](#maintenance)

## System Architecture

### Current vs Proposed Architecture

```
Current (Chinese Calendar):
get_lunar() → cnlunar library → Chinese calendar data → English response

Proposed (Indian Calendar):
get_panchang() → Indian calendar libraries → Panchang data → Multi-language response
get_indian_calendar() → Regional calendar support → Localized data → Regional responses
```

### Integration Points

```
Configuration (data/.config.yaml)
         ↓
   Calendar Selection (chinese/indian/both)
         ↓
   Function Registration (get_lunar/get_panchang)
         ↓
   Calendar Libraries (cnlunar/pyephem/swisseph)
         ↓
   Response Formatting (English/Hindi/Regional)
         ↓
   Cache Management (separate cache keys)
         ↓
   AI Response Generation
```

## Required Dependencies

### Python Libraries

#### Primary Libraries
```python
# Core astronomical calculations
pyephem==4.1.4              # Astronomical calculations
swisseph==2.10.03.2          # Swiss Ephemeris for precise calculations

# Indian calendar specific
indic-transliteration==2.3.37 # Script conversion (Devanagari, Tamil, etc.)
python-dateutil==2.8.2       # Date manipulation utilities

# Optional regional support
hijri-converter==2.3.1       # Islamic calendar support
nepali-datetime==1.0.7       # Nepali calendar support
```

#### Alternative Libraries
```python
# Lightweight alternatives
astral==3.2                  # Sun/moon calculations
lunardate==0.2.0            # Basic lunar calendar
pytz==2023.3                # Timezone support for regional calculations
```

### System Dependencies

#### Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install -y \
    libswisseph-dev \
    python3-dev \
    build-essential \
    libffi-dev
```

#### CentOS/RHEL
```bash
sudo yum install -y \
    epel-release \
    python3-devel \
    gcc \
    libffi-devel
```

#### Windows
```powershell
# Install Visual Studio Build Tools
# Or use conda for easier dependency management
conda install -c conda-forge pyephem swisseph
```

## Calendar Systems Overview

### 1. Panchang (Hindu Calendar)

**Components:**
- **Tithi** (Lunar Day): 30 tithis per lunar month
- **Nakshatra** (Lunar Mansion): 27 constellations
- **Yoga** (Auspicious Combination): 27 yogas
- **Karana** (Half Tithi): 11 karanas
- **Vara** (Weekday): 7 days with planetary rulers

**Calculation Method:**
```python
# Pseudo-code for Panchang calculation
def calculate_panchang(date, location):
    # Calculate lunar day (Tithi)
    tithi = calculate_tithi(date, location)
    
    # Calculate constellation (Nakshatra)
    nakshatra = calculate_nakshatra(date, location)
    
    # Calculate yoga
    yoga = calculate_yoga(date, location)
    
    # Calculate karana
    karana = calculate_karana(date, location)
    
    return {
        'tithi': tithi,
        'nakshatra': nakshatra,
        'yoga': yoga,
        'karana': karana,
        'vara': get_weekday_ruler(date)
    }
```

### 2. Regional Calendar Systems

#### Vikram Samvat (North India)
- **Era**: Starts from 57 BCE
- **Months**: 12 lunar months
- **New Year**: Chaitra Shukla Pratipada

#### Tamil Calendar (Tamil Nadu)
- **Era**: Various eras (Kali Yuga, Shalivahana Shaka)
- **Months**: 12 solar months
- **New Year**: Tamil New Year (April 14/15)

#### Bengali Calendar (West Bengal)
- **Era**: Bengali San
- **Months**: 12 solar months
- **New Year**: Pohela Boishakh (April 14/15)

### 3. Festival and Muhurat Calculations

**Major Festival Categories:**
- **Solar Festivals**: Based on sun's position
- **Lunar Festivals**: Based on moon phases
- **Stellar Festivals**: Based on star positions
- **Regional Festivals**: State/community specific

## Implementation Plan

### Phase 1: Core Infrastructure (Week 1-2)

#### 1.1 Dependency Setup
```python
# requirements.txt additions
pyephem==4.1.4
swisseph==2.10.03.2
indic-transliteration==2.3.37
python-dateutil==2.8.2
```

#### 1.2 Base Calendar Class
```python
# main/xiaozhi-server/core/utils/indian_calendar.py
class IndianCalendarBase:
    def __init__(self, date, location=None):
        self.date = date
        self.location = location or self.get_default_location()
    
    def get_default_location(self):
        # Default to New Delhi coordinates
        return {'lat': 28.6139, 'lon': 77.2090, 'timezone': 'Asia/Kolkata'}
    
    def calculate_panchang(self):
        raise NotImplementedError
    
    def get_festivals(self):
        raise NotImplementedError
    
    def get_muhurat(self):
        raise NotImplementedError
```

#### 1.3 Configuration Updates
```yaml
# data/.config.yaml additions
calendar_systems:
  enabled: ["chinese", "indian"]  # Enable multiple systems
  default: "chinese"              # Default system
  
indian_calendar:
  default_location:
    city: "New Delhi"
    latitude: 28.6139
    longitude: 77.2090
    timezone: "Asia/Kolkata"
  
  supported_regions:
    - name: "North India"
      calendar: "vikram_samvat"
      language: "hindi"
    - name: "Tamil Nadu"
      calendar: "tamil"
      language: "tamil"
    - name: "West Bengal"
      calendar: "bengali"
      language: "bengali"
  
  festivals:
    include_regional: true
    include_national: true
    max_upcoming: 10
```

### Phase 2: Panchang Implementation (Week 3-4)

#### 2.1 Panchang Calculator
```python
# main/xiaozhi-server/core/utils/panchang_calculator.py
import ephem
import swisseph as swe
from datetime import datetime, timedelta

class PanchangCalculator:
    def __init__(self, date, location):
        self.date = date
        self.location = location
        self.setup_ephemeris()
    
    def setup_ephemeris(self):
        """Initialize Swiss Ephemeris"""
        swe.set_ephe_path('/path/to/ephemeris/data')
    
    def calculate_tithi(self):
        """Calculate lunar day (Tithi)"""
        # Calculate moon and sun positions
        sun_lon = self.get_sun_longitude()
        moon_lon = self.get_moon_longitude()
        
        # Tithi = (Moon longitude - Sun longitude) / 12
        tithi_value = (moon_lon - sun_lon) % 360 / 12
        tithi_number = int(tithi_value) + 1
        
        return {
            'number': tithi_number,
            'name': self.get_tithi_name(tithi_number),
            'percentage': (tithi_value % 1) * 100,
            'end_time': self.calculate_tithi_end_time()
        }
    
    def calculate_nakshatra(self):
        """Calculate lunar mansion (Nakshatra)"""
        moon_lon = self.get_moon_longitude()
        nakshatra_number = int(moon_lon / (360/27)) + 1
        
        return {
            'number': nakshatra_number,
            'name': self.get_nakshatra_name(nakshatra_number),
            'lord': self.get_nakshatra_lord(nakshatra_number),
            'pada': self.calculate_nakshatra_pada(moon_lon)
        }
    
    def calculate_yoga(self):
        """Calculate Yoga"""
        sun_lon = self.get_sun_longitude()
        moon_lon = self.get_moon_longitude()
        
        yoga_value = (sun_lon + moon_lon) % 360 / (360/27)
        yoga_number = int(yoga_value) + 1
        
        return {
            'number': yoga_number,
            'name': self.get_yoga_name(yoga_number),
            'end_time': self.calculate_yoga_end_time()
        }
    
    def calculate_karana(self):
        """Calculate Karana (half Tithi)"""
        tithi = self.calculate_tithi()
        karana_number = ((tithi['number'] - 1) * 2) % 60 + 1
        
        return {
            'number': karana_number,
            'name': self.get_karana_name(karana_number),
            'type': self.get_karana_type(karana_number)
        }
    
    def get_sun_longitude(self):
        """Get sun's longitude using Swiss Ephemeris"""
        jd = swe.julday(self.date.year, self.date.month, self.date.day)
        result = swe.calc_ut(jd, swe.SUN)
        return result[0][0]  # Longitude in degrees
    
    def get_moon_longitude(self):
        """Get moon's longitude using Swiss Ephemeris"""
        jd = swe.julday(self.date.year, self.date.month, self.date.day)
        result = swe.calc_ut(jd, swe.MOON)
        return result[0][0]  # Longitude in degrees
```

#### 2.2 Data Mappings
```python
# main/xiaozhi-server/core/utils/indian_calendar_data.py

TITHI_NAMES = {
    1: "Pratipada", 2: "Dwitiya", 3: "Tritiya", 4: "Chaturthi",
    5: "Panchami", 6: "Shashthi", 7: "Saptami", 8: "Ashtami",
    9: "Navami", 10: "Dashami", 11: "Ekadashi", 12: "Dwadashi",
    13: "Trayodashi", 14: "Chaturdashi", 15: "Purnima/Amavasya"
}

NAKSHATRA_NAMES = {
    1: "Ashwini", 2: "Bharani", 3: "Krittika", 4: "Rohini",
    5: "Mrigashira", 6: "Ardra", 7: "Punarvasu", 8: "Pushya",
    9: "Ashlesha", 10: "Magha", 11: "Purva Phalguni", 12: "Uttara Phalguni",
    13: "Hasta", 14: "Chitra", 15: "Swati", 16: "Vishakha",
    17: "Anuradha", 18: "Jyeshtha", 19: "Mula", 20: "Purva Ashadha",
    21: "Uttara Ashadha", 22: "Shravana", 23: "Dhanishta", 24: "Shatabhisha",
    25: "Purva Bhadrapada", 26: "Uttara Bhadrapada", 27: "Revati"
}

YOGA_NAMES = {
    1: "Vishkambha", 2: "Preeti", 3: "Ayushman", 4: "Saubhagya",
    5: "Shobhana", 6: "Atiganda", 7: "Sukarma", 8: "Dhriti",
    9: "Shula", 10: "Ganda", 11: "Vriddhi", 12: "Dhruva",
    13: "Vyaghata", 14: "Harshana", 15: "Vajra", 16: "Siddhi",
    17: "Vyatipata", 18: "Variyana", 19: "Parigha", 20: "Shiva",
    21: "Siddha", 22: "Sadhya", 23: "Shubha", 24: "Shukla",
    25: "Brahma", 26: "Indra", 27: "Vaidhriti"
}

FESTIVALS_DATABASE = {
    "national": {
        "Diwali": {"type": "lunar", "month": "Kartik", "tithi": "Amavasya"},
        "Holi": {"type": "lunar", "month": "Phalguna", "tithi": "Purnima"},
        "Dussehra": {"type": "lunar", "month": "Ashwin", "tithi": "Dashami"},
        "Karva Chauth": {"type": "lunar", "month": "Kartik", "tithi": "Chaturthi"}
    },
    "regional": {
        "tamil": {
            "Tamil New Year": {"type": "solar", "date": "April 14"},
            "Pongal": {"type": "solar", "date": "January 14"}
        },
        "bengali": {
            "Durga Puja": {"type": "lunar", "month": "Ashwin", "tithi": "Saptami-Dashami"},
            "Kali Puja": {"type": "lunar", "month": "Kartik", "tithi": "Amavasya"}
        }
    }
}
```

### Phase 3: Function Integration (Week 5)

#### 3.1 New Function Implementation
```python
# main/xiaozhi-server/plugins_func/functions/get_panchang.py
from datetime import datetime
from plugins_func.register import register_function, ToolType, ActionResponse, Action
from core.utils.panchang_calculator import PanchangCalculator
from core.utils.indian_calendar_data import *

get_panchang_function_desc = {
    "type": "function",
    "function": {
        "name": "get_panchang",
        "description": (
            "Get Indian calendar (Panchang) information including Tithi, Nakshatra, Yoga, Karana, "
            "festivals, auspicious timings (Muhurat), and regional calendar details. "
            "Supports multiple Indian calendar systems including Vikram Samvat, Tamil, Bengali calendars."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "Date to query in YYYY-MM-DD format, e.g., 2024-01-01. If not provided, uses current date",
                },
                "location": {
                    "type": "string",
                    "description": "Location for calculations (city name or coordinates). Defaults to New Delhi if not specified",
                },
                "calendar_type": {
                    "type": "string",
                    "description": "Type of Indian calendar: 'panchang', 'vikram_samvat', 'tamil', 'bengali'. Defaults to 'panchang'",
                },
                "query": {
                    "type": "string",
                    "description": "Specific information to query: 'basic', 'detailed', 'festivals', 'muhurat', 'all'",
                },
            },
            "required": [],
        },
    },
}

@register_function("get_panchang", get_panchang_function_desc, ToolType.WAIT)
def get_panchang(date=None, location=None, calendar_type="panchang", query="basic"):
    """
    Get Indian calendar (Panchang) information for the specified date and location
    """
    from core.utils.cache.manager import cache_manager, CacheType
    
    # Parse date
    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            return ActionResponse(
                Action.REQLLM,
                "Date format error. Please use YYYY-MM-DD format, e.g., 2024-01-01",
                None,
            )
    else:
        target_date = datetime.now()
    
    # Set default location
    if not location:
        location = {
            'city': 'New Delhi',
            'lat': 28.6139,
            'lon': 77.2090,
            'timezone': 'Asia/Kolkata'
        }
    
    # Check cache
    cache_key = f"panchang_{target_date.strftime('%Y-%m-%d')}_{calendar_type}_{query}"
    cached_result = cache_manager.get(CacheType.PANCHANG, cache_key)
    if cached_result:
        return ActionResponse(Action.REQLLM, cached_result, None)
    
    # Calculate Panchang
    calculator = PanchangCalculator(target_date, location)
    
    response_text = f"Indian Calendar ({calendar_type.title()}) Information for {target_date.strftime('%B %d, %Y')}:\n\n"
    
    if query in ["basic", "detailed", "all"]:
        # Basic Panchang information
        tithi = calculator.calculate_tithi()
        nakshatra = calculator.calculate_nakshatra()
        yoga = calculator.calculate_yoga()
        karana = calculator.calculate_karana()
        
        response_text += f"**Panchang Details:**\n"
        response_text += f"• Tithi (Lunar Day): {tithi['name']} ({tithi['number']}/15)\n"
        response_text += f"• Nakshatra (Constellation): {nakshatra['name']} (Pada {nakshatra['pada']})\n"
        response_text += f"• Yoga: {yoga['name']}\n"
        response_text += f"• Karana: {karana['name']}\n"
        response_text += f"• Weekday Ruler: {get_weekday_ruler(target_date)}\n\n"
    
    if query in ["detailed", "all"]:
        # Detailed astronomical information
        response_text += f"**Astronomical Details:**\n"
        response_text += f"• Nakshatra Lord: {nakshatra['lord']}\n"
        response_text += f"• Tithi End Time: {tithi['end_time']}\n"
        response_text += f"• Yoga End Time: {yoga['end_time']}\n"
        response_text += f"• Moon Phase: {get_moon_phase(tithi['number'])}\n\n"
    
    if query in ["festivals", "all"]:
        # Festival information
        festivals = get_festivals_for_date(target_date, calendar_type)
        if festivals:
            response_text += f"**Festivals & Observances:**\n"
            for festival in festivals:
                response_text += f"• {festival['name']} ({festival['type']})\n"
            response_text += "\n"
    
    if query in ["muhurat", "all"]:
        # Auspicious timings
        muhurat = calculate_muhurat(target_date, location)
        response_text += f"**Auspicious Timings (Muhurat):**\n"
        response_text += f"• Sunrise: {muhurat['sunrise']}\n"
        response_text += f"• Sunset: {muhurat['sunset']}\n"
        response_text += f"• Brahma Muhurat: {muhurat['brahma_muhurat']}\n"
        response_text += f"• Abhijit Muhurat: {muhurat['abhijit_muhurat']}\n"
        
        if muhurat['auspicious_periods']:
            response_text += f"• Good Times: {', '.join(muhurat['auspicious_periods'])}\n"
        if muhurat['inauspicious_periods']:
            response_text += f"• Avoid Times: {', '.join(muhurat['inauspicious_periods'])}\n"
    
    # Cache the result
    cache_manager.set(CacheType.PANCHANG, cache_key, response_text)
    
    return ActionResponse(Action.REQLLM, response_text, None)
```

#### 3.2 Cache Type Addition
```python
# main/xiaozhi-server/core/utils/cache/config.py
class CacheType(Enum):
    # ... existing types
    PANCHANG = "panchang"  # Add this new cache type
```

### Phase 4: Multi-language Support (Week 6)

#### 4.1 Language Support
```python
# main/xiaozhi-server/core/utils/indian_calendar_translations.py
TRANSLATIONS = {
    "hindi": {
        "tithi": "तिथि",
        "nakshatra": "नक्षत्र",
        "yoga": "योग",
        "karana": "करण",
        "festivals": "त्योहार",
        "auspicious": "शुभ",
        "inauspicious": "अशुभ"
    },
    "tamil": {
        "tithi": "திதி",
        "nakshatra": "நட்சத்திரம்",
        "yoga": "யோகம்",
        "karana": "கரணம்",
        "festivals": "திருவிழாக்கள்",
        "auspicious": "நல்ல",
        "inauspicious": "கெட்ட"
    },
    "bengali": {
        "tithi": "তিথি",
        "nakshatra": "নক্ষত্র",
        "yoga": "যোগ",
        "karana": "করণ",
        "festivals": "উৎসব",
        "auspicious": "শুভ",
        "inauspicious": "অশুভ"
    }
}

def get_localized_response(data, language="english"):
    """Convert response to specified language"""
    if language == "english":
        return data
    
    # Implement transliteration logic
    from indic_transliteration import sanscript
    
    # Convert to target script
    if language == "hindi":
        return sanscript.transliterate(data, sanscript.IAST, sanscript.DEVANAGARI)
    elif language == "tamil":
        return sanscript.transliterate(data, sanscript.IAST, sanscript.TAMIL)
    # Add more languages as needed
    
    return data
```

### Phase 5: Configuration Integration (Week 7)

#### 5.1 Update Configuration Loader
```python
# main/xiaozhi-server/config/config_loader.py additions
def load_calendar_config():
    """Load calendar-specific configuration"""
    config = load_config()
    
    calendar_config = config.get('calendar_systems', {})
    indian_config = config.get('indian_calendar', {})
    
    # Validate calendar configuration
    enabled_systems = calendar_config.get('enabled', ['chinese'])
    if 'indian' in enabled_systems:
        # Ensure required Indian calendar dependencies
        validate_indian_calendar_setup(indian_config)
    
    return calendar_config, indian_config

def validate_indian_calendar_setup(config):
    """Validate Indian calendar configuration and dependencies"""
    try:
        import ephem
        import swisseph
    except ImportError as e:
        raise ImportError(f"Indian calendar dependencies missing: {e}")
    
    # Validate location configuration
    default_location = config.get('default_location', {})
    required_fields = ['latitude', 'longitude', 'timezone']
    
    for field in required_fields:
        if field not in default_location:
            raise ValueError(f"Missing required field in indian_calendar.default_location: {field}")
```

#### 5.2 Function Registration Updates
```python
# main/xiaozhi-server/core/providers/tools/server_plugins/plugin_executor.py
def get_calendar_functions(config):
    """Get calendar functions based on configuration"""
    calendar_config = config.get('calendar_systems', {})
    enabled_systems = calendar_config.get('enabled', ['chinese'])
    
    functions = []
    
    if 'chinese' in enabled_systems:
        functions.append('get_lunar')
    
    if 'indian' in enabled_systems:
        functions.append('get_panchang')
    
    return functions
```

## API Design

### Function Signatures

#### get_panchang()
```python
def get_panchang(
    date: str = None,           # "2024-01-01"
    location: str = None,       # "Mumbai" or "lat,lon"
    calendar_type: str = "panchang",  # "panchang", "vikram_samvat", "tamil"
    query: str = "basic"        # "basic", "detailed", "festivals", "muhurat", "all"
) -> ActionResponse
```

#### get_indian_festivals()
```python
def get_indian_festivals(
    date_range: str = "month",  # "week", "month", "year"
    region: str = "national",   # "national", "tamil", "bengali", etc.
    calendar_type: str = "panchang"
) -> ActionResponse
```

#### get_muhurat()
```python
def get_muhurat(
    date: str = None,
    location: str = None,
    activity: str = "general"   # "marriage", "business", "travel", "general"
) -> ActionResponse
```

### Response Format

```json
{
    "action": "REQLLM",
    "result": "Indian Calendar (Panchang) Information for January 15, 2024:\n\n**Panchang Details:**\n• Tithi: Panchami (5/15)\n• Nakshatra: Rohini (Pada 2)\n• Yoga: Siddhi\n• Karana: Bava\n• Weekday Ruler: Jupiter\n\n**Festivals:**\n• Makar Sankranti (Solar)\n• Pongal (Regional - Tamil)\n\n**Auspicious Timings:**\n• Sunrise: 07:12 AM\n• Brahma Muhurat: 05:30-06:18 AM\n• Good Times: 09:00-11:00 AM, 02:00-04:00 PM",
    "response": null
}
```

## Configuration

### Complete Configuration Example

```yaml
# data/.config.yaml
calendar_systems:
  enabled: ["chinese", "indian"]
  default: "chinese"
  auto_detect_region: true

indian_calendar:
  default_location:
    city: "New Delhi"
    latitude: 28.6139
    longitude: 77.2090
    timezone: "Asia/Kolkata"
  
  supported_regions:
    - name: "North India"
      calendar: "vikram_samvat"
      language: "hindi"
      festivals: ["diwali", "holi", "dussehra"]
    
    - name: "Tamil Nadu"
      calendar: "tamil"
      language: "tamil"
      festivals: ["pongal", "tamil_new_year"]
    
    - name: "West Bengal"
      calendar: "bengali"
      language: "bengali"
      festivals: ["durga_puja", "kali_puja"]
    
    - name: "Maharashtra"
      calendar: "vikram_samvat"
      language: "marathi"
      festivals: ["gudi_padwa", "ganesh_chaturthi"]
  
  features:
    include_muhurat: true
    include_festivals: true
    include_regional_data: true
    max_upcoming_festivals: 10
    cache_duration_hours: 24
  
  languages:
    primary: "english"
    supported: ["hindi", "tamil", "bengali", "marathi"]
    transliteration: true

# Function configuration
plugins:
  get_panchang:
    enabled: true
    default_query: "basic"
    cache_results: true
  
  get_indian_festivals:
    enabled: true
    include_regional: true
    max_results: 10
  
  get_muhurat:
    enabled: true
    activities: ["general", "marriage", "business", "travel"]
```

## Testing Strategy

### Unit Tests

#### 1. Panchang Calculation Tests
```python
# tests/test_panchang_calculator.py
import unittest
from datetime import datetime
from core.utils.panchang_calculator import PanchangCalculator

class TestPanchangCalculator(unittest.TestCase):
    def setUp(self):
        self.date = datetime(2024, 1, 15)
        self.location = {'lat': 28.6139, 'lon': 77.2090}
        self.calculator = PanchangCalculator(self.date, self.location)
    
    def test_tithi_calculation(self):
        tithi = self.calculator.calculate_tithi()
        self.assertIn('number', tithi)
        self.assertIn('name', tithi)
        self.assertBetween(tithi['number'], 1, 15)
    
    def test_nakshatra_calculation(self):
        nakshatra = self.calculator.calculate_nakshatra()
        self.assertIn('number', nakshatra)
        self.assertIn('name', nakshatra)
        self.assertBetween(nakshatra['number'], 1, 27)
    
    def test_yoga_calculation(self):
        yoga = self.calculator.calculate_yoga()
        self.assertIn('number', yoga)
        self.assertIn('name', yoga)
        self.assertBetween(yoga['number'], 1, 27)
    
    def assertBetween(self, value, min_val, max_val):
        self.assertGreaterEqual(value, min_val)
        self.assertLessEqual(value, max_val)
```

#### 2. Function Integration Tests
```python
# tests/test_get_panchang.py
import unittest
from plugins_func.functions.get_panchang import get_panchang

class TestGetPanchang(unittest.TestCase):
    def test_basic_panchang_query(self):
        result = get_panchang(date="2024-01-15", query="basic")
        self.assertEqual(result.action, "REQLLM")
        self.assertIn("Panchang Details", result.result)
        self.assertIn("Tithi", result.result)
        self.assertIn("Nakshatra", result.result)
    
    def test_detailed_panchang_query(self):
        result = get_panchang(date="2024-01-15", query="detailed")
        self.assertIn("Astronomical Details", result.result)
        self.assertIn("Nakshatra Lord", result.result)
    
    def test_festivals_query(self):
        result = get_panchang(date="2024-01-15", query="festivals")
        self.assertIn("Festivals", result.result)
    
    def test_invalid_date_format(self):
        result = get_panchang(date="invalid-date")
        self.assertIn("Date format error", result.result)
```

### Integration Tests

#### 1. Cache Integration
```python
# tests/test_panchang_cache.py
import unittest
from core.utils.cache.manager import cache_manager, CacheType
from plugins_func.functions.get_panchang import get_panchang

class TestPanchangCache(unittest.TestCase):
    def setUp(self):
        cache_manager.clear(CacheType.PANCHANG)
    
    def test_cache_storage_and_retrieval(self):
        # First call - should calculate and cache
        result1 = get_panchang(date="2024-01-15", query="basic")
        
        # Second call - should retrieve from cache
        result2 = get_panchang(date="2024-01-15", query="basic")
        
        self.assertEqual(result1.result, result2.result)
        
        # Verify cache was used
        cache_key = "panchang_2024-01-15_panchang_basic"
        cached_data = cache_manager.get(CacheType.PANCHANG, cache_key)
        self.assertIsNotNone(cached_data)
```

### Performance Tests

#### 1. Calculation Performance
```python
# tests/test_panchang_performance.py
import unittest
import time
from datetime import datetime, timedelta
from core.utils.panchang_calculator import PanchangCalculator

class TestPanchangPerformance(unittest.TestCase):
    def test_calculation_speed(self):
        """Test that panchang calculation completes within acceptable time"""
        date = datetime.now()
        location = {'lat': 28.6139, 'lon': 77.2090}
        
        start_time = time.time()
        calculator = PanchangCalculator(date, location)
        
        # Calculate all panchang elements
        tithi = calculator.calculate_tithi()
        nakshatra = calculator.calculate_nakshatra()
        yoga = calculator.calculate_yoga()
        karana = calculator.calculate_karana()
        
        end_time = time.time()
        calculation_time = end_time - start_time
        
        # Should complete within 2 seconds
        self.assertLess(calculation_time, 2.0)
    
    def test_bulk_calculation_performance(self):
        """Test performance for calculating multiple dates"""
        location = {'lat': 28.6139, 'lon': 77.2090}
        start_date = datetime.now()
        
        start_time = time.time()
        
        # Calculate for 30 days
        for i in range(30):
            date = start_date + timedelta(days=i)
            calculator = PanchangCalculator(date, location)
            calculator.calculate_tithi()
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Should complete 30 calculations within 10 seconds
        self.assertLess(total_time, 10.0)
```

## Deployment Guide

### 1. Pre-deployment Checklist

```bash
# 1. Install system dependencies
sudo apt-get install -y libswisseph-dev python3-dev build-essential

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Download ephemeris data
mkdir -p /opt/xiaozhi/ephemeris
wget -O /opt/xiaozhi/ephemeris/sepl_18.se1 ftp://ftp.astro.com/pub/swisseph/ephe/sepl_18.se1
wget -O /opt/xiaozhi/ephemeris/semo_18.se1 ftp://ftp.astro.com/pub/swisseph/ephe/semo_18.se1

# 4. Set environment variables
export SWISSEPH_PATH=/opt/xiaozhi/ephemeris

# 5. Run tests
python -m pytest tests/test_panchang* -v

# 6. Validate configuration
python -c "from config.config_loader import load_calendar_config; load_calendar_config()"
```

### 2. Configuration Deployment

```bash
# 1. Backup existing configuration
cp data/.config.yaml data/.config.yaml.backup

# 2. Update configuration with Indian calendar settings
# (Add the configuration from the Configuration section above)

# 3. Restart the server
systemctl restart xiaozhi-server

# 4. Verify functionality
curl -X POST http://localhost:8000/test-panchang \
  -H "Content-Type: application/json" \
  -d '{"date": "2024-01-15", "query": "basic"}'
```

### 3. Docker Deployment

```dockerfile
# Dockerfile additions
FROM python:3.9-slim

# Install system dependencies for Indian calendar
RUN apt-get update && apt-get install -y \
    libswisseph-dev \
    python3-dev \
    build-essential \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Download ephemeris data
RUN mkdir -p /opt/ephemeris && \
    wget -O /opt/ephemeris/sepl_18.se1 ftp://ftp.astro.com/pub/swisseph/ephe/sepl_18.se1 && \
    wget -O /opt/ephemeris/semo_18.se1 ftp://ftp.astro.com/pub/swisseph/ephe/semo_18.se1

# Set environment variables
ENV SWISSEPH_PATH=/opt/ephemeris

# Copy application code
COPY . /app
WORKDIR /app

# Install Python dependencies
RUN pip install -r requirements.txt

# Expose port
EXPOSE 8000

# Start application
CMD ["python", "app.py"]
```

### 4. Production Considerations

#### Performance Optimization
```python
# main/xiaozhi-server/core/utils/panchang_optimizer.py
class PanchangOptimizer:
    def __init__(self):
        self.calculation_cache = {}
        self.ephemeris_cache = {}
    
    def optimize_calculations(self):
        """Implement calculation optimizations"""
        # Pre-calculate common values
        # Use lookup tables for frequently accessed data
        # Implement batch processing for multiple dates
        pass
    
    def setup_ephemeris_cache(self):
        """Pre-load ephemeris data into memory"""
        # Load commonly used ephemeris data
        # Implement memory-efficient caching
        pass
```

#### Monitoring and Logging
```python
# main/xiaozhi-server/core/utils/panchang_monitor.py
import logging
from datetime import datetime

class PanchangMonitor:
    def __init__(self):
        self.logger = logging.getLogger('panchang')
        self.metrics = {
            'calculations_per_hour': 0,
            'cache_hit_rate': 0,
            'average_response_time': 0,
            'error_rate': 0
        }
    
    def log_calculation(self, date, calculation_time, cache_hit=False):
        """Log panchang calculation metrics"""
        self.logger.info(f"Panchang calculation for {date}: {calculation_time:.3f}s (cache: {cache_hit})")
        
        # Update metrics
        self.metrics['calculations_per_hour'] += 1
        if cache_hit:
            self.metrics['cache_hit_rate'] += 1
    
    def log_error(self, error, context):
        """Log panchang calculation errors"""
        self.logger.error(f"Panchang error: {error} (context: {context})")
        self.metrics['error_rate'] += 1
```

## Maintenance

### 1. Regular Updates

#### Ephemeris Data Updates
```bash
#!/bin/bash
# scripts/update_ephemeris.sh

EPHEMERIS_DIR="/opt/xiaozhi/ephemeris"
BACKUP_DIR="/opt/xiaozhi/ephemeris_backup"

# Create backup
mkdir -p $BACKUP_DIR
cp $EPHEMERIS_DIR/* $BACKUP_DIR/

# Download latest ephemeris files
wget -O $EPHEMERIS_DIR/sepl_18.se1 ftp://ftp.astro.com/pub/swisseph/ephe/sepl_18.se1
wget -O $EPHEMERIS_DIR/semo_18.se1 ftp://ftp.astro.com/pub/swisseph/ephe/semo_18.se1

# Verify files
python -c "
import swisseph as swe
swe.set_ephe_path('$EPHEMERIS_DIR')
print('Ephemeris files updated successfully')
"

# Restart service
systemctl restart xiaozhi-server
```

#### Festival Database Updates
```python
# scripts/update_festivals.py
import json
from datetime import datetime

def update_festival_database():
    """Update festival database with new entries"""
    
    # Load current database
    with open('core/utils/indian_calendar_data.py', 'r') as f:
        current_data = f.read()
    
    # Add new festivals (example)
    new_festivals = {
        "2024": {
            "Maha Shivratri": {"date": "2024-03-08", "type": "lunar"},
            "Ram Navami": {"date": "2024-04-17", "type": "lunar"}
        }
    }
    
    # Update and save
    # Implementation depends on data structure
    print("Festival database updated")

if __name__ == "__main__":
    update_festival_database()
```

### 2. Performance Monitoring

#### Daily Health Checks
```bash
#!/bin/bash
# scripts/panchang_health_check.sh

# Test basic functionality
python -c "
from plugins_func.functions.get_panchang import get_panchang
from datetime import datetime

result = get_panchang(date=datetime.now().strftime('%Y-%m-%d'))
if 'Panchang Details' in result.result:
    print('✓ Panchang calculation working')
else:
    print('✗ Panchang calculation failed')
    exit(1)
"

# Check cache performance
python -c "
from core.utils.cache.manager import cache_manager, CacheType

stats = cache_manager.get_stats(CacheType.PANCHANG)
hit_rate = stats.get('hit_rate', 0)

if hit_rate > 0.8:
    print(f'✓ Cache performance good ({hit_rate:.2%} hit rate)')
else:
    print(f'⚠ Cache performance low ({hit_rate:.2%} hit rate)')
"

# Check ephemeris data
python -c "
import swisseph as swe
import os

if os.path.exists('/opt/xiaozhi/ephemeris/sepl_18.se1'):
    print('✓ Ephemeris data available')
else:
    print('✗ Ephemeris data missing')
    exit(1)
"

echo "Panchang health check completed"
```

### 3. Troubleshooting Guide

#### Common Issues and Solutions

**Issue 1: Swiss Ephemeris Import Error**
```bash
# Solution
sudo apt-get install libswisseph-dev
pip install --force-reinstall swisseph
```

**Issue 2: Calculation Accuracy Issues**
```python
# Verify ephemeris data
import swisseph as swe
swe.set_ephe_path('/opt/xiaozhi/ephemeris')

# Test calculation
jd = swe.julday(2024, 1, 15)
result = swe.calc_ut(jd, swe.SUN)
print(f"Sun longitude: {result[0][0]}")  # Should be reasonable value
```

**Issue 3: Performance Degradation**
```python
# Check cache status
from core.utils.cache.manager import cache_manager, CacheType

# Clear old cache entries
cache_manager.clear_expired(CacheType.PANCHANG)

# Monitor calculation times
import time
start = time.time()
# ... perform calculation
end = time.time()
print(f"Calculation time: {end - start:.3f}s")
```

## Conclusion

This implementation guide provides a comprehensive approach to adding Indian calendar support to the Xiaozhi server. The modular design allows for:

- **Gradual Implementation**: Can be implemented in phases
- **Extensibility**: Easy to add new regional calendars
- **Performance**: Optimized calculations with caching
- **Maintainability**: Clear separation of concerns
- **Scalability**: Supports multiple users and locations

The system maintains compatibility with existing Chinese calendar functionality while providing rich Indian calendar features including Panchang calculations, festival information, and auspicious timing calculations.

For questions or support during implementation, refer to the troubleshooting section or create detailed issue reports with calculation examples and expected vs. actual results.