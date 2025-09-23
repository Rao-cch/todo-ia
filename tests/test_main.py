# tests/test_main.py
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))


from fastapi.testclient import TestClient
from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy.pool import StaticPool
from main import app, get_session  # Importamos desde tu main.py

# ---------- CONFIGURACIÓN DE LA BD DE PRUEBAS ----------
# Usamos StaticPool para que la BD en memoria se mantenga entre requests
TEST_SQLITE_URL = "sqlite://"
test_engine = create_engine(
    TEST_SQLITE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)

# Crear tablas en la BD de pruebas
def setup_module():
    SQLModel.metadata.create_all(test_engine)

# Sobrescribir dependencia get_session para usar test_engine
def override_get_session():
    with Session(test_engine) as session:
        yield session

app.dependency_overrides[get_session] = override_get_session

# Cliente de pruebas para simular llamadas HTTP
client = TestClient(app)


# ---------- TESTS ----------

def test_create_task_success():
    res = client.post("/tasks", json={"title": "Comprar leche", "done": False})
    assert res.status_code == 200
    data = res.json()
    assert data["title"] == "Comprar leche"
    assert "id" in data

def test_create_duplicate_fails():
    client.post("/tasks", json={"title": "Duplicado", "done": False})
    res = client.post("/tasks", json={"title": "Duplicado", "done": False})
    assert res.status_code == 400

def test_read_tasks():
    client.post("/tasks", json={"title": "Leer", "done": False})
    res = client.get("/tasks")
    assert res.status_code == 200
    assert isinstance(res.json(), list)

def test_update_task():
    res = client.post("/tasks", json={"title": "Editar", "done": False})
    tid = res.json()["id"]
    res2 = client.put(f"/tasks/{tid}", json={"title": "Editada", "done": True})
    assert res2.status_code == 200
    assert res2.json()["title"] == "Editada"
    assert res2.json()["done"] == True

def test_toggle_and_delete_task():
    res = client.post("/tasks", json={"title": "ToggleDel", "done": False})
    tid = res.json()["id"]

    # toggle
    res2 = client.patch(f"/tasks/{tid}/toggle")
    assert res2.status_code == 200
    assert res2.json()["done"] in (True, False)

    # delete
    res3 = client.delete(f"/tasks/{tid}")
    assert res3.status_code == 200
