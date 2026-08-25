# Vehicle Ad Automation

One pipeline:

```
source → ingest → canonicalize → preflight → ready/rejected → Playwright post → report
```

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
cp .env.example .env
chmod +x run.sh
```

## Source data

Put listings under:

- `data/vehicles/<id>/vehicle.json` (optional `source.html`)
- or `data/inventory.json` / `data/inventory.csv` (same canonical schema)

Images are downloaded/copied to `data/images/<id>/`.

## Commands

```bash
./run.sh prepare                 # ingest → canonicalize → preflight
./run.sh inspect-source --id 11195371
./run.sh test
./run.sh dry-run-one 11195371    # blocked until form map core fields inspected
./run.sh dry-run
./run.sh post-one 11195371
./run.sh post
./run.sh inspect                 # login, open form, dump selectors
```

Equivalent Python:

```bash
python -m app.pipeline --prepare
python -m app.pipeline --id 11195371 --dry-run
python -m app.pipeline --batch --dry-run
python -m app.pipeline --batch --submit
```

## Validation

`app/validation/preflight.py` is the only gate before the browser.

Requires year, make, model, price, mileage, transmission, fuel, drive_type, colour, seats,
contact, dealer name/address, ≥3 features, ≥1 highlight, **exactly 5** local images,
fixed category path:

`Vehicles → Cars - Parts → Used cars in South Africa`

Outputs:

- `data/ready/ready_to_post.json`
- `data/rejected/rejected.json` (with reasons)
- `data/canonical/<id>.json`
- `data/reports/`

Rejected ads never open Playwright.

## Destination form map

Static map: `config/form_map.json`

- Category cascade + SA extra fields (`exf_111`…`exf_128`) and image uploader were inspected
  via public JomClassifieds AJAX/JS (no login).
- Core fields (title, description, price, location/country, submit) need an authenticated
  session. Run `./run.sh inspect`, merge selectors into `form_map.json`, set
  `ready_for_browser: true`.

Dropdown aliases: `config/dropdown_map.json` (explicit only; unknown values reject).

Country and location are separate fields — never aliased together.

## Posting rules

The poster only fills from ready canonical records + the static form map.

It does **not** scrape, parse descriptions, guess selectors, or invent dropdown values.

Dry-run fills and verifies; it does not click submit.
