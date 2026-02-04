from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel


class SubscriptionRead(SQLModel):
    id: int
    status: str
    start_date: datetime
    next_payment_date: Optional[datetime]
    end_date: Optional[datetime]
    amount: float
    currency: str
    frequency: int
    frequency_type: str
    mp_subscription_id: str
    mp_plan_id: Optional[str]
