# 🚀 Indian Stock Market AI Chatbot

A comprehensive AI-powered stock market analysis system for Indian stocks with real-time data collection, database management, and intelligent chatbot capabilities.

## 🌟 Features

### 📊 **Stock Database Management**
- **85+ Nifty 50 stocks** with comprehensive data
- Real-time price tracking and financial metrics
- Historical data storage and analysis
- Sector and industry classification

### 🤖 **AI-Powered Analysis**
- **OpenAI GPT Integration** for intelligent stock analysis
- **Perplexity AI Support** as alternative LLM provider
- Context-aware responses using real stock data
- Investment recommendations and risk assessment

### 🔄 **Data Collection System**
- Automated data collection from NSE/BSE
- Real-time market data updates
- Financial statements and quarterly results
- Shareholding patterns and corporate announcements

### 🌐 **Modern Web Interface**
- **FastAPI Backend** with RESTful APIs
- Interactive API documentation (Swagger UI)
- Beautiful chatbot interface
- Real-time data visualization

## 🏗️ Architecture

```
ai/
├── app/
│   ├── core/           # Configuration & database setup
│   ├── models/         # SQLAlchemy data models
│   ├── schemas/        # Pydantic data validation
│   ├── services/       # Business logic & AI services
│   └── main.py         # FastAPI application
├── frontend/           # Web interface
├── requirements.txt    # Python dependencies
└── README.md          # This file
```

## 🚀 Quick Start

### **Prerequisites**
- Python 3.8+
- PostgreSQL database
- OpenAI API key or Perplexity Pro subscription

### **Installation**

1. **Clone the repository**
```bash
git clone https://github.com/gurudayal37/indian-stock-ai-chatbot.git
cd indian-stock-ai-chatbot
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Set up environment variables**
```bash
cp .env.example .env
# Edit .env with your API keys and database credentials
```

4. **Configure database**
```bash
# Update database connection in .env
DATABASE_URL=postgresql://username:password@localhost:5432/indian_stocks
```

5. **Launch the application**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## 🔑 Configuration

### **Required API Keys**
- **OpenAI API Key**: For GPT-powered analysis
- **Perplexity API Key**: Alternative AI provider
- **Alpha Vantage API Key**: Market data (optional)

### **Environment Variables**
```bash
# AI Services
OPENAI_API_KEY=your_openai_key_here
PERPLEXITY_API_KEY=your_perplexity_key_here

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/dbname
ACTIVE_DATABASE=local

# Application
DEBUG=True
LOG_LEVEL=INFO
```

## 📱 API Endpoints

### **Stock Management**
- `GET /api/stocks` - List all stocks
- `GET /api/stocks/{symbol}` - Get specific stock details
- `GET /api/sectors` - List all sectors
- `GET /api/industries` - List industries by sector

### **AI Chatbot**
- `POST /api/chat` - Chat with AI about stocks
- `POST /api/analyze-stock` - Get comprehensive stock analysis

### **Data Collection**
- `POST /api/collect-data` - Trigger manual data collection

### **Documentation**
- `/docs` - Interactive API documentation (Swagger UI)
- `/redoc` - Alternative API documentation

## 🎯 Usage Examples

### **Chat with AI about Stocks**
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is the current market cap of RELIANCE?",
    "stock_symbol": "RELIANCE"
  }'
```

### **Get Stock Analysis**
```bash
curl -X POST "http://localhost:8000/api/analyze-stock" \
  -H "Content-Type: application/json" \
  -d '{
    "stock_symbol": "TCS",
    "analysis_type": "comprehensive"
  }'
```

## 🛠️ Technology Stack

- **Backend**: FastAPI, SQLAlchemy, PostgreSQL
- **AI/ML**: OpenAI GPT, Perplexity AI
- **Frontend**: HTML5, Tailwind CSS, JavaScript
- **Data Collection**: NSEpy, BSE, yfinance
- **Deployment**: Docker, uvicorn

## 📊 Data Sources

- **NSE (National Stock Exchange)**
- **BSE (Bombay Stock Exchange)**
- **Yahoo Finance**
- **Real-time market feeds**

## 🔒 Security Features

- Environment-based configuration
- API key management
- CORS protection
- Input validation with Pydantic
- SQL injection prevention

## 🚀 Deployment

### **Local Development**
```bash
uvicorn app.main:app --reload
```

### **Production**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### **Docker (Coming Soon)**
```bash
docker build -t stock-ai-chatbot .
docker run -p 8000:8000 stock-ai-chatbot
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **NSE & BSE** for market data
- **OpenAI** for GPT integration
- **Perplexity AI** for alternative LLM support
- **FastAPI** community for the excellent framework

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/gurudayal37/indian-stock-ai-chatbot/issues)
- **Discussions**: [GitHub Discussions](https://github.com/gurudayal37/indian-stock-ai-chatbot/discussions)

---

**Built with ❤️ for the Indian Stock Market Community**

*Last updated: August 2025*
