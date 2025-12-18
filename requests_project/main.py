from fastapi import FastAPI, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from datetime import date
import qrcode
from fastapi.responses import FileResponse

from db import SessionLocal
from models import User, Role, Request, Comment, Part, RequestPart, RequestStatus
from schemas import (
    LoginSchema, RegisterSchema, UserOut,
    RequestOut, RequestCreate, RequestUpdate,
    CommentCreate, PartsUpdate, ExtendDeadline, StatsOut
)

app = FastAPI(title="Учет заявок на ремонт")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def role_name_by_id(db: Session, role_id: int) -> str:
    r = db.query(Role).filter(Role.id == role_id).first()
    return r.name if r else "client"

def status_id_by_name(db: Session, name: str) -> int:
    st = db.query(RequestStatus).filter(RequestStatus.name == name).first()
    if not st:
        raise HTTPException(400, detail=f"Неизвестный статус: {name}")
    return st.id

def next_user_id(db: Session) -> int:
    max_id = db.query(func.max(User.id)).scalar()
    return (max_id or 0) + 1

def next_request_id(db: Session) -> int:
    max_id = db.query(func.max(Request.id)).scalar()
    return (max_id or 0) + 1

def get_current_user(
    db: Session = Depends(get_db),
    x_user_id: int | None = Header(default=None, alias="X-User-Id")
) -> User:
    if not x_user_id:
        raise HTTPException(401, detail="Нет X-User-Id (пользователь не авторизован)")
    user = db.query(User).filter(User.id == x_user_id).first()
    if not user:
        raise HTTPException(401, detail="Пользователь не найден")
    return user

def require_roles(db: Session, user: User, allowed: set[str]):
    rn = role_name_by_id(db, user.role_id)
    if rn not in allowed:
        raise HTTPException(403, detail=f"Нет доступа. Ваша роль: {rn}")


@app.post("/register")
def register(data: RegisterSchema, db: Session = Depends(get_db)):
    if db.query(User).filter(User.login == data.login).first():
        raise HTTPException(400, detail="Логин уже занят")

    role = db.query(Role).filter(Role.name == "client").first()
    if not role:
        raise HTTPException(500, detail="Нет роли client в БД")

    u = User(
        id=next_user_id(db),
        fio=data.fio,
        phone=data.phone,
        login=data.login,
        password=data.password,  
        role_id=role.id
    )
    db.add(u)
    db.commit()
    return {"message": "Регистрация успешна"}

@app.post("/login", response_model=UserOut)
def login(data: LoginSchema, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.login == data.login, User.password == data.password).first()
    if not user:
        raise HTTPException(401, detail="Неверный логин или пароль")
    return UserOut(
        id=user.id,
        fio=user.fio,
        phone=user.phone,
        role=role_name_by_id(db, user.role_id)
    )


def request_to_out(db: Session, r: Request) -> RequestOut:
    client = db.query(User).filter(User.id == r.client_id).first()
    master = db.query(User).filter(User.id == r.master_id).first() if r.master_id else None
    status = db.query(RequestStatus).filter(RequestStatus.id == r.status_id).first()
    return RequestOut(
        id=r.id,
        start_date=r.start_date,
        climate_tech_type=r.climate_tech_type,
        climate_tech_model=r.climate_tech_model,
        problem_description=r.problem_description,
        status=status.name if status else "open",
        client_fio=client.fio if client else "—",
        client_phone=client.phone if client else None,
        master_fio=master.fio if master else None,
        completion_date=r.completion_date,
        extended_due_date=r.extended_due_date
    )

@app.get("/requests", response_model=list[RequestOut])
def list_requests(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rn = role_name_by_id(db, user.role_id)
    q = db.query(Request)
    if rn == "client":
        q = q.filter(Request.client_id == user.id)
    rows = q.order_by(Request.id.asc()).all()
    return [request_to_out(db, r) for r in rows]

@app.get("/requests/search", response_model=list[RequestOut])
def search_requests(q: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rn = role_name_by_id(db, user.role_id)
    base = db.query(Request).filter(
        (Request.climate_tech_type.ilike(f"%{q}%")) |
        (Request.climate_tech_model.ilike(f"%{q}%")) |
        (Request.problem_description.ilike(f"%{q}%")) |
        (text("CAST(id AS TEXT) ILIKE :qq")).bindparams(qq=f"%{q}%")
    )
    if rn == "client":
        base = base.filter(Request.client_id == user.id)
    rows = base.order_by(Request.id.asc()).all()
    return [request_to_out(db, r) for r in rows]

@app.post("/requests")
def create_request(data: RequestCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    
    rn = role_name_by_id(db, user.role_id)
    if rn not in {"client", "operator", "admin"}:
        raise HTTPException(403, detail="Создавать заявки может клиент или оператор")

    st_id = status_id_by_name(db, "open")  
    r = Request(
        id=next_request_id(db),
        start_date=date.today(),
        climate_tech_type=data.climate_tech_type,
        climate_tech_model=data.climate_tech_model,
        problem_description=data.problem_description,
        status_id=st_id,
        client_id=user.id if rn == "client" else user.id,  
        master_id=None,
        completion_date=None
    )
    db.add(r)
    db.commit()
    return {"message": "Заявка создана", "request_id": r.id}

@app.put("/requests/{request_id}")
def update_request(request_id: int, data: RequestUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    
    rn = role_name_by_id(db, user.role_id)

    r = db.query(Request).filter(Request.id == request_id).first()
    if not r:
        raise HTTPException(404, detail="Заявка не найдена")

    
    if rn == "client":
        if r.client_id != user.id:
            raise HTTPException(403, detail="Это не ваша заявка")
        if data.problem_description is None or data.status is not None or data.master_id is not None:
            raise HTTPException(403, detail="Клиент может менять только описание проблемы")
        r.problem_description = data.problem_description
        db.commit()
        return {"message": "Описание обновлено"}

    
    if rn not in {"operator", "manager", "admin"}:
        raise HTTPException(403, detail="Редактировать заявки может оператор или менеджер")

    if data.problem_description is not None:
        r.problem_description = data.problem_description

    if data.master_id is not None:
        
        r.master_id = data.master_id

    if data.status is not None:
        r.status_id = status_id_by_name(db, data.status)
        
        if data.status == "done" and not r.completion_date:
            r.completion_date = date.today()

    if data.completion_date is not None:
        r.completion_date = data.completion_date

    db.commit()
    return {"message": "Заявка обновлена"}


@app.post("/comments")
def add_comment(data: CommentCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rn = role_name_by_id(db, user.role_id)
    if rn not in {"specialist", "operator", "manager", "admin"}:
        raise HTTPException(403, detail="Комментарий может оставить специалист/сотрудник")

    r = db.query(Request).filter(Request.id == data.request_id).first()
    if not r:
        raise HTTPException(404, detail="Заявка не найдена")

    
    if rn == "specialist" and r.master_id != user.id:
        raise HTTPException(403, detail="Вы не назначены на эту заявку")

    c = Comment(request_id=data.request_id, user_id=user.id, message=data.message)
    db.add(c)
    db.commit()
    return {"message": "Комментарий добавлен"}

@app.post("/requests/parts")
def set_parts(data: PartsUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rn = role_name_by_id(db, user.role_id)
    if rn not in {"specialist", "operator", "manager", "admin"}:
        raise HTTPException(403, detail="Запчасти может фиксировать специалист/сотрудник")

    r = db.query(Request).filter(Request.id == data.request_id).first()
    if not r:
        raise HTTPException(404, detail="Заявка не найдена")

    if rn == "specialist" and r.master_id != user.id:
        raise HTTPException(403, detail="Вы не назначены на эту заявку")

    
    db.query(RequestPart).filter(RequestPart.request_id == data.request_id).delete()

    parts = [p.strip() for p in data.parts_csv.split(",") if p.strip()]
    for p in parts:
        part = db.query(Part).filter(Part.name == p).first()
        if not part:
            part = Part(name=p)
            db.add(part)
            db.flush()  
        db.add(RequestPart(request_id=data.request_id, part_id=part.id))

    db.commit()
    return {"message": "Запчасти сохранены"}


@app.put("/requests/extend")
def extend_deadline(data: ExtendDeadline, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_roles(db, user, {"manager", "admin"})

    r = db.query(Request).filter(Request.id == data.request_id).first()
    if not r:
        raise HTTPException(404, detail="Заявка не найдена")

    r.extended_due_date = data.new_date
    db.commit()
    return {"message": "Срок продлен"}


@app.get("/stats", response_model=StatsOut)
def stats(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_roles(db, user, {"operator", "manager", "admin"})

    done_id = status_id_by_name(db, "done")
    done_count = db.query(func.count(Request.id)).filter(Request.status_id == done_id).scalar() or 0

    
    avg_days = db.execute(text("""
        SELECT COALESCE(AVG((completion_date - start_date)), 0)
        FROM requests
        WHERE completion_date IS NOT NULL
    """)).scalar() or 0.0

    by_equipment = db.execute(text("""
        SELECT climate_tech_type AS k, COUNT(*) AS c
        FROM requests
        GROUP BY climate_tech_type
        ORDER BY c DESC
        LIMIT 10
    """)).mappings().all()

    
    by_problem = db.execute(text("""
        SELECT split_part(problem_description, ' ', 1) AS k, COUNT(*) AS c
        FROM requests
        GROUP BY k
        ORDER BY c DESC
        LIMIT 10
    """)).mappings().all()

    return StatsOut(
        done_count=int(done_count),
        avg_days=float(avg_days),
        by_equipment_type=[{"name": r["k"], "count": int(r["c"])} for r in by_equipment],
        by_problem_keywords=[{"keyword": r["k"], "count": int(r["c"])} for r in by_problem],
    )


@app.get("/feedback/qr")
def get_qr():
    img = qrcode.make(
        "https://docs.google.com/forms/d/e/1FAIpQLSdhZcExx6LSIXxk0ub55mSu-WIh23WYdGG9HY5EZhLDo7P8eA/viewform?usp=sf_link"
    )
    img.save("qr.png")
    return FileResponse("qr.png")
