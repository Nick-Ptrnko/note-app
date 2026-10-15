from datetime import datetime
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

app = FastAPI(title="Note Taking API")

# Підключаємо пастку шаблонів Jinja2
templates = Jinja2Templates(directory="templates")


class Note:

    def __init__(self, note_id: int, title: str, content: str):
        self.id: int = note_id
        self.title: str = title
        self.content: str = content
        self.created_at: str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "created_at": self.created_at,
        }


class NoteRepository:

    def __init__(self):
        self._storage: dict[int, Note] = {}
        self._next_id: int = 1

    def add(self, title: str, content: str) -> Note:
        note = Note(note_id=self._next_id, title=title, content=content)
        self._storage[note.id] = note
        self._next_id += 1
        return note

    def get_all(self) -> list[Note]:
        return list(self._storage.values())

    def get_by_id(self, note_id: int) -> Note | None:
        return self._storage.get(note_id)


repo = NoteRepository()


# Головна сторінка: передаємо список нотаток для лівого сайдбару
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    notes = repo.get_all()
    return templates.TemplateResponse(
        request, "index.html", {"notes": notes}
    )


# Сторінка однієї нотатки: також передаємо notes для сайдбару
@app.get("/note/{note_id}", response_class=HTMLResponse)
async def view_note_page(request: Request, note_id: int):
    note = repo.get_by_id(note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Нотатку не знайдено")

    notes = repo.get_all()
    return templates.TemplateResponse(
        request, "detail.html", {"note": note, "notes": notes}
    )


# API ендпоінти залишаються без змін
@app.get("/notes")
async def get_notes():
    return [note.to_dict() for note in repo.get_all()]


@app.post("/notes")
async def create_note(title: str, content: str):
    if not title.strip() or not content.strip():
        raise HTTPException(
            status_code=400, detail="Заголовок та текст не можуть бути порожніми"
        )
    note = repo.add(title=title.strip(), content=content.strip())
    return note.to_dict()
