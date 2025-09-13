# Daily OHLCV Data Syncer

A comprehensive daily data synchronization system that fetches, validates, and stores OHLCV (Open, High, Low, Close, Volume) price data for all NIFTY 500 stocks.

## 🚀 Features

### Core Functionality
- **Daily Sync**: Automatically runs at 5 PM every day
- **Data Validation**: Validates last day's data against Yahoo Finance
- **Complete Refresh**: Automatically refreshes all data if validation fails
- **Incremental Updates**: Only fetches new data to minimize API calls
- **Error Handling**: Comprehensive error handling and retry logic

### Data Management
- **1 Year Coverage**: Fetches complete 1-year historical data
- **Data Integrity**: Validates data consistency with configurable tolerance
- **Sync Tracking**: Tracks sync status and last update times
- **Logging**: Comprehensive logging for monitoring and debugging

## 📁 Files

### Main Scripts
- `scripts/daily_ohlcv_syncer.py` - Main syncer script
- `scripts/setup_daily_sync_cron.sh` - Cron job setup script
- `scripts/run_daily_sync.sh` - Cron execution wrapper
- `scripts/test_daily_syncer.py` - Test script

### Logs
- `logs/daily_ohlcv_sync.log` - Main sync logs
- `logs/cron_sync.log` - Cron execution logs
- `logs/test_daily_syncer.log` - Test logs

## 🛠️ Setup

### 1. Install Dependencies
```bash
pip install yfinance pandas sqlalchemy
```

### 2. Setup Cron Job
```bash
# Make scripts executable
chmod +x scripts/setup_daily_sync_cron.sh
chmod +x scripts/run_daily_sync.sh
chmod +x scripts/daily_ohlcv_syncer.py

# Setup cron job (runs at 5 PM daily)
./scripts/setup_daily_sync_cron.sh
```

### 3. Verify Setup
```bash
# Check cron job
crontab -l

# Test the syncer
python3 scripts/test_daily_syncer.py
```

## 🎯 Usage

### Manual Execution
```bash
# Sync all stocks
python3 scripts/daily_ohlcv_syncer.py

# Sync specific stock
python3 scripts/daily_ohlcv_syncer.py --symbol RELIANCE

# Validate existing data only
python3 scripts/daily_ohlcv_syncer.py --validate-only

# Custom validation tolerance (default: 1%)
python3 scripts/daily_ohlcv_syncer.py --tolerance 0.02
```

### Testing
```bash
# Run all tests
python3 scripts/test_daily_syncer.py

# Test specific stock
python3 scripts/test_daily_syncer.py --symbol RELIANCE

# Test validation only
python3 scripts/test_daily_syncer.py --validate-only
```

## 🔧 Configuration

### Validation Tolerance
- **Default**: 1% (0.01)
- **Purpose**: Determines how much price difference is acceptable
- **Usage**: `--tolerance 0.02` for 2% tolerance

### Data Sources
- **Primary**: Yahoo Finance (yfinance)
- **Symbol Format**: `{NSE_SYMBOL}.NS`
- **Data Range**: 1 year historical data

### Sync Schedule
- **Time**: 5:00 PM daily
- **Timezone**: System timezone
- **Cron Expression**: `0 17 * * *`

## 📊 Data Flow

### 1. Data Validation
```
Last DB Data → Compare with Yahoo Finance → Within Tolerance?
                                                      ↓
                                                 Yes → Continue
                                                      ↓
                                                 No → Delete All Data
```

### 2. Data Fetching
```
Check Last Sync Date → Fetch New Data → Save to Database → Update Sync Tracker
```

### 3. Complete Refresh
```
Validation Failed → Delete All OHLCV Data → Fetch 1 Year Data → Save All Data
```

## 🗄️ Database Schema

### DailyPrice Table
```sql
CREATE TABLE daily_prices (
    id SERIAL PRIMARY KEY,
    stock_id INTEGER REFERENCES stocks(id),
    date DATE NOT NULL,
    open_price FLOAT NOT NULL,
    high_price FLOAT NOT NULL,
    low_price FLOAT NOT NULL,
    close_price FLOAT NOT NULL,
    volume INTEGER,
    turnover FLOAT,
    vwap FLOAT,
    delivery_quantity INTEGER,
    delivery_percentage FLOAT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### SyncTracker Table
```sql
CREATE TABLE sync_tracker (
    id SERIAL PRIMARY KEY,
    stock_id INTEGER REFERENCES stocks(id),
    data_type VARCHAR(50) NOT NULL,
    last_sync_time TIMESTAMP DEFAULT NOW(),
    last_data_date DATE,
    records_count INTEGER DEFAULT 0,
    sync_status VARCHAR(20) DEFAULT 'success',
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(stock_id, data_type)
);
```

## 📈 Monitoring

### Log Files
- **Main Logs**: `logs/daily_ohlcv_sync.log`
- **Cron Logs**: `logs/cron_sync.log`
- **Test Logs**: `logs/test_daily_syncer.log`

### Log Levels
- **INFO**: Normal operations and progress
- **WARNING**: Non-critical issues (e.g., no new data)
- **ERROR**: Critical errors that need attention

### Key Metrics
- **Sync Success Rate**: Percentage of successful syncs
- **Data Validation Rate**: Percentage of data that passes validation
- **Complete Refresh Rate**: Percentage of stocks requiring complete refresh

## 🔍 Troubleshooting

### Common Issues

#### 1. No Data from Yahoo Finance
```bash
# Check if stock symbol exists
python3 scripts/daily_ohlcv_syncer.py --symbol RELIANCE

# Check Yahoo Finance directly
python3 -c "import yfinance as yf; print(yf.Ticker('RELIANCE.NS').history(period='1d'))"
```

#### 2. Validation Failures
```bash
# Check validation tolerance
python3 scripts/daily_ohlcv_syncer.py --tolerance 0.05

# Validate existing data only
python3 scripts/daily_ohlcv_syncer.py --validate-only
```

#### 3. Database Connection Issues
```bash
# Test database connection
python3 scripts/test_daily_syncer.py

# Check environment variables
echo $PYTHONPATH
echo $ACTIVE_DATABASE
```

#### 4. Cron Job Not Running
```bash
# Check cron service
sudo systemctl status cron

# Check cron logs
tail -f /var/log/cron

# Check our cron logs
tail -f logs/cron_sync.log
```

### Debug Mode
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
python3 scripts/daily_ohlcv_syncer.py
```

## 📋 Maintenance

### Daily Tasks
- Monitor sync logs for errors
- Check sync success rates
- Verify data quality

### Weekly Tasks
- Review validation failure rates
- Check for stocks with consistent sync issues
- Update stock symbols if needed

### Monthly Tasks
- Analyze sync performance trends
- Review and update validation tolerance if needed
- Clean up old log files

## 🚨 Alerts

### Critical Alerts
- Sync failure rate > 10%
- Database connection errors
- Yahoo Finance API errors

### Warning Alerts
- Validation failure rate > 5%
- No new data for > 3 days
- Sync duration > 2 hours

## 📊 Performance

### Expected Performance
- **Sync Time**: 30-60 minutes for all stocks
- **API Calls**: ~500 calls per day (1 per stock)
- **Data Volume**: ~1-2 MB per day
- **Storage**: ~500 MB per year

### Optimization
- **Rate Limiting**: 1 second delay between stocks
- **Caching**: Yahoo Finance data caching
- **Batch Processing**: Process stocks in batches
- **Error Recovery**: Automatic retry on failures

## 🔒 Security

### Data Protection
- **No Sensitive Data**: Only public market data
- **API Keys**: No API keys required
- **Database**: Secure database connections

### Access Control
- **Script Permissions**: Executable by owner only
- **Log Access**: Readable by owner only
- **Cron Jobs**: User-specific cron jobs

## 📚 API Reference

### DailyOHLCVSyncer Class

#### Methods
- `get_all_stocks()` - Get all active stocks
- `get_stock_by_symbol(symbol)` - Get stock by symbol
- `get_latest_ohlcv_data(stock)` - Get latest OHLCV data
- `fetch_yahoo_data(stock, start_date, end_date)` - Fetch Yahoo data
- `validate_ohlcv_data(db_data, yahoo_data)` - Validate data
- `sync_stock_ohlcv(stock, validate_only)` - Sync single stock
- `sync_all_stocks(validate_only)` - Sync all stocks

#### Parameters
- `validation_tolerance` - Price validation tolerance (default: 0.01)
- `symbol` - Stock symbol for specific sync
- `validate_only` - Only validate, don't fetch new data

## 🤝 Contributing

### Adding New Features
1. Update the main syncer script
2. Add corresponding tests
3. Update documentation
4. Test thoroughly

### Reporting Issues
1. Check logs first
2. Run test script
3. Provide error details
4. Include system information

## 📄 License

This project is part of the PEAD Trading Strategy system and follows the same license terms.

---

**Last Updated**: $(date)
**Version**: 1.0.0
**Maintainer**: PEAD Trading Strategy Team
