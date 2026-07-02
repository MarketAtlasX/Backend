from .event_schema import HistoricalEvent, MarketOutcome

# ruff: noqa: E501

HISTORICAL_EVENTS = [
    HistoricalEvent(
        id="yom-kippur-1973",
        name="Yom Kippur War (1973)",
        description="On October 6, 1973, a coalition of Arab states led by Egypt and Syria launched a surprise attack on Israel on Yom Kippur. The US initiated a major airlift of military supplies to Israel, while the Soviet Union supported Arab states. OPEC declared an oil embargo against nations supporting Israel, leading to the 1973 oil crisis. Global oil prices quadrupled, causing economic turmoil worldwide.",
        date="1973-10-06",
        event_type="conflict",
        entities=["Israel", "Egypt", "Syria", "United States", "Soviet Union", "OPEC", "Arab League"],
        sectors=["Energy", "Defense", "Transportation", "Manufacturing"],
        outcomes=[
            MarketOutcome(sector="Energy", impact_pct=400.0, volatility=85.0, recovery_days=365),
            MarketOutcome(sector="Defense", impact_pct=15.0, volatility=30.0, recovery_days=120),
            MarketOutcome(sector="Transportation", impact_pct=-12.0, volatility=45.0, recovery_days=180),
            MarketOutcome(sector="Manufacturing", impact_pct=-8.0, volatility=35.0, recovery_days=200),
        ],
        volatility=85.0, recovery_days=365,
        summary="Oil prices quadrupled, defense stocks surged, global recession ensued."
    ),
    HistoricalEvent(
        id="iranian-revolution-1979",
        name="Iranian Revolution (1979)",
        description="The Iranian Revolution resulted in the overthrow of the US-backed Shah and establishment of an Islamic republic under Ayatollah Khomeini. Iran's oil production collapsed from 6 million barrels per day to under 1.5 million. Global oil prices surged from $13 to $40 per barrel. The US embassy hostage crisis further escalated tensions.",
        date="1979-01-16", event_type="political",
        entities=["Iran", "United States", "Shah Pahlavi", "Ayatollah Khomeini", "OPEC", "Middle East"],
        sectors=["Energy", "Defense", "Financials"],
        outcomes=[
            MarketOutcome(sector="Energy", impact_pct=200.0, volatility=75.0, recovery_days=300),
            MarketOutcome(sector="Defense", impact_pct=10.0, volatility=25.0, recovery_days=90),
            MarketOutcome(sector="Financials", impact_pct=-5.0, volatility=40.0, recovery_days=150),
        ],
        volatility=75.0, recovery_days=300,
        summary="Oil prices tripled, defense stocks rose, global uncertainty spiked."
    ),
    HistoricalEvent(
        id="gulf-war-1990",
        name="Iraq Invasion of Kuwait / Gulf War (1990)",
        description="On August 2, 1990, Iraq under Saddam Hussein invaded and annexed Kuwait. The invasion triggered immediate UN sanctions and a US-led coalition of 35 nations. Iraq set fire to over 700 Kuwaiti oil wells as they retreated. Oil prices doubled from $15 to $40 per barrel.",
        date="1990-08-02", event_type="conflict",
        entities=["Iraq", "Kuwait", "United States", "Saddam Hussein", "UN", "Saudi Arabia"],
        sectors=["Energy", "Defense", "Airlines", "Insurance"],
        outcomes=[
            MarketOutcome(sector="Energy", impact_pct=100.0, volatility=60.0, recovery_days=180),
            MarketOutcome(sector="Defense", impact_pct=20.0, volatility=25.0, recovery_days=60),
            MarketOutcome(sector="Airlines", impact_pct=-15.0, volatility=40.0, recovery_days=120),
            MarketOutcome(sector="Insurance", impact_pct=10.0, volatility=30.0, recovery_days=90),
        ],
        volatility=60.0, recovery_days=180,
        summary="Oil prices doubled, defense stocks surged, markets recovered quickly after coalition victory."
    ),
    HistoricalEvent(
        id="9-11-2001",
        name="September 11 Attacks (2001)",
        description="On September 11, 2001, al-Qaeda terrorists hijacked four commercial airplanes and attacked the World Trade Center in New York and the Pentagon in Washington, D.C. The attacks killed nearly 3,000 people and triggered the War on Terror. Global markets plunged, the S&P 500 lost 14% in the following week. The US launched invasions of Afghanistan and later Iraq.",
        date="2001-09-11", event_type="terrorist_attack",
        entities=["United States", "Al-Qaeda", "Osama Bin Laden", "New York", "Washington DC", "NATO", "Afghanistan"],
        sectors=["Airlines", "Insurance", "Defense", "Travel & Hospitality", "Financials"],
        outcomes=[
            MarketOutcome(sector="Airlines", impact_pct=-40.0, volatility=70.0, recovery_days=365),
            MarketOutcome(sector="Insurance", impact_pct=25.0, volatility=50.0, recovery_days=180),
            MarketOutcome(sector="Defense", impact_pct=35.0, volatility=30.0, recovery_days=365),
            MarketOutcome(sector="Travel & Hospitality", impact_pct=-25.0, volatility=55.0, recovery_days=270),
            MarketOutcome(sector="Financials", impact_pct=-14.0, volatility=60.0, recovery_days=90),
        ],
        volatility=70.0, recovery_days=365,
        summary="S&P 500 lost 14% in a week, airlines devastated, defense and insurance stocks surged."
    ),
    HistoricalEvent(
        id="2008-financial-crisis",
        name="Global Financial Crisis (2008)",
        description="The 2008 financial crisis was triggered by the collapse of the US housing bubble and the failure of Lehman Brothers. The crisis spread globally through interconnected financial systems, causing a severe recession. Major banks were bailed out by governments worldwide. The S&P 500 fell 57% from peak to trough. Central banks implemented unprecedented monetary stimulus.",
        date="2008-09-15", event_type="financial_crisis",
        entities=["United States", "Lehman Brothers", "Federal Reserve", "European Union", "China"],
        sectors=["Financials", "Real Estate", "Manufacturing", "Technology"],
        outcomes=[
            MarketOutcome(sector="Financials", impact_pct=-55.0, volatility=80.0, recovery_days=1095),
            MarketOutcome(sector="Real Estate", impact_pct=-40.0, volatility=60.0, recovery_days=730),
            MarketOutcome(sector="Manufacturing", impact_pct=-25.0, volatility=50.0, recovery_days=545),
            MarketOutcome(sector="Technology", impact_pct=-35.0, volatility=55.0, recovery_days=730),
        ],
        volatility=80.0, recovery_days=1095,
        summary="S&P 500 fell 57%, financial stocks collapsed, global recession lasted 18 months."
    ),
    HistoricalEvent(
        id="russia-ukraine-2022",
        name="Russia-Ukraine War (2022)",
        description="On February 24, 2022, Russia launched a full-scale invasion of Ukraine. The conflict triggered unprecedented Western sanctions against Russia, including SWIFT disconnection and asset freezes. Global energy prices surged as Russia is a major oil and gas exporter. Natural gas prices in Europe reached record highs. Food prices spiked due to Ukraine being a major grain exporter.",
        date="2022-02-24", event_type="conflict",
        entities=["Russia", "Ukraine", "United States", "NATO", "European Union", "China"],
        sectors=["Energy", "Defense", "Agriculture", "Manufacturing", "Transportation"],
        outcomes=[
            MarketOutcome(sector="Energy", impact_pct=80.0, volatility=65.0, recovery_days=540),
            MarketOutcome(sector="Defense", impact_pct=30.0, volatility=25.0, recovery_days=365),
            MarketOutcome(sector="Agriculture", impact_pct=35.0, volatility=45.0, recovery_days=365),
            MarketOutcome(sector="Manufacturing", impact_pct=-15.0, volatility=40.0, recovery_days=270),
            MarketOutcome(sector="Transportation", impact_pct=-10.0, volatility=35.0, recovery_days=180),
        ],
        volatility=65.0, recovery_days=540,
        summary="Energy prices surged 80%, defense stocks rallied, global food crisis ensued."
    ),
    HistoricalEvent(
        id="red-sea-2023",
        name="Red Sea Shipping Crisis (2023-2024)",
        description="Houthi rebels in Yemen began attacking commercial shipping vessels in the Red Sea in late 2023, forcing major shipping companies to reroute around the Cape of Good Hope. This added 10-14 days to shipping times and significantly increased costs. Global trade routes were disrupted, affecting supply chains worldwide.",
        date="2023-11-19", event_type="disruption",
        entities=["Yemen", "Houthis", "Israel", "Egypt", "Iran", "Suez Canal", "Red Sea"],
        sectors=["Shipping", "Energy", "Manufacturing", "Insurance"],
        outcomes=[
            MarketOutcome(sector="Shipping", impact_pct=25.0, volatility=50.0, recovery_days=360),
            MarketOutcome(sector="Energy", impact_pct=15.0, volatility=35.0, recovery_days=270),
            MarketOutcome(sector="Manufacturing", impact_pct=-5.0, volatility=25.0, recovery_days=180),
            MarketOutcome(sector="Insurance", impact_pct=20.0, volatility=30.0, recovery_days=270),
        ],
        volatility=50.0, recovery_days=360,
        summary="Shipping costs spiked 250%, supply chains disrupted, energy prices rose."
    ),
    HistoricalEvent(
        id="covid-19-2020",
        name="COVID-19 Pandemic (2020)",
        description="The COVID-19 pandemic caused the most severe global economic crisis since the Great Depression. Global lockdowns brought economic activity to a near standstill. The S&P 500 fell 34% in a month. Oil prices briefly turned negative. Governments and central banks implemented unprecedented fiscal and monetary stimulus totaling over $10 trillion.",
        date="2020-03-11", event_type="pandemic",
        entities=["China", "United States", "European Union", "WHO", "World Bank"],
        sectors=["Travel & Hospitality", "Airlines", "Energy", "Technology", "Healthcare", "Retail"],
        outcomes=[
            MarketOutcome(sector="Travel & Hospitality", impact_pct=-60.0, volatility=75.0, recovery_days=545),
            MarketOutcome(sector="Airlines", impact_pct=-55.0, volatility=70.0, recovery_days=545),
            MarketOutcome(sector="Energy", impact_pct=-50.0, volatility=80.0, recovery_days=365),
            MarketOutcome(sector="Technology", impact_pct=40.0, volatility=45.0, recovery_days=180),
            MarketOutcome(sector="Healthcare", impact_pct=25.0, volatility=35.0, recovery_days=180),
            MarketOutcome(sector="Retail", impact_pct=-20.0, volatility=40.0, recovery_days=270),
        ],
        volatility=80.0, recovery_days=545,
        summary="S&P 500 fell 34%, oil went negative, tech stocks soared on work-from-home trend."
    ),
    HistoricalEvent(
        id="china-taiwan-2022",
        name="China-Taiwan Tensions (2022-2024)",
        description="Following US House Speaker Nancy Pelosi's visit to Taiwan in August 2022, China conducted unprecedented large-scale military exercises around Taiwan. China intensified economic coercion and military posturing. The semiconductor supply chain faced severe disruption risks, given Taiwan's dominance in advanced chip manufacturing.",
        date="2022-08-02", event_type=" geopolitical_tension",
        entities=["China", "Taiwan", "United States", "TSMC", "Semiconductor Industry"],
        sectors=["Technology", "Semiconductors", "Defense", "Manufacturing"],
        outcomes=[
            MarketOutcome(sector="Semiconductors", impact_pct=-10.0, volatility=55.0, recovery_days=180),
            MarketOutcome(sector="Technology", impact_pct=-8.0, volatility=40.0, recovery_days=120),
            MarketOutcome(sector="Defense", impact_pct=15.0, volatility=20.0, recovery_days=90),
            MarketOutcome(sector="Manufacturing", impact_pct=-5.0, volatility=30.0, recovery_days=120),
        ],
        volatility=55.0, recovery_days=180,
        summary="Semiconductor stocks fell, defense stocks rose, supply chain fears emerged."
    ),
    HistoricalEvent(
        id="north-korea-2017",
        name="North Korea Nuclear Crisis (2017)",
        description="North Korea conducted multiple intercontinental ballistic missile tests and its sixth and most powerful nuclear test in September 2017. The US and allies imposed strict sanctions. President Trump threatened 'fire and fury.' Global markets experienced heightened volatility with safe-haven flows into gold and bonds.",
        date="2017-09-03", event_type="geopolitical_tension",
        entities=["North Korea", "United States", "South Korea", "Japan", "China", "UN"],
        sectors=["Defense", "Energy", "Financials"],
        outcomes=[
            MarketOutcome(sector="Defense", impact_pct=8.0, volatility=20.0, recovery_days=60),
            MarketOutcome(sector="Energy", impact_pct=5.0, volatility=20.0, recovery_days=45),
            MarketOutcome(sector="Financials", impact_pct=-3.0, volatility=25.0, recovery_days=30),
        ],
        volatility=25.0, recovery_days=60,
        summary="Safe-haven demand surged, defense stocks rose, volatility spiked briefly."
    ),
    HistoricalEvent(
        id="us-china-trade-war",
        name="US-China Trade War (2018-2020)",
        description="The US under President Trump imposed tariffs on hundreds of billions of dollars of Chinese goods, triggering retaliatory tariffs from China. The trade war disrupted global supply chains, particularly in technology and manufacturing. The S&P 500 experienced multiple corrections. A Phase 1 deal was signed in January 2020 but many tariffs remained.",
        date="2018-07-06", event_type="trade_policy",
        entities=["United States", "China", "European Union", "WTO", "Trump Administration"],
        sectors=["Manufacturing", "Technology", "Agriculture", "Semiconductors"],
        outcomes=[
            MarketOutcome(sector="Manufacturing", impact_pct=-12.0, volatility=35.0, recovery_days=365),
            MarketOutcome(sector="Technology", impact_pct=-15.0, volatility=40.0, recovery_days=270),
            MarketOutcome(sector="Agriculture", impact_pct=-20.0, volatility=30.0, recovery_days=545),
            MarketOutcome(sector="Semiconductors", impact_pct=-18.0, volatility=45.0, recovery_days=365),
        ],
        volatility=40.0, recovery_days=545,
        summary="Supply chains disrupted, manufacturing and tech stocks fell, farmers received bailouts."
    ),
    HistoricalEvent(
        id="brexit-2016",
        name="Brexit Referendum (2016)",
        description="On June 23, 2016, the United Kingdom voted to leave the European Union in a shock referendum result. Global markets plunged, with the FTSE 100 initially falling 8% before recovering rapidly. The British pound fell to its lowest level in 31 years. Political uncertainty dominated European markets for years.",
        date="2016-06-23", event_type="political",
        entities=["United Kingdom", "European Union", "London", "Scotland", "Northern Ireland"],
        sectors=["Financials", "Real Estate", "Manufacturing", "Travel & Hospitality"],
        outcomes=[
            MarketOutcome(sector="Financials", impact_pct=-20.0, volatility=50.0, recovery_days=365),
            MarketOutcome(sector="Real Estate", impact_pct=-10.0, volatility=30.0, recovery_days=545),
            MarketOutcome(sector="Manufacturing", impact_pct=-5.0, volatility=25.0, recovery_days=365),
            MarketOutcome(sector="Travel & Hospitality", impact_pct=-8.0, volatility=20.0, recovery_days=180),
        ],
        volatility=50.0, recovery_days=545,
        summary="Pound crashed, London property market stalled, financial services faced uncertainty."
    ),
]


def seed_events() -> list[HistoricalEvent]:
    return HISTORICAL_EVENTS
