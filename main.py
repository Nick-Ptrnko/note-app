from datetime import datetime
from itertools import groupby
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

app = FastAPI(title="Note Taking API")

templates = Jinja2Templates(directory="templates")


class Note:

    def __init__(
        self,
        note_id: int,
        title: str,
        content: str,
        linked_note_ids: list[int] | None = None,
    ):
        self.id: int = note_id
        self.title: str = title
        self.content: str = content
        self.linked_note_ids: list[int] = linked_note_ids or []
        self.created_at: str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "linked_note_ids": self.linked_note_ids,
            "created_at": self.created_at,
        }


class NoteRepository:

    def __init__(self):
        self._storage: dict[int, Note] = {}
        self._next_id: int = 1

    def add(
        self, title: str, content: str, linked_note_ids: list[int] | None = None
    ) -> Note:
        note = Note(
            note_id=self._next_id,
            title=title,
            content=content,
            linked_note_ids=linked_note_ids,
        )
        self._storage[note.id] = note
        self._next_id += 1
        return note

    def update(
        self,
        note_id: int,
        title: str,
        content: str,
        linked_note_ids: list[int] | None = None,
    ) -> Note | None:
        note = self.get_by_id(note_id)
        if not note:
            return None
        note.title = title
        note.content = content
        note.linked_note_ids = linked_note_ids or []
        return note

    def get_all(self) -> list[Note]:
        return list(self._storage.values())

    def get_by_id(self, note_id: int) -> Note | None:
        return self._storage.get(note_id)


repo = NoteRepository()


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    notes = repo.get_all()
    sorted_notes = sorted(notes, key=lambda n: n.created_at, reverse=True)

    grouped_notes = []
    for date, items in groupby(sorted_notes, key=lambda n: n.created_at[:10]):
        grouped_notes.append((date, list(items)))

    return templates.TemplateResponse(
        request, "index.html", {"grouped_notes": grouped_notes}
    )


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
    
    # Отримуємо об'єкти пов'язаних нотаток, щоб передати їхні назви у форму редагування
    linked_notes = [repo.get_by_id(lid) for lid in note.linked_note_ids]
    linked_notes = [n for n in linked_notes if n is not None]

    return templates.TemplateResponse(
        request, "edit.html", {"note": note, "notes": notes, "linked_notes": linked_notes}
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


# Приймаємо список значень linked_titles замість одного рядка
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
