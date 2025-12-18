import pandas as pd
from sqlalchemy import create_engine, text

DB_URL = "postgresql://postgres:123@localhost:5432/requests_db"

engine = create_engine(DB_URL)

users_df = pd.read_excel("inputDataUsers.xlsx")
requests_df = pd.read_excel("inputDataRequests.xlsx")
comments_df = pd.read_excel("inputDataComments.xlsx")

ROLE_MAP = {
    "Оператор": "operator",
    "Специалист": "specialist",
    "Менеджер": "manager",
    "Заказчик": "client"
}

STATUS_MAP = {
    "Новая заявка": "open",
    "В процессе ремонта": "in_progress",
    "Ожидание комплектующих": "waiting_parts",
    "Завершена": "done"
}

with engine.begin() as conn:
    # пользователи
    for _, row in users_df.iterrows():
        role_name = ROLE_MAP.get(row["type"], "client")
        role_id = conn.execute(
            text("SELECT id FROM roles WHERE name=:n"),
            {"n": role_name}
        ).scalar()

        conn.execute(text("""
            INSERT INTO users (id, fio, phone, login, password, role_id)
            VALUES (:id, :fio, :phone, :login, :password, :role_id)
            ON CONFLICT (id) DO NOTHING
        """), {
            "id": int(row["userID"]),
            "fio": row["fio"],
            "phone": str(row["phone"]),
            "login": row["login"],
            "password": row["password"],
            "role_id": role_id
        })

    # заявки
    for _, row in requests_df.iterrows():
        status_name = STATUS_MAP.get(row["requestStatus"], "open")
        status_id = conn.execute(
            text("SELECT id FROM request_statuses WHERE name=:n"),
            {"n": status_name}
        ).scalar()

        conn.execute(text("""
            INSERT INTO requests (
                id, start_date, climate_tech_type, climate_tech_model,
                problem_description, status_id, client_id, master_id,
                completion_date
            )
            VALUES (
                :id, :start_date, :type, :model,
                :problem, :status_id, :client_id, :master_id,
                :completion_date
            )
            ON CONFLICT (id) DO NOTHING
        """), {
            "id": int(row["requestID"]),
            "start_date": row["startDate"],
            "type": row["climateTechType"],
            "model": row["climateTechModel"],
            "problem": row["problemDescryption"],
            "status_id": status_id,
            "client_id": int(row["clientID"]),
            "master_id": int(row["masterID"]) if not pd.isna(row["masterID"]) else None,
            "completion_date": None if pd.isna(row["completionDate"]) else row["completionDate"]
        })

    # комментарии
    for _, row in comments_df.iterrows():
        conn.execute(text("""
            INSERT INTO comments (id, request_id, user_id, message)
            VALUES (:id, :request_id, :user_id, :message)
            ON CONFLICT (id) DO NOTHING
        """), {
            "id": int(row["commentID"]),
            "request_id": int(row["requestID"]),
            "user_id": int(row["masterID"]),
            "message": row["message"]
        })

print("✅ Данные из Excel загружены")
