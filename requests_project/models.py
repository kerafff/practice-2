from sqlalchemy import Column, Integer, Text, Date, DateTime, ForeignKey, func
from db import Base

class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True)
    name = Column(Text, unique=True)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)  
    fio = Column(Text, nullable=False)
    phone = Column(Text)
    login = Column(Text, unique=True, nullable=False)
    password = Column(Text, nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)

class Request(Base):
    __tablename__ = "requests"
    id = Column(Integer, primary_key=True)
    start_date = Column(Date, nullable=False)
    climate_tech_type = Column(Text, nullable=False)
    climate_tech_model = Column(Text, nullable=False)
    problem_description = Column(Text, nullable=False)

    status_id = Column(Integer, ForeignKey("request_statuses.id"), nullable=False)

    client_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    master_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    completion_date = Column(Date, nullable=True)
    due_date = Column(Date, nullable=True)
    extended_due_date = Column(Date, nullable=True)

class RequestStatus(Base):
    __tablename__ = "request_statuses"
    id = Column(Integer, primary_key=True)
    name = Column(Text, unique=True, nullable=False)

class Comment(Base):
    __tablename__ = "comments"
    id = Column(Integer, primary_key=True)
    request_id = Column(Integer, ForeignKey("requests.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

class Part(Base):
    __tablename__ = "parts"
    id = Column(Integer, primary_key=True)
    name = Column(Text, unique=True, nullable=False)

class RequestPart(Base):
    __tablename__ = "request_parts"
    request_id = Column(Integer, ForeignKey("requests.id", ondelete="CASCADE"), primary_key=True)
    part_id = Column(Integer, ForeignKey("parts.id"), primary_key=True)
