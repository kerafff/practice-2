from pydantic import BaseModel
from datetime import date
from typing import Optional, List

class LoginSchema(BaseModel):
    login: str
    password: str

class RegisterSchema(BaseModel):
    fio: str
    phone: str
    login: str
    password: str

class UserOut(BaseModel):
    id: int
    fio: str
    phone: str | None
    role: str

class RequestOut(BaseModel):
    id: int
    start_date: date
    climate_tech_type: str
    climate_tech_model: str
    problem_description: str
    status: str
    client_fio: str
    client_phone: str | None
    master_fio: str | None
    completion_date: date | None
    extended_due_date: date | None

class RequestCreate(BaseModel):
    climate_tech_type: str
    climate_tech_model: str
    problem_description: str

class RequestUpdate(BaseModel):
    
    status: Optional[str] = None  
    problem_description: Optional[str] = None
    master_id: Optional[int] = None
    completion_date: Optional[date] = None

class CommentCreate(BaseModel):
    request_id: int
    message: str

class PartsUpdate(BaseModel):
    request_id: int
    parts_csv: str  

class ExtendDeadline(BaseModel):
    request_id: int
    new_date: date

class StatsOut(BaseModel):
    done_count: int
    avg_days: float
    by_equipment_type: List[dict]
    by_problem_keywords: List[dict]
