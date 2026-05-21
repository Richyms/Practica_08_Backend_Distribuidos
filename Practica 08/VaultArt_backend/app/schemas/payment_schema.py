from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional
    
class PaymentCreate(BaseModel):
    card_number: str = Field(..., min_length=15, max_length=19)
    card_name: str = Field(..., min_length=3)
    expiration_month: int = Field(..., ge=1, le=12)
    expiration_year: int
    cvv: str = Field(..., min_length=3, max_length=4)
    
    @field_validator('card_number')
    def validate_card_number(cls, v):
        v = v.replace(' ', '')
        if not v.isdigit():
            raise ValueError("El número de tarjeta no es válido.")
        
        def luhn_algorithm(card_num):
            total = 0
            reverse_digits = card_num[::-1]
            for i, digit in enumerate(reverse_digits):
                n = int(digit)
                if i%2 == 1:
                    n *= 2
                    if n > 9:
                        n -= 9
                total += n
            return total % 10 == 0
        
        if not luhn_algorithm(v):
            raise ValueError("El número de tarjeta no es válido.")
        
        return v
    
    @field_validator('expiration_year')
    def validate_expiration(cls, v, info):
        current_year = datetime.now().year
        current_month = datetime.now().month
        month = info.data.get('expiration_month', 1)
        
        if v < current_year or (v == current_year and month < current_month):
            raise ValueError("La tarjeta está vencida")
        return v
    
    @field_validator('cvv')
    def valdiate_cvv(cls, v):
        if not v.isdigit():
            raise ValueError("El cvv no es válido")
        return v

class SubscriptionCreate(BaseModel):
    payment_method: PaymentCreate
    accept_terms: bool
    
    @field_validator('accept_terms')
    def valdiate_terms(cls, v):
        if not v:
            raise ValueError("Debes aceptar los términos y condiciones")
        return v
    
class SecureSubscription(BaseModel):
    public_key_client: str
    data: dict
    salt: str
    
class PaymentRecord(BaseModel):
    payment_id: str = Field(alias="_id")
    user_id: str
    amount: float
    currency: str
    last_four: str
    status: str
    payment_id: str
    created_at: datetime
    expires_at: datetime
    
class SubscriptionResponse(BaseModel):
    is_active: bool
    end_date: Optional[datetime] = None
    message: str

    class Config:
        populate_by_name = True
        from_attributes = True