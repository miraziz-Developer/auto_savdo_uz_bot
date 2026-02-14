"""
FSM States for bot conversations — Enhanced
"""
from aiogram.fsm.state import State, StatesGroup


class RegistrationStates(StatesGroup):
    """User registration states"""
    waiting_for_phone = State()


class CarSearchStates(StatesGroup):
    """Car search and filtering states"""
    waiting_for_brand = State()
    waiting_for_model = State()
    waiting_for_year = State()
    waiting_for_price = State()


class SubscriptionStates(StatesGroup):
    """Subscription creation states"""
    waiting_for_brand = State()
    waiting_for_model = State()
    waiting_for_year_from = State()
    waiting_for_year_to = State()
    waiting_for_price_from = State()
    waiting_for_price_to = State()
    waiting_for_condition = State()
    confirm_subscription = State()


class SellCarStates(StatesGroup):
    """Sell car inquiry states"""
    waiting_for_brand = State()
    waiting_for_model = State()
    waiting_for_year = State()
    waiting_for_price = State()
    waiting_for_mileage = State()
    waiting_for_description = State()
    waiting_for_images = State()
    confirm_inquiry = State()


class AddCarStates(StatesGroup):
    """Admin: Add new car states"""
    waiting_for_brand = State()
    waiting_for_model = State()
    waiting_for_year = State()
    waiting_for_price = State()
    waiting_for_mileage = State()
    waiting_for_color = State()
    waiting_for_condition = State()
    waiting_for_transmission = State()
    waiting_for_fuel_type = State()
    waiting_for_description = State()
    waiting_for_images = State()
    waiting_for_expert_notes = State()
    confirm_car = State()


class RecordSaleStates(StatesGroup):
    """Admin: Record sale states"""
    waiting_for_brand = State()
    waiting_for_model = State()
    waiting_for_year = State()
    waiting_for_purchase_price = State()
    waiting_for_selling_price = State()
    waiting_for_buyer_phone = State()
    confirm_sale = State()


class BroadcastStates(StatesGroup):
    """Admin: Broadcast message states"""
    waiting_for_message = State()
    confirm_broadcast = State()


class AdminConvertStates(StatesGroup):
    """Admin: Convert inquiry to car"""
    waiting_for_price = State()
    waiting_for_confirmation = State()


# ====== NEW STATES ======

class BuyRequestStates(StatesGroup):
    """User: Buy request — moshina olmoqchiman"""
    waiting_for_brand = State()
    waiting_for_model = State()
    waiting_for_year = State()
    waiting_for_budget = State()
    waiting_for_transmission = State()
    waiting_for_fuel = State()
    waiting_for_color = State()
    waiting_for_mileage = State()
    waiting_for_notes = State()
    waiting_for_phone = State()
    confirm_request = State()


class PriceCheckStates(StatesGroup):
    """User: Price estimation — narxni baholash"""
    waiting_for_brand = State()
    waiting_for_model = State()
    waiting_for_year = State()
    waiting_for_transmission = State()
    waiting_for_mileage = State()


class PipelineStates(StatesGroup):
    """Admin: Pipeline management"""
    waiting_for_status = State()
    waiting_for_notes = State()


class ContactLogStates(StatesGroup):
    """Admin: Log contact with client"""
    waiting_for_type = State()
    waiting_for_notes = State()
    waiting_for_result = State()


class AdminNoteStates(StatesGroup):
    """Admin: Add note to user"""
    waiting_for_note = State()
