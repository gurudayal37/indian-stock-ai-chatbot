# Stock Analysis Dashboard

A modern web application for analyzing Indian stock market data, built with FastAPI and Bootstrap.

## Features

- **Stock Dashboard**: View all Nifty 50 stocks with key metrics
- **Stock Analysis**: Detailed stock information, price charts, and quarterly results
- **Interactive Charts**: OHLCV price charts using Chart.js
- **Responsive Design**: Mobile-first UI built with Bootstrap 5

## Tech Stack

- **Backend**: FastAPI (Python)
- **Frontend**: HTML, CSS, JavaScript, Bootstrap 5, Chart.js
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Data Source**: Yahoo Finance API

## Quick Start

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd stock-analysis-dashboard
   ```

2. **Set up virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp env.example .env
   # Edit .env with your database credentials
   ```

5. **Run the application**
   ```bash
   python app/main.py
   ```

6. **Open browser**
   - Home: http://localhost:8000/
   - Stock Detail: http://localhost:8000/stock/RELIANCE

## Project Structure

```
├── app/
│   ├── api/           # API endpoints
│   ├── core/          # Database and config
│   ├── models/        # Database models
│   ├── schemas/       # Pydantic schemas
│   ├── templates/     # HTML templates
│   └── main.py        # FastAPI application
├── scripts/            # Data sync scripts
├── requirements.txt    # Python dependencies
└── .env               # Environment variables
```

## Data Synchronization

Use the included scripts to sync stock data:

- `scripts/populate_nifty50_stocks.py` - Populate basic stock information
- `scripts/smart_yahoo_syncer.py` - Sync financial data from Yahoo Finance

## License

MIT License - see LICENSE file for details.
