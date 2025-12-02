mlb_standings_predictor/
├── data/
│   ├── raw/
│   │   └── espn_mlb_standings_2003_2025.json  # (Ignorado por Git)
│   └── processed/
├── notebooks/
├── src/
│   ├── __init__.py
│   ├── data_extraction/
│   │   └── espn_api_scraper.py  # 👈 Script para la API de ESPN
│   ├── data_processing/
│   │   └── feature_engineer.py
│   ├── models/
│   │   └── train_predictor.py
│   └── prediction/
│       └── predict_2026.py     # Script para generar la tabla final de predicción
├── models/
│   └── predictor_v1.pkl       # (Ignorado por Git si es grande)
├── reports/
│   └── predictions/
│       └── 2026_standings.csv # 👈 Tabla final de predicción
├── config/
│   └── api_keys.py            # (Ignorado por Git)
├── .gitignore
├── requirements.txt
└── README.md