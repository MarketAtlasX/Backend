"""
Seed the frontend-facing tables (countries, trade_routes, military_relations, ports)
with the 50-country dataset from frontend/src/data/countries.ts and relations.ts.

Usage:
    python -m scripts.seed_frontend_data
"""

import asyncio
import logging

from sqlalchemy import delete, select

from app.database import AsyncSessionLocal
from app.models.country import Country
from app.models.military_relation import MilitaryRelation
from app.models.port import Port
from app.models.trade_route import TradeRoute

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Country data — from frontend/src/data/countries.ts
# ---------------------------------------------------------------------------

countries_data = [
    # Americas
    {"code": "US", "name": "United States", "region": "Americas", "stock_exchange": "NYSE / NASDAQ", "currency": "USD", "currency_symbol": "$", "market_cap": "$50.8T", "trading_hours": "09:30-16:00 ET", "tickers": "AAPL,MSFT,GOOGL,AMZN,TSLA,JPM,V,NVDA,META", "latitude": 37.09, "longitude": -95.71, "commodities": "Oil,Natural Gas,Corn,Soybeans,Wheat,Copper,Gold,LNG,Semiconductors,Automobiles,Aerospace", "port_names": "Port of Los Angeles,Port of New York & New Jersey,Port of Houston,Port of Long Beach,Port of Savannah"},
    {"code": "CA", "name": "Canada", "region": "Americas", "stock_exchange": "TSX", "currency": "CAD", "currency_symbol": "C$", "market_cap": "$3.2T", "trading_hours": "09:30-16:00 ET", "tickers": "SHOP,RY,TD,ENB,CNQ,BMO,BNS,SU,TRP,CM", "latitude": 56.13, "longitude": -106.35, "commodities": "Oil,Natural Gas,Gold,Potash,Uranium,Timber,Wheat,Nickel", "port_names": "Port of Vancouver,Port of Montreal,Port of Prince Rupert"},
    {"code": "BR", "name": "Brazil", "region": "Americas", "stock_exchange": "B3", "currency": "BRL", "currency_symbol": "R$", "market_cap": "$1.1T", "trading_hours": "10:00-17:00 BRT", "tickers": "PETR4,VALE3,ITUB4,ABEV3,WEGE3,SUZB3,BBAS3", "latitude": -14.24, "longitude": -51.93, "commodities": "Iron Ore,Coffee,Soybeans,Sugar,Beef,Oil,Gold,Orange Juice", "port_names": "Port of Santos,Port of Rio de Janeiro,Port of Paranaguá"},
    {"code": "MX", "name": "Mexico", "region": "Americas", "stock_exchange": "BMV", "currency": "MXN", "currency_symbol": "Mex$", "market_cap": "$450B", "trading_hours": "08:30-15:00 CST", "tickers": "AMXL,FEMSA,WALMEX,GFNORTE,GMEXICO,CEMEX", "latitude": 23.63, "longitude": -102.55, "commodities": "Oil,Silver,Gold,Avocados,Automobiles,Copper,Electronics", "port_names": "Port of Manzanillo,Port of Veracruz,Port of Altamira"},
    {"code": "AR", "name": "Argentina", "region": "Americas", "stock_exchange": "BCBA", "currency": "ARS", "currency_symbol": "AR$", "market_cap": "$85B", "trading_hours": "11:00-17:00 ART", "tickers": "GGAL,YPF,PAMP,CEPU,TECO2", "latitude": -38.42, "longitude": -63.62, "commodities": "Soybeans,Corn,Wheat,Beef,Wine,Lithium,Natural Gas", "port_names": "Port of Buenos Aires,Port of Rosario"},
    {"code": "CL", "name": "Chile", "region": "Americas", "stock_exchange": "BCS", "currency": "CLP", "currency_symbol": "CLP$", "market_cap": "$210B", "tickers": "COPEC,BSANTANDER,CMPC,ENELAM,FALABELLA", "latitude": -35.68, "longitude": -71.54, "commodities": "Copper,Lithium,Gold,Silver,Wine,Salmon,Fruit", "port_names": "Port of Valparaiso,Port of San Antonio"},
    {"code": "CO", "name": "Colombia", "region": "Americas", "stock_exchange": "BVC", "currency": "COP", "currency_symbol": "COL$", "market_cap": "$140B", "tickers": "ECOPETROL,GRUPOSURA,BCOLOMBIA,NUTRESA,ISA", "latitude": 4.57, "longitude": -74.30, "commodities": "Oil,Coffee,Gold,Coal,Bananas,Flowers", "port_names": "Port of Cartagena,Port of Buenaventura"},
    # Europe
    {"code": "GB", "name": "United Kingdom", "region": "Europe", "stock_exchange": "LSE", "currency": "GBP", "currency_symbol": "£", "market_cap": "$3.4T", "trading_hours": "08:00-16:30 GMT", "tickers": "HSBA,ULVR,SHEL,BP,GSK,DGE,RIO,GLEN,LLOY", "latitude": 55.38, "longitude": -3.44, "commodities": "Oil,Natural Gas,Gold,Pharmaceuticals,Financial Services,Aerospace", "port_names": "Port of Felixstowe,Port of Southampton,Port of London"},
    {"code": "DE", "name": "Germany", "region": "Europe", "stock_exchange": "FWB (Frankfurt)", "currency": "EUR", "currency_symbol": "€", "market_cap": "$2.2T", "trading_hours": "08:00-20:00 CET", "tickers": "SAP,ALV,DBK,VOW3,BAYN,BMW,ADS,MRK,LIN", "latitude": 51.17, "longitude": 10.45, "commodities": "Automobiles,Chemicals,Steel,Machinery,Pharmaceuticals,Electronics", "port_names": "Port of Hamburg,Port of Bremen,Port of Wilhelmshaven"},
    {"code": "FR", "name": "France", "region": "Europe", "stock_exchange": "Euronext Paris", "currency": "EUR", "currency_symbol": "€", "market_cap": "$2.8T", "trading_hours": "09:00-17:30 CET", "tickers": "MC,OR,TTE,SAN,AIR,BNP,SU,KER", "latitude": 46.60, "longitude": 1.89, "commodities": "Wine,Aerospace,Luxury Goods,Pharmaceuticals,Wheat,Dairy,Nuclear Energy", "port_names": "Port of Marseille,Port of Le Havre,Port of Dunkerque"},
    {"code": "CH", "name": "Switzerland", "region": "Europe", "stock_exchange": "SIX Swiss", "currency": "CHF", "currency_symbol": "CHF", "market_cap": "$1.7T", "trading_hours": "09:00-17:30 CET", "tickers": "NOVN,ROG,NESN,UBSG,ABBN,CFR,ZURN", "latitude": 46.82, "longitude": 8.23, "commodities": "Gold,Pharmaceuticals,Financial Services,Machinery,Chocolate,Watches", "port_names": "Port of Basel (Rhine)"},
    {"code": "NL", "name": "Netherlands", "region": "Europe", "stock_exchange": "Euronext Amsterdam", "currency": "EUR", "currency_symbol": "€", "market_cap": "$900B", "tickers": "ASML,UNA,INGA,AD,KPN,AKZA,HEIA", "latitude": 52.13, "longitude": 5.29, "commodities": "Natural Gas,Chemicals,Electronics,Flowers,Dairy,Semiconductors", "port_names": "Port of Rotterdam,Port of Amsterdam"},
    {"code": "SE", "name": "Sweden", "region": "Europe", "stock_exchange": "OMX Nordic Stockholm", "currency": "SEK", "currency_symbol": "kr", "market_cap": "$820B", "tickers": "ERIC,SEB,VOLV,ABB,ATCO,SAND,SHB", "latitude": 60.13, "longitude": 18.64, "commodities": "Iron Ore,Timber,Steel,Machinery,Automobiles,Telecom", "port_names": "Port of Gothenburg,Port of Stockholm"},
    {"code": "DK", "name": "Denmark", "region": "Europe", "stock_exchange": "OMX Nordic Copenhagen", "currency": "DKK", "currency_symbol": "kr", "tickers": "NOVO,DSV,NZYM,MAERSK,CARL,VWS,GN", "latitude": 56.26, "longitude": 9.50, "commodities": "Pharmaceuticals,Wind Energy,Dairy,Pork,Furniture", "port_names": "Port of Copenhagen,Port of Aarhus"},
    {"code": "NO", "name": "Norway", "region": "Europe", "stock_exchange": "Oslo Børs", "currency": "NOK", "currency_symbol": "kr", "tickers": "EQUINOR,DNB,ORK,NHY,YAR,MOWI,SUBC", "latitude": 60.47, "longitude": 8.47, "commodities": "Oil,Natural Gas,Fish,Aluminum,Fertilizer,Timber", "port_names": "Port of Oslo,Port of Bergen"},
    {"code": "IT", "name": "Italy", "region": "Europe", "stock_exchange": "Borsa Italiana", "currency": "EUR", "currency_symbol": "€", "market_cap": "$700B", "tickers": "ENI,ISP,ENEL,UCG,LDO,PRY,RACE", "latitude": 41.87, "longitude": 12.57, "commodities": "Wine,Olive Oil,Fashion,Automobiles,Machinery,Steel,Fruit", "port_names": "Port of Genoa,Port of Trieste,Port of Naples"},
    {"code": "ES", "name": "Spain", "region": "Europe", "stock_exchange": "BME (Madrid)", "currency": "EUR", "currency_symbol": "€", "market_cap": "$650B", "tickers": "SAN,BBVA,TEF,IBE,REP,FER,AENA", "latitude": 40.46, "longitude": -3.75, "commodities": "Olive Oil,Wine,Fruit,Automobiles,Renewable Energy,Tourism", "port_names": "Port of Algeciras,Port of Barcelona,Port of Valencia"},
    {"code": "IE", "name": "Ireland", "region": "Europe", "stock_exchange": "Euronext Dublin", "currency": "EUR", "currency_symbol": "€", "tickers": "CRH,KER,RYAI,DCC", "latitude": 53.41, "longitude": -8.24, "commodities": "Pharmaceuticals,Dairy,Beef,Tech Services,Whiskey", "port_names": "Port of Dublin,Port of Cork"},
    {"code": "BE", "name": "Belgium", "region": "Europe", "stock_exchange": "Euronext Brussels", "currency": "EUR", "currency_symbol": "€", "tickers": "ABI,UCB,KBC,SOLB", "latitude": 50.85, "longitude": 4.35, "commodities": "Chemicals,Pharmaceuticals,Diamonds,Chocolate,Steel", "port_names": "Port of Antwerp,Port of Zeebrugge"},
    {"code": "PT", "name": "Portugal", "region": "Europe", "stock_exchange": "Euronext Lisbon", "currency": "EUR", "currency_symbol": "€", "tickers": "EDP,BCP,GALP,RENE", "latitude": 39.40, "longitude": -8.22, "commodities": "Wine,Cork,Olive Oil,Fish,Renewable Energy", "port_names": "Port of Lisbon,Port of Sines"},
    {"code": "AT", "name": "Austria", "region": "Europe", "stock_exchange": "Wiener Börse", "currency": "EUR", "currency_symbol": "€", "tickers": "EBS,OMV,RBI,VOE", "latitude": 47.52, "longitude": 14.55, "commodities": "Steel,Machinery,Timber,Chemicals,Tourism", "port_names": "Port of Vienna (Danube)"},
    {"code": "FI", "name": "Finland", "region": "Europe", "stock_exchange": "OMX Nordic Helsinki", "currency": "EUR", "currency_symbol": "€", "tickers": "NOKIA,NESTE,KNEBV,SAMPO", "latitude": 61.92, "longitude": 25.75, "commodities": "Timber,Paper,Tech,Steel,Chemicals", "port_names": "Port of Helsinki,Port of HaminaKotka"},
    {"code": "GR", "name": "Greece", "region": "Europe", "stock_exchange": "ATHEX", "currency": "EUR", "currency_symbol": "€", "market_cap": "$65B", "tickers": "ALPHA,EUROB,PPC,OPAP", "latitude": 39.07, "longitude": 21.82, "commodities": "Olive Oil,Shipping,Fruit,Wine,Tobacco", "port_names": "Port of Piraeus,Port of Thessaloniki"},
    {"code": "PL", "name": "Poland", "region": "Europe", "stock_exchange": "GPW (Warsaw)", "currency": "PLN", "currency_symbol": "zł", "market_cap": "$160B", "tickers": "PKN,PKOBP,PZU,CDR", "latitude": 51.92, "longitude": 19.15, "commodities": "Coal,Steel,Chemicals,Food Processing,Automotive Parts", "port_names": "Port of Gdansk,Port of Gdynia"},
    {"code": "RU", "name": "Russia", "region": "Europe", "stock_exchange": "MOEX", "currency": "RUB", "currency_symbol": "₽", "tickers": "SBER,GAZP,LKOH,ROSN", "latitude": 61.52, "longitude": 105.32, "commodities": "Oil,Natural Gas,Coal,Gold,Nickel,Diamonds,Wheat,Timber,Aluminum,Steel", "port_names": "Port of Novorossiysk,Port of Saint Petersburg,Port of Vladivostok"},
    {"code": "TR", "name": "Turkey", "region": "Europe", "stock_exchange": "BIST", "currency": "TRY", "currency_symbol": "₺", "market_cap": "$180B", "tickers": "THYAO,GARAN,KOCHOL,EREGL", "latitude": 38.96, "longitude": 35.24, "commodities": "Textiles,Automotive,Steel,Fruit,Ceramics,Chemicals", "port_names": "Port of Istanbul,Port of Izmir,Port of Mersin"},
    # Asia Pacific
    {"code": "JP", "name": "Japan", "region": "Asia Pacific", "stock_exchange": "TSE (Tokyo)", "currency": "JPY", "currency_symbol": "¥", "market_cap": "$6.7T", "trading_hours": "09:00-15:00 JST", "tickers": "TM,SONY,MUFG,SMFG,NTT,KDDI", "latitude": 36.20, "longitude": 138.25, "commodities": "Automobiles,Electronics,Steel,Chemicals,Semiconductors,Robotics", "port_names": "Port of Tokyo,Port of Yokohama,Port of Osaka,Port of Nagoya"},
    {"code": "CN", "name": "China", "region": "Asia Pacific", "stock_exchange": "SSE / HKEX", "currency": "CNY", "currency_symbol": "¥", "market_cap": "$8.2T", "trading_hours": "09:30-15:00 CST", "tickers": "BABA,TCEHY,JD,BIDU,NIO,PDD", "latitude": 35.86, "longitude": 104.19, "commodities": "Rare Earth,Steel,Electronics,Textiles,Coal,Solar Panels,Lithium,Rare Earth Minerals,Aluminum", "port_names": "Port of Shanghai,Port of Shenzhen,Port of Ningbo-Zhoushan,Port of Guangzhou,Port of Qingdao"},
    {"code": "HK", "name": "Hong Kong", "region": "Asia Pacific", "stock_exchange": "HKEX", "currency": "HKD", "currency_symbol": "HK$", "market_cap": "$4.1T", "tickers": "TCEHY,BABA,HSB,1299", "latitude": 22.32, "longitude": 114.17, "commodities": "Financial Services,Logistics,Electronics,Jewelry", "port_names": "Port of Hong Kong"},
    {"code": "KR", "name": "South Korea", "region": "Asia Pacific", "stock_exchange": "KRX", "currency": "KRW", "currency_symbol": "₩", "market_cap": "$1.8T", "trading_hours": "09:00-15:30 KST", "tickers": "SAMSUNG,HYMC,SKHY,POSCO,KB,KAKAO,NAVER", "latitude": 35.91, "longitude": 127.77, "commodities": "Semiconductors,Automobiles,Steel,Shipbuilding,Electronics,Petrochemicals", "port_names": "Port of Busan,Port of Incheon,Port of Ulsan"},
    {"code": "IN", "name": "India", "region": "Asia Pacific", "stock_exchange": "BSE / NSE", "currency": "INR", "currency_symbol": "₹", "market_cap": "$3.5T", "trading_hours": "09:15-15:30 IST", "tickers": "RELIANCE,TCS,INFY,HDFCBANK,ICICIBANK,SBIN,BHARTIARTL", "latitude": 20.59, "longitude": 78.96, "commodities": "Rice,Wheat,Cotton,Tea,Steel,Pharmaceuticals,IT Services,Diamonds", "port_names": "Port of Mumbai,Port of Chennai,Port of Mundra,Port of Kolkata"},
    {"code": "AU", "name": "Australia", "region": "Asia Pacific", "stock_exchange": "ASX", "currency": "AUD", "currency_symbol": "A$", "market_cap": "$1.8T", "trading_hours": "10:00-16:00 AEDT", "tickers": "BHP,CBA,CSL,NAB,WBC,ANZ,WOW,TLS,RIO", "latitude": -25.27, "longitude": 133.77, "commodities": "Iron Ore,Coal,Gold,LNG,Wheat,Beef,Wine,Lithium,Copper,Nickel", "port_names": "Port of Port Hedland,Port of Sydney,Port of Melbourne,Port of Brisbane"},
    {"code": "SG", "name": "Singapore", "region": "Asia Pacific", "stock_exchange": "SGX", "currency": "SGD", "currency_symbol": "S$", "market_cap": "$600B", "trading_hours": "09:00-17:00 SGT", "tickers": "DBS,OCBC,UOB,SBUX,WIL,KEP", "latitude": 1.35, "longitude": 103.82, "commodities": "Electronics,Chemicals,Pharmaceuticals,Financial Services,Oil Refining", "port_names": "Port of Singapore"},
    {"code": "TW", "name": "Taiwan", "region": "Asia Pacific", "stock_exchange": "TWSE", "currency": "TWD", "currency_symbol": "NT$", "market_cap": "$1.2T", "tickers": "TSMC,FOXCONN,MTK,HTC", "latitude": 23.70, "longitude": 120.96, "commodities": "Semiconductors,Electronics,Machinery,Steel,Petrochemicals", "port_names": "Port of Kaohsiung,Port of Taipei"},
    {"code": "MY", "name": "Malaysia", "region": "Asia Pacific", "stock_exchange": "Bursa Malaysia", "currency": "MYR", "currency_symbol": "RM", "market_cap": "$350B", "tickers": "MAYBANK,CIMB,PUBLIC,TENAGA", "latitude": 4.21, "longitude": 101.98, "commodities": "Palm Oil,Rubber,Oil,Natural Gas,Electronics,Timber", "port_names": "Port of Klang,Port of Tanjung Pelepas"},
    {"code": "ID", "name": "Indonesia", "region": "Asia Pacific", "stock_exchange": "IDX", "currency": "IDR", "currency_symbol": "Rp", "market_cap": "$500B", "tickers": "BBCA,BBRI,TLKM,ASII", "latitude": -0.79, "longitude": 113.92, "commodities": "Palm Oil,Coal,Nickel,Rubber,Coffee,Oil,Natural Gas,Tin", "port_names": "Port of Tanjung Priok,Port of Surabaya,Port of Belawan"},
    {"code": "TH", "name": "Thailand", "region": "Asia Pacific", "stock_exchange": "SET", "currency": "THB", "currency_symbol": "฿", "market_cap": "$450B", "tickers": "CPALL,PTT,AOT,ADVANC", "latitude": 15.87, "longitude": 100.99, "commodities": "Rice,Rubber,Electronics,Automotive,Sugar,Seafood,Tourism", "port_names": "Port of Bangkok,Port of Laem Chabang"},
    {"code": "PH", "name": "Philippines", "region": "Asia Pacific", "stock_exchange": "PSE", "currency": "PHP", "currency_symbol": "₱", "tickers": "SM,BDO,ALI,TEL", "latitude": 12.88, "longitude": 121.77, "commodities": "Electronics,Coconut Oil,Bananas,Nickel,Copper,Gold,BPO Services", "port_names": "Port of Manila,Port of Cebu"},
    {"code": "VN", "name": "Vietnam", "region": "Asia Pacific", "stock_exchange": "HOSE", "currency": "VND", "currency_symbol": "₫", "tickers": "VIC,VHM,TCB,HPG", "latitude": 14.06, "longitude": 108.28, "commodities": "Rice,Coffee,Textiles,Electronics,Seafood,Rubber", "port_names": "Port of Ho Chi Minh City,Port of Hai Phong,Port of Da Nang"},
    {"code": "NZ", "name": "New Zealand", "region": "Asia Pacific", "stock_exchange": "NZX", "currency": "NZD", "currency_symbol": "NZ$", "tickers": "FPH,A2M,ATM,SPK", "latitude": -40.90, "longitude": 174.89, "commodities": "Dairy,Meat,Wine,Wool,Timber,Fish,Fruit", "port_names": "Port of Auckland,Port of Tauranga"},
    {"code": "PK", "name": "Pakistan", "region": "Asia Pacific", "stock_exchange": "PSX", "currency": "PKR", "currency_symbol": "Rs", "market_cap": "$35B", "tickers": "OGDC,MCB,POL,ENGRO", "latitude": 30.38, "longitude": 69.35, "commodities": "Textiles,Rice,Wheat,Cotton,Sugar,Fruit,Leather", "port_names": "Port of Karachi,Port of Qasim,Gwadar Port"},
    # Middle East & Africa
    {"code": "AE", "name": "UAE", "region": "Middle East & Africa", "stock_exchange": "ADX / DFM", "currency": "AED", "currency_symbol": "د.إ", "market_cap": "$720B", "tickers": "ADNOC,EMAAR,DEWA,FAB", "latitude": 23.42, "longitude": 53.85, "commodities": "Oil,Natural Gas,Gold,Aluminum,Petrochemicals,Tourism,Logistics", "port_names": "Port of Jebel Ali,Port of Khalifa,Port of Zayed"},
    {"code": "SA", "name": "Saudi Arabia", "region": "Middle East & Africa", "stock_exchange": "Tadawul", "currency": "SAR", "currency_symbol": "﷼", "market_cap": "$2.7T", "tickers": "ARAMCO,SNB,ALRAJHI,STC,SABIC", "latitude": 23.89, "longitude": 45.08, "commodities": "Oil,Natural Gas,Petrochemicals,Gold,Fertilizer,Desalination", "port_names": "Port of Jeddah,King Abdulaziz Port (Dammam),Port of Jubail"},
    {"code": "QA", "name": "Qatar", "region": "Middle East & Africa", "stock_exchange": "QSE", "currency": "QAR", "currency_symbol": "﷼", "tickers": "QNB,QATAR,MASRAF", "latitude": 25.35, "longitude": 51.18, "commodities": "LNG,Oil,Petrochemicals,Fertilizer,Steel", "port_names": "Port of Hamad,Port of Doha"},
    {"code": "KW", "name": "Kuwait", "region": "Middle East & Africa", "stock_exchange": "Boursa Kuwait", "currency": "KWD", "currency_symbol": "د.ك", "tickers": "NBK,ZAIN,KFH", "latitude": 29.31, "longitude": 47.48, "commodities": "Oil,Natural Gas,Petrochemicals,Fertilizer", "port_names": "Port of Shuwaikh,Port of Shuaiba"},
    {"code": "IL", "name": "Israel", "region": "Middle East & Africa", "stock_exchange": "TASE", "currency": "ILS", "currency_symbol": "₪", "market_cap": "$260B", "tickers": "TEVA,NICE,WIX,CHKP", "latitude": 31.05, "longitude": 34.85, "commodities": "Diamonds,Pharmaceuticals,Tech,Citrus,Natural Gas,Chemicals", "port_names": "Port of Haifa,Port of Ashdod"},
    {"code": "ZA", "name": "South Africa", "region": "Middle East & Africa", "stock_exchange": "JSE", "currency": "ZAR", "currency_symbol": "R", "market_cap": "$900B", "trading_hours": "09:00-17:00 SAST", "tickers": "NASPERS,ANHEUSER,FIRSTRAND,STANDARD,MTN", "latitude": -30.56, "longitude": 22.94, "commodities": "Gold,Diamonds,Platinum,Coal,Iron Ore,Wine,Corn,Chromium", "port_names": "Port of Durban,Port of Cape Town,Port of Richards Bay"},
    {"code": "NG", "name": "Nigeria", "region": "Middle East & Africa", "stock_exchange": "NGX", "currency": "NGN", "currency_symbol": "₦", "tickers": "DANGOTE,MTNN,ZENITH,ACCESS", "latitude": 9.08, "longitude": 8.68, "commodities": "Oil,Natural Gas,Cocoa,Rubber,Gold,Cassava", "port_names": "Port of Lagos,Port of Port Harcourt"},
    {"code": "KE", "name": "Kenya", "region": "Middle East & Africa", "stock_exchange": "NSE", "currency": "KES", "currency_symbol": "KSh", "tickers": "SCOM,EABL,KCB", "latitude": -0.02, "longitude": 37.91, "commodities": "Tea,Coffee,Horticulture,Tourism,Flowers", "port_names": "Port of Mombasa"},
    {"code": "EG", "name": "Egypt", "region": "Middle East & Africa", "stock_exchange": "EGX", "currency": "EGP", "currency_symbol": "E£", "tickers": "COMI,EFG,HRHO,TMGH", "latitude": 26.82, "longitude": 30.80, "commodities": "Oil,Natural Gas,Cotton,Gold,Phosphates,Tourism", "port_names": "Port of Alexandria,Port of Damietta,Suez Canal"},
    {"code": "MA", "name": "Morocco", "region": "Middle East & Africa", "stock_exchange": "Casablanca SE", "currency": "MAD", "currency_symbol": "MAD", "tickers": "ATW,IAM,BCP,LQ", "latitude": 31.79, "longitude": -7.09, "commodities": "Phosphates,Fish,Olive Oil,Fruit,Automotive,Renewable Energy", "port_names": "Port of Casablanca,Port of Tangier"},
    {"code": "MU", "name": "Mauritius", "region": "Middle East & Africa", "stock_exchange": "SEM", "currency": "MUR", "currency_symbol": "Rs", "tickers": "MCB,SBM,NMH", "latitude": -20.35, "longitude": 57.55, "commodities": "Sugar,Textiles,Tourism,Financial Services", "port_names": "Port of Port Louis"},
    {"code": "IR", "name": "Iran", "region": "Middle East & Africa", "stock_exchange": "TSE", "currency": "IRR", "currency_symbol": "﷼", "tickers": "TSM,FARS,MOBILE", "latitude": 32.43, "longitude": 53.69, "commodities": "Oil,Natural Gas,Petrochemicals,Steel,Copper,Pistachios,Carpets", "port_names": "Port of Bandar Abbas,Port of Imam Khomeini"},
]

# ---------------------------------------------------------------------------
# Trade routes — from frontend/src/data/relations.ts
# ---------------------------------------------------------------------------

_coords = {
    k: v for k, v in [
        ("US", (37.09, -95.71)), ("CA", (56.13, -106.35)), ("BR", (-14.24, -51.93)),
        ("MX", (23.63, -102.55)), ("AR", (-38.42, -63.62)), ("CL", (-35.68, -71.54)),
        ("CO", (4.57, -74.30)), ("GB", (55.38, -3.44)), ("DE", (51.17, 10.45)),
        ("FR", (46.60, 1.89)), ("CH", (46.82, 8.23)), ("NL", (52.13, 5.29)),
        ("SE", (60.13, 18.64)), ("DK", (56.26, 9.50)), ("NO", (60.47, 8.47)),
        ("IT", (41.87, 12.57)), ("ES", (40.46, -3.75)), ("IE", (53.41, -8.24)),
        ("BE", (50.85, 4.35)), ("PT", (39.40, -8.22)), ("AT", (47.52, 14.55)),
        ("FI", (61.92, 25.75)), ("GR", (39.07, 21.82)), ("PL", (51.92, 19.15)),
        ("RU", (61.52, 105.32)), ("TR", (38.96, 35.24)), ("JP", (36.20, 138.25)),
        ("CN", (35.86, 104.19)), ("HK", (22.32, 114.17)), ("KR", (35.91, 127.77)),
        ("IN", (20.59, 78.96)), ("AU", (-25.27, 133.77)), ("SG", (1.35, 103.82)),
        ("TW", (23.70, 120.96)), ("MY", (4.21, 101.98)), ("ID", (-0.79, 113.92)),
        ("TH", (15.87, 100.99)), ("PH", (12.88, 121.77)), ("VN", (14.06, 108.28)),
        ("NZ", (-40.90, 174.89)), ("AE", (23.42, 53.85)), ("SA", (23.89, 45.08)),
        ("QA", (25.35, 51.18)), ("KW", (29.31, 47.48)), ("IL", (31.05, 34.85)),
        ("ZA", (-30.56, 22.94)), ("NG", (9.08, 8.68)), ("KE", (-0.02, 37.91)),
        ("EG", (26.82, 30.80)), ("MA", (31.79, -7.09)), ("MU", (-20.35, 57.55)),
        ("PK", (30.38, 69.35)), ("IR", (32.43, 53.69)),
    ]
}

trade_routes_data = [
    ("US", "CN", "$558B", "#00d4ff"), ("US", "MX", "$415B", "#00ff88"),
    ("US", "CA", "$382B", "#00d4ff"), ("US", "JP", "$208B", "#00d4ff"),
    ("US", "DE", "$190B", "#00d4ff"), ("US", "GB", "$260B", "#00ff88"),
    ("US", "KR", "$165B", "#00d4ff"), ("US", "IN", "$146B", "#00d4ff"),
    ("CN", "JP", "$348B", "#00ff88"), ("CN", "KR", "$312B", "#00ff88"),
    ("CN", "DE", "$245B", "#ffaa00"), ("CN", "AU", "$207B", "#ffaa00"),
    ("CN", "RU", "$190B", "#ffaa00"), ("CN", "BR", "$152B", "#ffaa00"),
    ("DE", "NL", "$195B", "#00d4ff"), ("DE", "FR", "$182B", "#00d4ff"),
    ("DE", "CN", "$245B", "#ffaa00"), ("JP", "KR", "$142B", "#00ff88"),
    ("JP", "AU", "$125B", "#00ff88"), ("GB", "US", "$260B", "#00ff88"),
    ("GB", "DE", "$155B", "#00d4ff"), ("GB", "NL", "$130B", "#00d4ff"),
    ("IN", "AE", "$105B", "#ffaa00"), ("IN", "US", "$146B", "#00d4ff"),
    ("RU", "DE", "$135B", "#ff4444"), ("RU", "CN", "$190B", "#ffaa00"),
    ("SA", "CN", "$120B", "#ffaa00"), ("SA", "US", "$85B", "#ffaa00"),
    ("BR", "CN", "$152B", "#ffaa00"), ("AU", "CN", "$207B", "#ffaa00"),
    ("AU", "JP", "$125B", "#00ff88"), ("KR", "CN", "$312B", "#00ff88"),
    ("KR", "US", "$165B", "#00d4ff"), ("SG", "CN", "$140B", "#ffaa00"),
    ("MY", "SG", "$95B", "#00ff88"), ("ID", "CN", "$110B", "#ffaa00"),
    ("AE", "IN", "$105B", "#ffaa00"), ("NG", "US", "$25B", "#ff4444"),
    ("ZA", "CN", "$75B", "#ffaa00"), ("TR", "DE", "$68B", "#ffaa00"),
]

# ---------------------------------------------------------------------------
# Military relations — from frontend/src/data/relations.ts
# ---------------------------------------------------------------------------

military_relations_data = [
    ("US", "GB", "alliance", "NATO - Five Eyes"),
    ("US", "CA", "alliance", "NATO - NORAD"),
    ("US", "DE", "alliance", "NATO Alliance"),
    ("US", "FR", "alliance", "NATO Alliance"),
    ("US", "JP", "alliance", "US-Japan Security Treaty"),
    ("US", "KR", "alliance", "US-ROK Mutual Defense"),
    ("US", "AU", "alliance", "ANZUS - AUKUS"),
    ("RU", "CN", "alliance", "Strategic Partnership"),
    ("RU", "IN", "alliance", "Defense Partnership"),
    ("CN", "PK", "alliance", "China-Pakistan Alliance"),
    ("US", "RU", "rivalry", "Geopolitical Rivalry"),
    ("US", "CN", "rivalry", "Strategic Competition"),
    ("IN", "CN", "rivalry", "Border Disputes"),
    ("IN", "PK", "conflict", "Kashmir Conflict"),
    ("IL", "IR", "conflict", "Regional Conflict"),
    ("RU", "GB", "rivalry", "Strategic Rivalry"),
    ("CN", "TW", "conflict", "Territorial Dispute"),
    ("KR", "JP", "neutral", "Historical Tensions"),
    ("SA", "IR", "rivalry", "Regional Proxy Conflict"),
    ("US", "IL", "alliance", "Strategic Ally"),
    ("RU", "TR", "neutral", "Competitive Cooperation"),
    ("FR", "DE", "alliance", "EU Core - Franco-German"),
    ("GB", "FR", "alliance", "NATO - Entente Cordiale"),
]

# ---------------------------------------------------------------------------
# Port locations — from frontend/src/data/relations.ts
# ---------------------------------------------------------------------------

ports_data = [
    ("US", "Los Angeles", 33.74, -118.27, "major"),
    ("US", "New York/New Jersey", 40.69, -74.04, "major"),
    ("US", "Houston", 29.75, -95.10, "major"),
    ("US", "Long Beach", 33.77, -118.22, "major"),
    ("US", "Savannah", 32.02, -81.15, "major"),
    ("CN", "Shanghai", 31.39, 121.50, "major"),
    ("CN", "Shenzhen", 22.50, 113.90, "major"),
    ("CN", "Ningbo-Zhoushan", 29.87, 122.20, "major"),
    ("CN", "Guangzhou", 23.10, 113.25, "major"),
    ("CN", "Qingdao", 36.06, 120.38, "major"),
    ("SG", "Singapore", 1.27, 103.84, "major"),
    ("KR", "Busan", 35.10, 129.04, "major"),
    ("KR", "Incheon", 37.45, 126.60, "major"),
    ("JP", "Tokyo", 35.65, 139.77, "major"),
    ("JP", "Yokohama", 35.44, 139.64, "major"),
    ("JP", "Osaka", 34.65, 135.43, "major"),
    ("JP", "Nagoya", 35.08, 136.88, "major"),
    ("NL", "Rotterdam", 51.91, 4.50, "major"),
    ("AE", "Jebel Ali", 25.01, 55.06, "major"),
    ("MY", "Port Klang", 3.00, 101.39, "major"),
    ("MY", "Tanjung Pelepas", 1.37, 103.56, "major"),
    ("AU", "Port Hedland", -20.31, 118.58, "major"),
    ("AU", "Sydney", -33.86, 151.21, "major"),
    ("AU", "Melbourne", -37.82, 144.97, "major"),
    ("IN", "Mumbai", 18.91, 72.83, "major"),
    ("IN", "Mundra", 22.84, 69.72, "major"),
    ("IN", "Chennai", 13.09, 80.29, "major"),
    ("GB", "Felixstowe", 51.95, 1.35, "major"),
    ("GB", "Southampton", 50.90, -1.40, "major"),
    ("DE", "Hamburg", 53.55, 9.97, "major"),
    ("DE", "Bremen", 53.08, 8.80, "major"),
    ("BR", "Santos", -23.97, -46.30, "major"),
    ("BR", "Rio de Janeiro", -22.90, -43.20, "major"),
    ("BE", "Antwerp", 51.25, 4.40, "major"),
    ("ES", "Algeciras", 36.13, -5.45, "major"),
    ("ES", "Barcelona", 41.33, 2.17, "major"),
    ("IT", "Genoa", 44.40, 8.92, "major"),
    ("FR", "Marseille", 43.33, 5.37, "major"),
    ("FR", "Le Havre", 49.49, 0.11, "major"),
    ("SA", "Jeddah", 21.49, 39.16, "major"),
    ("EG", "Alexandria", 31.20, 29.92, "major"),
    ("ZA", "Durban", -29.86, 31.03, "major"),
    ("ZA", "Cape Town", -33.91, 18.42, "major"),
    ("ID", "Tanjung Priok", -6.10, 106.88, "major"),
    ("TH", "Laem Chabang", 13.07, 100.88, "major"),
    ("VN", "Ho Chi Minh City", 10.77, 106.70, "major"),
    ("TW", "Kaohsiung", 22.62, 120.27, "major"),
    ("MX", "Manzanillo", 19.05, -104.32, "major"),
    ("CA", "Vancouver", 49.29, -123.12, "major"),
    ("CA", "Prince Rupert", 54.32, -130.33, "medium"),
    ("NG", "Lagos", 6.43, 3.40, "major"),
    ("QA", "Hamad", 24.78, 51.56, "major"),
    ("KW", "Shuwaikh", 29.35, 47.93, "major"),
    ("IL", "Haifa", 32.82, 34.99, "major"),
    ("IL", "Ashdod", 31.83, 34.64, "major"),
    ("KE", "Mombasa", -4.06, 39.66, "major"),
    ("HK", "Hong Kong", 22.35, 114.11, "major"),
    ("PH", "Manila", 14.58, 120.96, "major"),
    ("TR", "Istanbul", 41.00, 28.97, "major"),
    ("MA", "Tangier", 35.78, -5.81, "major"),
    ("EG", "Suez Canal", 30.50, 32.55, "major"),
    ("GR", "Piraeus", 37.94, 23.64, "major"),
    ("PL", "Gdansk", 54.35, 18.65, "major"),
    ("PT", "Sines", 37.96, -8.87, "medium"),
    ("FI", "Helsinki", 60.17, 24.95, "medium"),
    ("IE", "Dublin", 53.35, -6.20, "medium"),
    ("MU", "Port Louis", -20.16, 57.50, "medium"),
    ("NZ", "Auckland", -36.84, 174.76, "major"),
    ("NZ", "Tauranga", -37.65, 176.17, "medium"),
]


async def seed() -> None:
    async with AsyncSessionLocal() as session:
        # Check if already seeded
        existing = await session.execute(select(Country).limit(1))
        if existing.scalars().first():
            logger.warning("Countries table already has data — skipping seed.")
            return

        # Countries
        for d in countries_data:
            session.add(Country(**d))
        logger.info("Seeding %d countries ...", len(countries_data))

        # Trade routes
        for from_c, to_c, value, color in trade_routes_data:
            fl, fg = _coords[from_c]
            tl, tg = _coords[to_c]
            session.add(TradeRoute(
                from_country=from_c, to_country=to_c,
                value_label=value, color=color,
                from_lat=fl, from_lng=fg,
                to_lat=tl, to_lng=tg,
            ))
        logger.info("Seeding %d trade routes ...", len(trade_routes_data))

        # Military relations
        for a, b, rtype, label in military_relations_data:
            a_fl, a_fg = _coords[a]
            b_tl, b_tg = _coords[b]
            session.add(MilitaryRelation(
                country_a=a, country_b=b,
                relation_type=rtype, label=label,
                from_lat=a_fl, from_lng=a_fg,
                to_lat=b_tl, to_lng=b_tg,
            ))
        logger.info("Seeding %d military relations ...", len(military_relations_data))

        # Ports
        for code, name, lat, lng, volume in ports_data:
            session.add(Port(
                country_code=code, name=name,
                latitude=lat, longitude=lng, volume=volume,
            ))
        logger.info("Seeding %d ports ...", len(ports_data))

        await session.commit()
        logger.info("Seed complete.")


async def clear() -> None:
    """Drop all rows from the frontend-facing tables."""
    async with AsyncSessionLocal() as session:
        for model in (Port, MilitaryRelation, TradeRoute, Country):
            await session.execute(delete(model))
        await session.commit()
    logger.info("Cleared frontend data tables.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    asyncio.run(seed())
