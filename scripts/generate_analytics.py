"""
Script to generate analytics reports manually
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from analytics.sales_analytics import SalesAnalytics
from loguru import logger


async def generate_reports():
    """Generate all analytics reports"""
    logger.info("Generating analytics reports...")
    
    analytics = SalesAnalytics()
    
    # Generate full report
    report = await analytics.generate_full_report()
    
    # Get summary stats
    stats = await analytics.get_summary_stats()
    
    print("\n" + "="*50)
    print("📊 SOTUVLAR ANALITIKASI")
    print("="*50)
    print(f"\n📈 Jami sotuvlar (30 kun): {stats['total_sales']} ta")
    print(f"💰 Jami foyda: {stats['total_profit']:,.0f} so'm")
    print(f"📊 O'rtacha foyda: {stats['avg_profit']:,.0f} so'm")
    print(f"🏆 Eng yaxshi kun: {stats.get('best_day', 'N/A')} ({stats.get('best_day_count', 0)} ta)")
    
    print("\n📁 Grafiklar saqlandi:")
    if report['daily_sales']:
        print(f"  - Kunlik sotuvlar: {report['daily_sales']}")
    if report['top_models']:
        print(f"  - Top modellar: {report['top_models']}")
    
    print(f"\n⏰ Yaratildi: {report['generated_at']}")
    print("="*50 + "\n")


if __name__ == "__main__":
    asyncio.run(generate_reports())
