from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlmodel import SQLModel, Field, Session, create_engine, select
from pydantic import constr
import os
import re

# ---------- INICIALIZACIÓN ----------
app = FastAPI()

# Base de datos
engine = create_engine("sqlite:///tasks.db", connect_args={"check_same_thread": False})


# ---------- MODELOS ----------
class TaskBase(SQLModel):
    title: constr(min_length=1, max_length=100)
    done: bool = False


class Task(TaskBase, table=True):
    id: int | None = Field(default=None, primary_key=True)


class TaskRead(TaskBase):
    id: int


# ---------- CREACIÓN DE TABLAS ----------
@app.on_event("startup")
def on_startup():
    SQLModel.metadata.create_all(engine)


# ---------- DEPENDENCIA DE SESIÓN ----------
def get_session():
    with Session(engine) as session:
        yield session


# ---------- CRUD DE TAREAS ----------
@app.post("/tasks", response_model=TaskRead)
def create_task(task: Task, session: Session = Depends(get_session)):
    # Validar título
    if not re.match(r"^[A-Za-zÁÉÍÓÚáéíóúÑñ\s]+$", task.title):
        raise HTTPException(status_code=400, detail="El título solo puede contener letras y espacios")

    # Verificar duplicados
    existing = session.exec(select(Task).where(Task.title == task.title)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Task already exists")

    session.add(task)
    session.commit()
    session.refresh(task)
    return task


@app.get("/tasks", response_model=list[TaskRead])
def read_tasks(session: Session = Depends(get_session)):
    return session.exec(select(Task)).all()


@app.put("/tasks/{task_id}", response_model=TaskRead)
def update_task(task_id: int, updated_task: TaskBase, session: Session = Depends(get_session)):
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if not re.match(r"^[A-Za-zÁÉÍÓÚáéíóúÑñ\s]+$", updated_task.title):
        raise HTTPException(status_code=400, detail="El título solo puede contener letras y espacios")

    task.title = updated_task.title
    task.done = updated_task.done
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


@app.delete("/tasks/{task_id}")
def delete_task(task_id: int, session: Session = Depends(get_session)):
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    session.delete(task)
    session.commit()
    return {"ok": True}


@app.patch("/tasks/{task_id}/toggle", response_model=TaskRead)
def toggle_task(task_id: int, session: Session = Depends(get_session)):
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.done = not task.done
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


# ---------- FRONTEND ----------
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def serve_frontend():
    return FileResponse(os.path.join("static", "index.html"))
