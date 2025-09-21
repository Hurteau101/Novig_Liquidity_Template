# Novig Liquidity

A Python wrapper around the Novig API with built-in filtering and validation.  
This package helps you fetch sports market data and filter it based on liquidity and stat types.

## Installation

Clone the repo and install locally:

```bash
git clone https://github.com/<your-username>/novig-liquidity.git
cd novig-liquidity
pip install -e .
```

Or install directly with pip:

```bash
pip install git+https://github.com/<your-username>/novig-liquidity.git
```

## Requirements

Dependencies are listed in `requirements.txt` and are installed automatically. Core ones include:

- `aiohttp`
- `redis`
- `pydantic`
- `requests`

## Usage

Create a `filters.json` file defining which stat types you care about. Example:

```json
{
  "WNBA": [
    {
      "raw_name": "points_rebounds_assists",
      "display_name": "Points, Rebounds, and Assists",
      "active": true
    },
    {
      "raw_name": "points",
      "display_name": "Points",
      "active": true
    },
    {
      "raw_name": "rebounds_assists",
      "display_name": "Rebounds and Assists",
      "active": true
    },
    {
      "raw_name": "points_assists",
      "display_name": "Points and Assists",
      "active": true
    },
    {
      "raw_name": "points_rebounds",
      "display_name": "Points and Rebounds",
      "active": true
    },
    {
      "raw_name": "three_pointers_made",
      "display_name": "Three Pointers Made",
      "active": true
    },
    {
      "raw_name": "double_double",
      "display_name": "Double-Double",
      "active": true
    }
  ],
  "NFL": [
    {
      "raw_name": "rushing_yards",
      "display_name": "Rushing Yards",
      "active": true
    },
    {
      "raw_name": "rushing_attempts",
      "display_name": "Rushing Attempts",
      "active": true
    },
    {
      "raw_name": "longest_rush",
      "display_name": "Longest Rush",
      "active": true
    },
    {
      "raw_name": "passing_yards",
      "display_name": "Passing Yards",
      "active": true
    },
    {
      "raw_name": "receiving_yards",
      "display_name": "Receiving Yards",
      "active": true
    },
    {
      "raw_name": "receptions",
      "display_name": "Receptions",
      "active": true
    },
    {
      "raw_name": "longest_reception",
      "display_name": "Longest Receptions",
      "active": true
    },
    {
      "raw_name": "passing_completions",
      "display_name": "Passing Completions",
      "active": true
    }
  ]
}
```

### Example script

```python
import asyncio
import json
from Config import Novig

if __name__ == "__main__":
    # Load filters from file
    with open("filters.json", "r") as f:
        filters = json.load(f)

    # Choose your filter type and amounts
    total_and_difference_filter = {
        # "filter_type": "total_difference",
        "filter_type": "total_and_difference",
        "difference_amount": 3000,
        "highest_order_amount": 1500
    }
    
    # OR
    
    total_difference_filter = {
        "filter_type": "total_difference",
        "difference_amount": 3000,
    }
        
    

    # Create Novig instance
    novig = Novig(filters=filters, filter_amount_dict=total_and_difference_filter)

    # Run it
    results = asyncio.run(novig.run())
    print(results)
```

## Filter Types

Two filter types are currently supported:

1. **`total_difference`**  
   Keeps markets where the liquidity difference between over/under is at least `difference_amount`.

2. **`total_and_difference`**  
   Keeps markets where:
   - Liquidity difference ≥ `difference_amount`, **and**
   - Either over/under side has a highest order with `liquidity_left` ≥ `highest_order_amount`.

## Output

`novig.run()` returns a dict keyed by league name (e.g., `"WNBA"`, `"NFL"`), each with a list of filtered market entries. Each entry includes:
- `key_name` (market description)
- `liquidity` (grouped by `over`/`under`, includes `highest_order`, totals, etc.)
- `additional_data` (player name, stat type, line, game title, start time)

## Features

- Async API calls via `aiohttp`
- Filtering on liquidity differences and totals
- Stat-type validation via your `filters.json`
- Clean models (Pydantic + dataclasses where applicable)
