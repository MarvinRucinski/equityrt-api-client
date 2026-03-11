# Unofficial Python client for EquityRT API

Library for interacting with [EquityRT](https://www.equityrt.com/) API, providing methods for authentication, data retrieval, and function invocation.

## Installation

```bash
pip install "git+https://github.com/MarvinRucinski/equityrt-api-client.git"
```

Import:

```python
from equityrt_api_client import EquityRTClient
```

---

## Quick Start

```python
from equityrt_api_client import EquityRTClient

client = EquityRTClient()
token = client.authenticate(username="email@email.com", password="YOUR_PASSWORD")

# Echo - simple test method to check connectivity and token validity
echo_result = client.echo(version="2.6.5.471", echo=402710)
print(echo_result)

# Get add-in information (e.g. available functions and parameters)
addin_result = client.add_in(version="2.6.5.471")
print(addin_result)
```

---

## API Methods

- `authenticate(username, password, authentication_type="UsernamePassword", set_as_default_token=True) -> str`
- `echo(version, echo, ua_cpu="AMD64")`
- `add_in(version, token=None)`
- `invoke(functions, token=None, culture_info=None)`
- `function_list_search_field(text, source_code, token=None)`
- `select_countries(classifications=None, zones=None, token=None)`
- `source_list(countries, token=None)`
- `select_securities(source_code, date1, date2, classifications=None, peers=None, is_financial_wizard=False, token=None)`
- `populate_formula_grid(formula_object_id, source_code, grid_type, token=None)`

---

## Usage Examples

### Get add-in information (e.g. available functions and parameters)

```python
addin_info = client.add_in(version="2.6.5.471")
print(addin_info)
```

### Search functions

```python
search_result = client.function_list_search_field(text="clos", source_code="PL")
print(search_result)
```

### List countries

```python
countries_result = client.select_countries(classifications=[], zones=[])
print(countries_result)
```

Example with zone filter:

```python
countries_europe = client.select_countries(zones=["EUROPE"])
print(countries_europe)
```

### List exchanges for countries

```python
sources_result = client.source_list(countries=["PL", "US", "DE"])
print(sources_result)
```

### List securities / indexes for source

```python
securities_result = client.select_securities(
	source_code="ZAA",
	date1="2026-03-11",
	date2="2026-03-11",
)
print(securities_result)
```

### Populate formula grid (function metadata)

```python
formula_grid_result = client.populate_formula_grid(
	formula_object_id="fte.787004",
	source_code="PL",
	grid_type="Search",
)
print(formula_grid_result)
```

---

## Invoke Format (`RasDaily` example)

```python
invoke_result = client.invoke(
	functions=[
		{
			"I": 0,
			"F": "RasDaily",
			"A": [
				{"S": "PKN:PL"},
				{"D": 2024.0},
				{"S": "CLOSE"},
				{"S": "DEFAULT"},
				{"M": ""},
				{"D": 1.0},
			],
		}
	],
	culture_info={
		"DatePattern": "d.MM.yyyy",
		"DecimalSeparator": ",",
		"GroupSeparator": "_",
	},
)
print(invoke_result)
```

Meaning:

- `I` – function index in batch (used when sending multiple functions)
- `F` – function name
- `A` – arguments list

Argument type markers:

- `S` = string
- `D` = decimal/number
- `M` = missing/empty value

---

## Integration Tests

Tests are in [tests/test_integration_equityrt_api.py](tests/test_integration_equityrt_api.py).

Set env vars:

```bash
export EQUITYRT_TOKEN="YOUR_TOKEN"
export EQUITYRT_USERNAME="email@email.com"  # optional (auth test)
export EQUITYRT_PASSWORD="YOUR_PASSWORD"    # optional (auth test)
export EQUITYRT_VERSION="2.6.5.471"         # optional
export EQUITYRT_SYMBOL="PKN:PL"             # optional
export EQUITYRT_DAY="2024"                  # optional
```

Run:

```bash
python -m unittest tests/test_integration_equityrt_api.py -v
```

If required env vars are missing, tests are skipped automatically.

