# Quote automation

Automates fabrication quoting workflows, starting with a SecturaFAB REST API client.

## SecturaFAB API

Auth uses OAuth2 resource-owner password credentials against:

`POST https://www.secturafab.com/token`

### Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env with your SecturaFAB username/password (and tenant if required)
```

### Commands

```bash
# Validate login
python -m secturafab auth-check

# Authenticate + probe common API routes; writes .discovery/
python -m secturafab discover

# Current user (if Account route exists)
python -m secturafab whoami

# List quotes (adaptive path probing)
python -m secturafab list-quotes --top 10
```

### Library usage

```python
from secturafab import SecturaFabClient
from secturafab.quotes import QuoteService

client = SecturaFabClient()
client.authenticate()
quotes = QuoteService(client).list_quotes()
```

After `discover` succeeds, use the routes/OpenAPI dump in `.discovery/` to harden quote create/update payloads for your tenant.
