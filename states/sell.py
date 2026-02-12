"""
States for selling cars
"""
from aiogram.fsm.state import State, StatesGroup


class CarSellStates(StatesGroup):
    choosing_method = State()
    
    # Common details for both methods
    waiting_brand = State()
    waiting_model = State()
    waiting_year = State()
    waiting_mileage = State()
    waiting_engine = State()
    waiting_gearbox = State()
    waiting_fuel = State()
    waiting_color = State()
    waiting_description = State()
    waiting_price = State()
    waiting_photos = State()
    waiting_phone = State()
    
    # Normal Ad (10,000 UZS)
    waiting_ad_payment = State()
