from datetime import datetime
from itertools import groupby
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

app = FastAPI(title="Note Taking API")

# Підключаємо папку templates для HTML-файлів
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


# 1. Головна сторінка: список нотаток, згрупований за датами
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    notes = repo.get_all()

    # Сортуємо від найновіших до найстаріших
    sorted_notes = sorted(notes, key=lambda n: n.created_at, reverse=True)

    # Групуємо нотатки за датою (перші 10 символів: "YYYY-MM-DD")
    grouped_notes = []
    for date, items in groupby(sorted_notes, key=lambda n: n.created_at[:10]):
        grouped_notes.append((date, list(items)))

    return templates.TemplateResponse(
        request, "index.html", {"grouped_notes": grouped_notes}
    )


# 2. Сторінка для створення нової нотатки
@app.get("/create", response_class=HTMLResponse)
async def create_page(request: Request):
    return templates.TemplateResponse(request, "create.html", {})


# 3. Сторінка перегляду конкретної нотатки
@app.get("/note/{note_id}", response_class=HTMLResponse)
async def view_note_page(request: Request, note_id: int):
    note = repo.get_by_id(note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Нотатку не знайдено")
    return templates.TemplateResponse(
        request, "detail.html", {"note": note}
    )


# 4. Обробка надсилання форми створення
@app.post("/notes")
async def create_note(title: str = Form(...), content: str = Form(...)):
    if not title.strip() or not content.strip():
        raise HTTPException(
            status_code=400, detail="Заголовок та текст не можуть бути порожніми"
        )
    repo.add(title=title.strip(), content=content.strip())
    # Після збереження перенаправляємо користувача назад на головну сторінку
    return RedirectResponse(url="/", status_code=303)
