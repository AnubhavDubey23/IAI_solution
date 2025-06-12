from enum import Enum
from pydantic import BaseModel, constr
from typing import Optional, List, Dict
from datetime import date

class ReimbursementStatus(str, Enum):
    """Defines possible reimbursement statuses"""
    FULLY = "Fully Reimbursed"
    PARTIALLY = "Partially Reimbursed"
    DECLINED = "Declined"

class ExpenseCategory(str, Enum):
    """Defines expense categories"""
    FOOD = "Food"
    TRAVEL = "Travel"
    CAB = "Cab"
    ACCOMMODATION = "Accommodation"
    OTHER = "Other"

class AnalysisResult(BaseModel):
    """Result model for invoice analysis"""
    category: str
    status: ReimbursementStatus
    reimbursed_amount: float
    requested_amount: float
    reason: str
    policy_references: List[str]
    # category: ExpenseCategory

class InvoiceAnalysisRequest(BaseModel):
    """Request model for invoice analysis"""
    employee_name: constr(min_length=2, max_length=100)
    invoice_date: Optional[date] = None

class ChatRequest(BaseModel):
    """Request model for chatbot queries"""
    query: constr(min_length=3)
    history: List[Dict[str, str]] = []
    filters: Optional[Dict[str, str]] = None

class InvoiceResponse(BaseModel):
    """Response model for invoice analysis"""
    invoice_id: str
    status: ReimbursementStatus
    reimbursed_amount: float
    reason: str
    category: ExpenseCategory

class ChatResponse(BaseModel):
    """Response model for chatbot"""
    response: str
    context: List[Dict[str, str]]