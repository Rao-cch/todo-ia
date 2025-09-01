from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlmodel import SQLModel, Field, Session, create_engine, select
from pydantic import constr

# ---------- INICIALIZACIÓN ----------
app = FastAPI()

# Crear el motor de base de datos (archivo SQLite en la carpeta)
engine = create_engine("sqlite:///tasks.db")


# ---------- MODELOS ----------
class TaskBase(SQLModel):
    """
    Modelo base de tareas (entrada).
    - title: texto obligatorio entre 1 y 100 caracteres
    - done: estado de la tarea
    """
    title: constr(min_length=1, max_length=100)
    done: bool = False


class Task(TaskBase, table=True):
    """
    Modelo que representa la tabla en la base de datos.
    """
    id: int | None = Field(default=None, primary_key=True)


class TaskRead(TaskBase):
    """
    Modelo para mostrar datos en las respuestas.
    """
    id: int


# ---------- CREACIÓN DE TABLAS ----------
@app.on_event("startup")
def on_startup():
    """
    Este evento se ejecuta automáticamente al iniciar la aplicación.
    Aquí creamos todas las tablas definidas con SQLModel.
    """
    SQLModel.metadata.create_all(engine)


# ---------- ENDPOINTS BÁSICOS ----------
from fastapi.responses import FileResponse
import os

@app.get("/")
def serve_frontend():
    """
    Devuelve el archivo index.html al entrar en la URL raíz.
    """
    return FileResponse(os.path.join("static", "index.html"))


#@app.get("/favicon.ico", include_in_schema=False)
#async def favicon():
#    return FileResponse("favicon.ico")


# ---------- DEPENDENCIA DE SESIÓN ----------
def get_session():
    with Session(engine) as session:
        yield session


# ---------- CRUD DE TAREAS ----------
# Crear una nueva tarea (evitando duplicados)
@app.post("/tasks")
def create_task(task: Task, session: Session = Depends(get_session)):
    """
    Crea una nueva tarea y la guarda en la base de datos.
    Antes de crearla, se valida que no exista otra con el mismo título.
    """
    # Verificar si ya existe una tarea con el mismo título
    existing_task = session.exec(select(Task).where(Task.title == task.title)).first()
    if existing_task:
        raise HTTPException(status_code=400, detail="Ya existe una tarea con ese título")

    session.add(task)
    session.commit()
    session.refresh(task)
    return task



# Listar todas las tareas
@app.get("/tasks", response_model=list[TaskRead])
def read_tasks(session: Session = Depends(get_session)):
    """
    Obtiene todas las tareas guardadas en la base de datos.
    """
    tasks = session.exec(select(Task)).all()
    return tasks


# Actualizar una tarea
@app.put("/tasks/{task_id}", response_model=TaskRead)
def update_task(task_id: int, updated_task: TaskBase, session: Session = Depends(get_session)):
    """
    PUT = Actualizar datos existentes.
    Busca una tarea por su id y reemplaza sus valores.
    """
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")

    task.title = updated_task.title
    task.done = updated_task.done
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


# Eliminar una tarea
@app.delete("/tasks/{task_id}")
def delete_task(task_id: int, session: Session = Depends(get_session)):
    """
    DELETE = Eliminar un recurso existente.
    Busca una tarea por su id y la borra de la base de datos.
    """
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")

    session.delete(task)
    session.commit()
    return {"mensaje": f"Tarea con id {task_id} eliminada"}

# -------- MARCAR TAREA COMO COMPLETADA --------
@app.patch("/tasks/{task_id}/done", response_model=TaskRead)
def mark_task_done(task_id: int, session: Session = Depends(get_session)):
    """
    PATCH = Modificación parcial.
    Marca una tarea como completada (done=True).
    """
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")

    task.done = True
    session.add(task)
    session.commit()
    session.refresh(task)
    return task

# -------- CAMBIAR SOLO EL ESTADO DE UNA TAREA --------
@app.patch("/tasks/{task_id}/toggle", response_model=TaskRead)
def toggle_task(task_id: int, session: Session = Depends(get_session)):
    """
    PATCH = Actualizar parcialmente un recurso.
    Este endpoint cambia el estado de 'done' de una tarea:
    - Si estaba en False pasa a True.
    - Si estaba en True pasa a False.
    """
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")

    # Cambiar el estado (toggle)
    task.done = not task.done

    session.add(task)
    session.commit()
    session.refresh(task)
    return task

from fastapi.staticfiles import StaticFiles
import os

# -------- SERVIR FRONTEND --------
# Montamos una carpeta "static" para guardar archivos HTML, CSS y JS
app.mount("/static", StaticFiles(directory="static"), name="static")

# Servir el archivo index.html en la raíz "/"
@app.get("/")
def serve_frontend():
    """
    Devuelve el archivo index.html al entrar en la URL raíz.
    """
    return FileResponse(os.path.join("static", "index.html"))
