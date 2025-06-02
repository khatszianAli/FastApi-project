from sqlalchemy import create_engine, Column, Integer, String, Date, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from fastapi import FastAPI, HTTPException, Depends, Header, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date
import enum
import sys

app = FastAPI()

DATABASE_URL = "sqlite:///./test.db"
AUTH_TOKEN = "task1234"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class StatusEnum(str, enum.Enum):
    new = "new"
    in_progress = "in_progress"
    done = "done"


class TaskModel(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    due_date = Column(Date, nullable=True)
    status = Column(Enum(StatusEnum, native_enum=False), default=StatusEnum.new)


Base.metadata.create_all(bind=engine)


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    due_date: Optional[date] = None
    status: StatusEnum = StatusEnum.new


class TaskOut(TaskCreate):
    id: int


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def verify_token(token: str = Header(...)):
    if token != AUTH_TOKEN:
        raise HTTPException(status_code=403, detail="Unauthorized")


@app.post("/tasks/", response_model=TaskOut)
def create_task(task: TaskCreate, db: Session = Depends(get_db), _: str = Depends(verify_token)):
    db_task = TaskModel(**task.dict())
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

@app.get("/")
def read_root():
    return {"message": "API is working!"}


@app.get("/tasks/", response_model=List[TaskOut])
def list_tasks(
        status: Optional[StatusEnum] = Query(None),
        due_date: Optional[date] = Query(None),
        db: Session = Depends(get_db),
        _: str = Depends(verify_token)
):
    query = db.query(TaskModel)
    if status:
        query = query.filter(TaskModel.status == status)
    if due_date:
        query = query.filter(TaskModel.due_date == due_date)
    return query.all()


@app.get("/tasks/{task_id}", response_model=TaskOut)
def get_task(task_id: int, db: Session = Depends(get_db), _: str = Depends(verify_token)):
    task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.put("/tasks/{task_id}", response_model=TaskOut)
def update_task(task_id: int, task: TaskCreate, db: Session = Depends(get_db), _: str = Depends(verify_token)):
    db_task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    for key, value in task.dict().items():
        setattr(db_task, key, value)
    db.commit()
    db.refresh(db_task)
    return db_task


@app.delete("/tasks/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db), _: str = Depends(verify_token)):
    task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(task)
    db.commit()
    return JSONResponse(content={"detail": "Task deleted successfully"})