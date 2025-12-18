from sqlalchemy.orm import Session
from models import User

def authenticate(db: Session, login: str, password: str):
    return db.query(User).filter(
        User.login == login,
        User.password == password
    ).first()
