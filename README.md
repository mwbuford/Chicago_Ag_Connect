# Chicago Ag Connect

Connect Chicago neighbors with farmers markets, urban farms, and food-access sites — plus garden advice and an AI Plant Doctor trained for real leaf photos.

Inspired by organizations like [Urban Growers Collective](https://www.urbangrowerscollective.org/).

## Features

- **Markets & food access map** — Chicago farmers markets, urban farms, CSAs, and related sites (SNAP / Link Match friendly)
- **Garden advisory** — soil, frost timing, and beginner crops for Chicago Zone 5/6 city lots and raised beds
- **Learn & Grow** — paths for backyard gardens, community garden plots, and selling at neighborhood markets
- **AI Plant Doctor** — leaf disease classifier (`PlantPathologyNet`) with organic remedies; weights trained on the open-source [PlantDoc](https://github.com/pratikkayal/PlantDoc-Dataset) dataset
- **Agronomy chat** — Chicago-focused Q&A for raised beds, lead-safe soil, community gardens, and markets

## Quick start

**Requirements:** Python 3.11+ recommended.

```bash
git clone <your-repo-url> Chicago-Ag-Connect
cd Chicago-Ag-Connect

python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

./scripts/run_dev.sh
```

Open **http://127.0.0.1:8000**

API docs: **http://127.0.0.1:8000/docs**

### Manual launch

```bash
export PYTHONPATH=.
.venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

## Project layout

```
backend/
  main.py                 # FastAPI app
  static/                 # Web UI (HTML/CSS/JS)
  routes/                 # API routers
  services/               # Map, advisory, vision, marketplace, …
  ml/                     # Plant Doctor model + training
  data/                   # Crop library, learning paths, extensions
data/
  processed/              # App data (locations, overlays) — required to run
  raw/                    # Optional USDA spreadsheets / PlantDoc (gitignored)
scripts/
  run_dev.sh
  download_plantdoc.py
  ingest_chicago_overlays.py
  ingest_usda.py
tests/
```

## Tests

```bash
export PYTHONPATH=.
.venv/bin/python tests/run_consumer_tests.py
.venv/bin/python tests/test_chicagoland.py
.venv/bin/python tests/test_ai_models.py
```

## Retrain Plant Doctor (optional)

Trained weights ship in `backend/ml/weights/plant_disease_model.pt`. To retrain on PlantDoc:

```bash
export PYTHONPATH=.
.venv/bin/python scripts/download_plantdoc.py
.venv/bin/python backend/ml/train_vision_classifier.py --epochs 5 --batch-size 32
```

PlantDoc citation: Singh et al., *PlantDoc: A Dataset for Visual Plant Disease Detection*, CoDS-COMAD 2020.

## Notes for GitHub

- `.venv/`, PlantDoc images, and raw USDA `.xlsx` files are gitignored (large / regenerable).
- Processed location data under `data/processed/` is included so the map works out of the box.
- Marketplace auth files start empty — create accounts in the UI after launch.
- Do not commit `.env` files or real user credentials.

## License

Add a license of your choice before publishing (e.g. MIT). PlantDoc remains under its upstream terms.
