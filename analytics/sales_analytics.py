"""
Sales analytics using pandas and matplotlib
"""
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
from typing import List
from pathlib import Path
from loguru import logger

from database.database import async_session_maker
from database.crud import get_sold_cars_last_30_days, get_top_sold_models


# Set matplotlib to use a non-GUI backend
plt.switch_backend('Agg')

# Configure matplotlib for better appearance
plt.style.use('seaborn-v0_8-darkgrid')
plt.rcParams['figure.figsize'] = (12, 6)
plt.rcParams['font.size'] = 10
plt.rcParams['axes.titlesize'] = 14
plt.rcParams['axes.labelsize'] = 12


class SalesAnalytics:
    """Sales analytics and visualization"""
    
    def __init__(self, output_dir: str = "analytics/reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    async def generate_daily_sales_chart(self) -> str:
        """
        Generate daily sales dynamics chart for last 30 days
        
        Returns:
            Path to saved chart image
        """
        try:
            # Get sold cars data
            async with async_session_maker() as session:
                sold_cars = await get_sold_cars_last_30_days(session)
            
            if not sold_cars:
                logger.warning("No sold cars data for analytics")
                return None
            
            # Convert to DataFrame
            df = pd.DataFrame([
                {
                    'date': car.sold_at.date(),
                    'brand': car.brand,
                    'model': car.model,
                    'profit': car.profit,
                    'selling_price': car.selling_price
                }
                for car in sold_cars
            ])
            
            # Group by date
            daily_stats = df.groupby('date').agg({
                'profit': 'sum',
                'selling_price': 'count'  # Count as number of sales
            }).reset_index()
            
            daily_stats.columns = ['date', 'total_profit', 'sales_count']
            
            # Create figure with two subplots
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
            
            # Plot 1: Daily sales count
            ax1.plot(daily_stats['date'], daily_stats['sales_count'], 
                    marker='o', linewidth=2, markersize=8, color='#2E86AB')
            ax1.fill_between(daily_stats['date'], daily_stats['sales_count'], 
                            alpha=0.3, color='#2E86AB')
            ax1.set_title('📊 Kunlik sotuvlar soni (30 kun)', fontsize=16, fontweight='bold')
            ax1.set_xlabel('Sana')
            ax1.set_ylabel('Sotuvlar soni')
            ax1.grid(True, alpha=0.3)
            ax1.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))
            plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
            
            # Plot 2: Daily profit
            ax2.plot(daily_stats['date'], daily_stats['total_profit'] / 1_000_000, 
                    marker='s', linewidth=2, markersize=8, color='#06A77D')
            ax2.fill_between(daily_stats['date'], daily_stats['total_profit'] / 1_000_000, 
                            alpha=0.3, color='#06A77D')
            ax2.set_title('💰 Kunlik foyda (30 kun)', fontsize=16, fontweight='bold')
            ax2.set_xlabel('Sana')
            ax2.set_ylabel('Foyda (mln so\'m)')
            ax2.grid(True, alpha=0.3)
            ax2.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))
            plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)
            
            plt.tight_layout()
            
            # Save chart
            filename = self.output_dir / f"daily_sales_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            plt.savefig(filename, dpi=300, bbox_inches='tight')
            plt.close()
            
            logger.info(f"Daily sales chart saved to {filename}")
            return str(filename)
            
        except Exception as e:
            logger.error(f"Error generating daily sales chart: {e}")
            return None
    
    async def generate_top_models_chart(self, top_n: int = 10) -> str:
        """
        Generate top sold models chart
        
        Args:
            top_n: Number of top models to show
            
        Returns:
            Path to saved chart image
        """
        try:
            # Get top models data
            async with async_session_maker() as session:
                top_models = await get_top_sold_models(session, limit=top_n)
            
            if not top_models:
                logger.warning("No top models data for analytics")
                return None
            
            # Convert to DataFrame
            df = pd.DataFrame(top_models)
            
            # Create figure with two subplots
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
            
            # Plot 1: Sales count by model
            colors1 = plt.cm.viridis(range(len(df)))
            bars1 = ax1.barh(df['model'], df['count'], color=colors1)
            ax1.set_title('🚗 Eng ko\'p sotilgan modellar', fontsize=16, fontweight='bold')
            ax1.set_xlabel('Sotuvlar soni')
            ax1.set_ylabel('Model')
            
            # Add value labels on bars
            for bar in bars1:
                width = bar.get_width()
                ax1.text(width, bar.get_y() + bar.get_height()/2, 
                        f'{int(width)}', ha='left', va='center', fontsize=10, fontweight='bold')
            
            # Plot 2: Total profit by model
            colors2 = plt.cm.plasma(range(len(df)))
            bars2 = ax2.barh(df['model'], df['total_profit'] / 1_000_000, color=colors2)
            ax2.set_title('💵 Model bo\'yicha umumiy foyda', fontsize=16, fontweight='bold')
            ax2.set_xlabel('Umumiy foyda (mln so\'m)')
            ax2.set_ylabel('Model')
            
            # Add value labels on bars
            for bar in bars2:
                width = bar.get_width()
                ax2.text(width, bar.get_y() + bar.get_height()/2, 
                        f'{width:.1f}M', ha='left', va='center', fontsize=10, fontweight='bold')
            
            plt.tight_layout()
            
            # Save chart
            filename = self.output_dir / f"top_models_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            plt.savefig(filename, dpi=300, bbox_inches='tight')
            plt.close()
            
            logger.info(f"Top models chart saved to {filename}")
            return str(filename)
            
        except Exception as e:
            logger.error(f"Error generating top models chart: {e}")
            return None
    
    async def generate_full_report(self) -> dict:
        """
        Generate full analytics report with all charts
        
        Returns:
            Dictionary with chart paths
        """
        daily_chart = await self.generate_daily_sales_chart()
        models_chart = await self.generate_top_models_chart()
        
        return {
            'daily_sales': daily_chart,
            'top_models': models_chart,
            'generated_at': datetime.now().isoformat()
        }
    
    async def get_summary_stats(self) -> dict:
        """
        Get summary statistics
        
        Returns:
            Dictionary with summary stats
        """
        try:
            async with async_session_maker() as session:
                sold_cars = await get_sold_cars_last_30_days(session)
            
            # Additional Stats for "Savdo statistikasi" block
            if not sold_cars:
                return {
                    'total_sales': 0,
                    'total_profit': 0,
                    'avg_profit': 0,
                    'best_day': None,
                    'best_model': 'N/A',
                    'best_model_profit': 0
                }
            
            df = pd.DataFrame([
                {'date': car.sold_at.date(), 'profit': c.profit, 'model': c.model}
                for c in sold_cars
            ])
            
            total_sales = len(sold_cars)
            total_profit = df['profit'].sum()
            avg_profit = df['profit'].mean()
            
            # Best day
            daily_sales = df.groupby('date').size()
            best_day = daily_sales.idxmax() if not daily_sales.empty else None
            
            # Best model by profit
            model_profit = df.groupby('model')['profit'].sum()
            best_model = model_profit.idxmax() if not model_profit.empty else 'N/A'
            best_model_val = model_profit.max() if not model_profit.empty else 0
            
            return {
                'total_sales': total_sales,
                'total_profit': float(total_profit),
                'avg_profit': float(avg_profit),
                'best_day': str(best_day) if best_day else None,
                'best_day_count': int(daily_sales.max()) if not daily_sales.empty else 0,
                'best_model': best_model,
                'best_model_profit': float(best_model_val)
            }
            
        except Exception as e:
            logger.error(f"Error getting summary stats: {e}")
            return {}

    async def get_customer_stats(self) -> dict:
        """
        Get customer statistics (Total, Active, New)
        """
        from database.crud import get_users_count, get_active_users_count, get_new_users_count
        async with async_session_maker() as session:
            total = await get_users_count(session)
            active = await get_active_users_count(session, days=7)
            new = await get_new_users_count(session, days=7)
            
        return {'total': total, 'active': active, 'new': new}

    async def get_popular_cars(self, limit: int = 3) -> List[dict]:
        """
        Get most viewed cars
        """
        from database.crud import get_most_viewed_cars
        async with async_session_maker() as session:
            cars = await get_most_viewed_cars(session, limit=limit)
        
        return [
            {'brand': c.brand, 'model': c.model, 'views': c.views_count} 
            for c in cars
        ]

    async def get_price_analysis(self) -> dict:
        """
        Price analysis of current inventory
        """
        from database.crud import get_price_stats
        async with async_session_maker() as session:
            stats = await get_price_stats(session)
            
        return stats # {avg, max, min, max_car_model, min_car_model}

    async def generate_weekly_excel_report(self) -> str:
        """
        Generate comprehensive Excel report
        """
        filename = self.output_dir / f"weekly_report_{datetime.now().strftime('%Y%m%d')}.xlsx"
        
        async with async_session_maker() as session:
            sold_cars = await get_sold_cars_last_30_days(session)
            
        # Create multiple dataframes for sheets
        df_sales = pd.DataFrame([
            {
                'ID': c.id, 'Brand': c.brand, 'Model': c.model, 'Year': c.year,
                'Buy Price': c.purchase_price, 'Sell Price': c.selling_price, 'Profit': c.profit,
                'Date': c.sold_at
            } for c in sold_cars
        ])
        
        try:
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                if not df_sales.empty:
                    df_sales.to_excel(writer, sheet_name='Sales', index=False)
                # Add more sheets if needed...
            return str(filename)
        except Exception as e:
            logger.error(f"Excel export error: {e}")
            return None
