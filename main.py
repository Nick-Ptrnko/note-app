import os
from datetime import datetime
from itertools import groupby
from dotenv import load_dotenv
import pymysql
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

# Завантажуємо змінні середовища з файлу .env
load_dotenv()

app = FastAPI(title="Mind Cards Log API")
templates = Jinja2Templates(directory="templates")

# Тепер пароль та інші параметри беруться безпечно з системного середовища
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "note_app"),
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
}


def get_db_connection():
    return pymysql.connect(**DB_CONFIG)


def init_db():
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS notes (
                id INT AUTO_INCREMENT PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                content TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS note_links (
                note_id INT,
                linked_note_id INT,
                PRIMARY KEY (note_id, linked_note_id)
            )
        """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS app_config (
                `key` VARCHAR(50) PRIMARY KEY,
                `value` TEXT
            )
        """
        )
        cursor.execute(
            """
            INSERT IGNORE INTO app_config (`key`, `value`) 
            VALUES ('reminder', 'Це ваше перше нагадування. Натисніть «змінити» нижче, щоб оновити цей текст.')
        """
        )
    conn.commit()
    conn.close()


init_db()


class Note:

    def __init__(
        self,
        note_id: int,
        title: str,
        content: str,
        linked_note_ids: list[int] | None = None,
        created_at: str | None = None,
    ):
        self.id: int = note_id
        self.title: str = title
        self.content: str = content
        self.linked_note_ids: list[int] = linked_note_ids or []
        self.created_at: str = created_at or datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "linked_note_ids": self.linked_note_ids,
            "created_at": self.created_at,
        }


class NoteRepository:

    def get_all(self) -> list[Note]:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT n.id, n.title, n.content, n.created_at, l.linked_note_id
                FROM notes n
                LEFT JOIN note_links l ON n.id = l.note_id
            """
            )
            rows = cursor.fetchall()

            notes_dict = {}
            for row in rows:
                nid = row["id"]
                if nid not in notes_dict:
                    created_at = row["created_at"]
                    created_at_str = (
                        created_at.strftime("%Y-%m-%d %H:%M:%S")
                        if hasattr(created_at, "strftime")
                        else str(created_at)
                    )

                    notes_dict[nid] = {
                        "id": nid,
                        "title": row["title"],
                        "content": row["content"],
                        "created_at": created_at_str,
                        "linked_note_ids": [],
                    }
                if row["linked_note_id"] is not None:
                    notes_dict[nid]["linked_note_ids"].append(
                        row["linked_note_id"]
                    )

            notes = [
                Note(
                    note_id=data["id"],
                    title=data["title"],
                    content=data["content"],
                    linked_note_ids=data["linked_note_ids"],
                    created_at=data["created_at"],
                )
                for data in notes_dict.values()
            ]
        conn.close()
        return notes

    def get_by_id(self, note_id: int) -> Note | None:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT n.id, n.title, n.content, n.created_at, l.linked_note_id
                FROM notes n
                LEFT JOIN note_links l ON n.id = l.note_id
                WHERE n.id = %s
            """,
                (note_id,),
            )
            rows = cursor.fetchall()
            if not rows:
                conn.close()
                return None

            row = rows[0]
            created_at = row["created_at"]
            created_at_str = (
                created_at.strftime("%Y-%m-%d %H:%M:%S")
                if hasattr(created_at, "strftime")
                else str(created_at)
            )

            links = [
                r["linked_note_id"]
                for r in rows
                if r["linked_note_id"] is not None
            ]
            note = Note(
                note_id=row["id"],
                title=row["title"],
                content=row["content"],
                linked_note_ids=links,
                created_at=created_at_str,
            )
        conn.close()
        return note

    def add(
        self, title: str, content: str, linked_note_ids: list[int] | None = None
    ) -> Note:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO notes (title, content) VALUES (%s, %s)",
                (title, content),
            )
            note_id = cursor.lastrowid
            if linked_note_ids:
                for lid in linked_note_ids:
                    cursor.execute(
                        "INSERT IGNORE INTO note_links (note_id, linked_note_id) VALUES (%s, %s)",
                        (note_id, lid),
                    )
        conn.commit()
        conn.close()
        return self.get_by_id(note_id)

    def update(
        self,
        note_id: int,
        title: str,
        content: str,
        linked_note_ids: list[int] | None = None,
    ) -> Note | None:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE notes SET title = %s, content = %s WHERE id = %s",
                (title, content, note_id),
            )
            cursor.execute(
                "DELETE FROM note_links WHERE note_id = %s", (note_id,)
            )
            if linked_note_ids:
                for lid in linked_note_ids:
                    cursor.execute(
                        "INSERT IGNORE INTO note_links (note_id, linked_note_id) VALUES (%s, %s)",
                        (note_id, lid),
                    )
        conn.commit()
        conn.close()
        return self.get_by_id(note_id)

    def delete(self, note_id: int):
        """Видаляє нотатку та всі її зв'язки з таблиць БД."""
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # Видаляємо зв'язки, де ця нотатка є джерелом або ціллю для інших
            cursor.execute(
                "DELETE FROM note_links WHERE note_id = %s OR linked_note_id = %s",
                (note_id, note_id),
            )
            # Видаляємо саму нотатку
            cursor.execute("DELETE FROM notes WHERE id = %s", (note_id,))
        conn.commit()
        conn.close()

    def get_reminder(self) -> str:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT `value` FROM app_config WHERE `key` = 'reminder'"
            )
            row = cursor.fetchone()
        conn.close()
        return row["value"] if row else ""

    def set_reminder(self, text: str):
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE app_config SET `value` = %s WHERE `key` = 'reminder'",
                (text,),
            )
        conn.commit()
        conn.close()


repo = NoteRepository()


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    notes = repo.get_all()
    sorted_notes = sorted(notes, key=lambda n: n.created_at, reverse=True)

    grouped_notes = []
    for date, items in groupby(sorted_notes, key=lambda n: n.created_at[:10]):
        grouped_notes.append((date, list(items)))

    reminder = repo.get_reminder()
    return templates.TemplateResponse(
        request,
        "index.html",
        {"grouped_notes": grouped_notes, "reminder": reminder},
    )


@app.get("/reminder/edit", response_class=HTMLResponse)
async def edit_reminder_page(request: Request):
    reminder = repo.get_reminder()
    return templates.TemplateResponse(
        request, "reminder_edit.html", {"reminder": reminder}
    )


@app.post("/reminder/update")
async def update_reminder(reminder_text: str = Form(...)):
    repo.set_reminder(reminder_text.strip())
    return RedirectResponse(url="/", status_code=303)


@app.get("/create", response_class=HTMLResponse)
async def create_page(request: Request):
    notes = repo.get_all()
    return templates.TemplateResponse(request, "create.html", {"notes": notes})


@app.get("/note/{note_id}/edit", response_class=HTMLResponse)
async def edit_page(request: Request, note_id: int):
    note = repo.get_by_id(note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Нотатку не знайдено")
    notes = repo.get_all()
    linked_notes = [repo.get_by_id(lid) for lid in note.linked_note_ids]
    linked_notes = [n for n in linked_notes if n is not None]

    return templates.TemplateResponse(
        request,
        "edit.html",
        {"note": note, "notes": notes, "linked_notes": linked_notes},
    )


@app.get("/note/{note_id}", response_class=HTMLResponse)
async def view_note_page(request: Request, note_id: int):
    note = repo.get_by_id(note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Нотатку не знайдено")

    linked_notes = [repo.get_by_id(lid) for lid in note.linked_note_ids]
    linked_notes = [n for n in linked_notes if n is not None]

    return templates.TemplateResponse(
        request, "detail.html", {"note": note, "linked_notes": linked_notes}
    )


@app.post("/notes")
async def create_note(
    title: str = Form(...),
    content: str = Form(...),
    linked_titles: list[str] = Form([]),
):
    if not title.strip() or not content.strip():
        raise HTTPException(
            status_code=400, detail="Заголовок та текст не можуть бути порожніми"
        )

    linked_ids = []
    all_notes = repo.get_all()
    for t in linked_titles:
        t_clean = t.strip()
        if t_clean:
            found = next((n for n in all_notes if n.title == t_clean), None)
            if found and found.id not in linked_ids:
                linked_ids.append(found.id)

    repo.add(
        title=title.strip(), content=content.strip(), linked_note_ids=linked_ids
    )
    return RedirectResponse(url="/", status_code=303)


@app.post("/note/{note_id}/update")
async def update_note(
    note_id: int,
    title: str = Form(...),
    content: str = Form(...),
    linked_titles: list[str] = Form([]),
):
    if not title.strip() or not content.strip():
        raise HTTPException(
            status_code=400, detail="Заголовок та текст не можуть бути порожніми"
        )

    linked_ids = []
    all_notes = repo.get_all()
    for t in linked_titles:
        t_clean = t.strip()
        if t_clean:
            found = next((n for n in all_notes if n.title == t_clean), None)
            if found and found.id not in linked_ids and found.id != note_id:
                linked_ids.append(found.id)

    updated = repo.update(
        note_id,
        title=title.strip(),
        content=content.strip(),
        linked_note_ids=linked_ids,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Нотатку не знайдено")

    return RedirectResponse(url=f"/note/{note_id}", status_code=303)


# Маршрут для видалення нотатки
@app.post("/note/{note_id}/delete")
async def delete_note(note_id: int):
    note = repo.get_by_id(note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Нотатку не знайдено")
    repo.delete(note_id)
    return RedirectResponse(url="/", status_code=303)