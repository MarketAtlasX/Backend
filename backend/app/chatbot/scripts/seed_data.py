"""Seed sample geopolitical events into the database for demo purposes."""

import asyncio
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

SAMPLE_EVENTS = [
    {
        "source": "Reuters",
        "title": "US Imposes New Sanctions on Russian Energy Sector",
        "description": "The United States announced a new round of sanctions targeting Russian oil and gas exports, targeting major energy companies and restricting access to Western insurance and shipping services.",
        "content": "The Biden administration unveiled sweeping new sanctions against Russia's energy sector, targeting companies involved in oil and gas production, liquefied natural gas exports, and related infrastructure. The measures include restrictions on insurance and shipping services that could significantly impact Russia's ability to export crude oil. Market analysts expect disruptions to global energy supply chains, with potential price increases for crude oil and natural gas. European Union officials indicated they would align with the new sanctions regime.",
    },
    {
        "source": "Bloomberg",
        "title": "Oil Prices Surge as Middle East Tensions Escalate",
        "description": "Brent crude soared past $90 per barrel following increased military activity in the Strait of Hormuz, raising concerns about supply disruptions through the strategic waterway.",
        "content": "Oil prices rallied sharply as geopolitical tensions in the Middle East reached a critical point. The Strait of Hormuz, through which approximately 20% of global oil passes, saw increased naval presence from multiple nations. The escalation follows a series of incidents involving commercial shipping vessels. Analysts warn that a sustained disruption could push oil prices above $100 per barrel. Energy stocks rallied on the news, with the XLE energy sector ETF gaining 3.2% in early trading. Safe-haven assets including gold and US Treasuries also saw increased demand.",
    },
    {
        "source": "FT",
        "title": "EU Accelerates Energy Transition Amid Supply Concerns",
        "description": "European Union leaders agree to fast-track renewable energy projects and reduce dependence on Russian natural gas imports following supply disruptions.",
        "content": "In an emergency summit, European Union leaders committed to accelerating the bloc's energy transition, approving streamlined permits for wind and solar projects across member states. The decision comes as natural gas storage levels remain below seasonal averages following reduced flows from Russia. The EU also announced a joint purchasing mechanism for LNG cargoes to reduce price volatility. Renewable energy stocks rose on the news, while utilities with significant gas exposure faced selling pressure.",
    },
    {
        "source": "Reuters",
        "title": "China Manufacturing PMI Contracts for Third Consecutive Month",
        "description": "China's manufacturing activity contracted for the third straight month in March, with the official PMI falling to 49.1, indicating ongoing weakness in the world's second-largest economy.",
        "content": "China's manufacturing sector continued to struggle as the official Purchasing Managers' Index (PMI) fell to 49.1, below the 50 threshold separating growth from contraction. The data adds to concerns about global economic growth prospects. Export orders declined sharply, reflecting weak external demand. Industrial metal prices retreated on the news, with copper and iron ore leading the decline. The Chinese government signaled potential additional stimulus measures to support the struggling property sector and boost domestic consumption.",
    },
    {
        "source": "Bloomberg",
        "title": "NATO Announces Increased Defense Spending Targets",
        "description": "NATO members agree to raise defense spending targets to 3% of GDP, marking the largest collective increase in European defense since the Cold War era.",
        "content": "NATO allies committed to significantly higher defense spending targets, with member nations agreeing to allocate at least 3% of GDP to defense budgets. The decision represents a major shift in European defense posture and is expected to benefit defense contractors across the alliance. Lockheed Martin, Rheinmetall, and BAE Systems are among the key beneficiaries. The announcement also triggered discussions about defense industrial base expansion and ammunition stockpile replenishment. European defense stocks surged 4-8% on the news.",
    },
    {
        "source": "Reuters",
        "title": "Iran Sanctions Tightened Following Nuclear Enrichment Concerns",
        "description": "The US and European allies impose additional sanctions on Iran's oil exports and banking sector in response to accelerated uranium enrichment activities.",
        "content": "Western nations announced a coordinated expansion of sanctions targeting Iran's economy, focusing on oil exports and the financial sector. The measures aim to restrict Iran's ability to sell crude oil to Asian markets and access international banking systems. Iran's oil exports had been running at approximately 1.5 million barrels per day, mostly to China. The sanctions are expected to reduce this by 300,000-500,000 barrels per day, potentially tightening global oil markets. Shipping and insurance companies face secondary sanctions risks for facilitating Iranian oil trade.",
    },
    {
        "source": "FT",
        "title": "Global Shipping Reroutes as Red Sea Security Deteriorates",
        "description": "Major shipping lines announce extended rerouting around the Cape of Good Hope as attacks on commercial vessels in the Red Sea continue to disrupt trade routes.",
        "content": "The ongoing security situation in the Red Sea has forced major container shipping lines to maintain longer routes around Africa's Cape of Good Hope, adding 10-14 days to transit times between Asia and Europe. Shipping costs have more than doubled since the disruptions began, with spot rates for Asia-Europe routes reaching levels not seen since the pandemic. The extended routes are straining global container capacity and causing delays in European retail supply chains. Insurance premiums for Red Sea transits have increased tenfold. Analysts expect the disruptions to persist.",
    },
    {
        "source": "Bloomberg",
        "title": "AI Chip Export Controls Reshape Global Tech Supply Chains",
        "description": "New US export controls on advanced AI semiconductors are forcing a fundamental restructuring of global technology supply chains, impacting NVIDIA, TSMC, and their customers worldwide.",
        "content": "The Biden administration's expanded export controls on advanced AI semiconductors are reshaping the global technology landscape. The measures restrict the sale of NVIDIA's H100 and B200 chips to certain countries, while requiring licenses for exports to a broader set of nations. TSMC, the world's largest semiconductor foundry, is navigating compliance requirements while expanding manufacturing in the US, Japan, and Germany. China's AI development faces significant headwinds as access to cutting-edge hardware becomes restricted. Semiconductor stocks have experienced increased volatility as investors assess the impact on global tech supply chains.",
    },
    {
        "source": "Reuters",
        "title": "OPEC+ Considers Extended Production Cuts Amid Demand Uncertainty",
        "description": "OPEC+ members are discussing extending voluntary production cuts through the end of the year as global oil demand growth shows signs of slowing.",
        "content": "OPEC+ delegates indicated that the group is considering extending current voluntary production cuts of 2.2 million barrels per day beyond the second quarter. The decision reflects growing uncertainty about global oil demand growth, particularly from China, where economic recovery has been uneven. Saudi Arabia, the de facto leader of OPEC+, has signaled its preference for maintaining market tightness to support prices above $80 per barrel for Brent crude. Non-OPEC production growth, particularly from US shale and Guyana, continues to pressure the group's market share. Oil analysts are divided on whether the cuts will be sufficient to balance the market.",
    },
    {
        "source": "Bloomberg",
        "title": "India Emerges as Key Beneficiary of Supply Chain Diversification",
        "description": "India attracts record foreign direct investment as multinational corporations diversify supply chains away from China, positioning the country as a major manufacturing alternative.",
        "content": "India has emerged as a primary beneficiary of the global supply chain diversification trend, attracting record FDI inflows in electronics manufacturing, pharmaceuticals, and renewable energy. Apple suppliers including Foxconn and Wistron have expanded operations in the country, while Tesla has announced plans to establish a manufacturing facility. India's electronics exports have more than doubled in two years. The government's production-linked incentive schemes have been instrumental in attracting investment. However, infrastructure bottlenecks and regulatory complexities remain challenges. The Indian equity market has outperformed emerging market peers.",
    },
]


async def seed_database():
    from app.database import AsyncSessionLocal
    from app.models.raw_event import RawEvent

    async with AsyncSessionLocal() as session:
        from sqlalchemy import func, select
        result = await session.execute(select(func.count()).select_from(RawEvent))
        count = result.scalar()
        if count and count > 0:
            logger.info(f"Database already has {count} events, skipping seed.")
            print(f"Database already has {count} events, skipping seed.")
            return

        for data in SAMPLE_EVENTS:
            event = RawEvent(
                source=data["source"],
                title=data["title"],
                description=data.get("description", ""),
                content=data.get("content", ""),
                fetched_at=datetime.now(timezone.utc),
            )
            session.add(event)

        await session.commit()
        print(f"Seeded {len(SAMPLE_EVENTS)} sample geopolitical events.")
        logger.info(f"Seeded {len(SAMPLE_EVENTS)} sample geopolitical events.")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, ".")
    logging.basicConfig(level=logging.INFO)
    asyncio.run(seed_database())
