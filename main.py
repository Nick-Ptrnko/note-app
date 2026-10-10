from datetime import datetime


# 1. Клас-Сутність
class Note:

    def __init__(self, note_id: int, title: str, content: str):
        self.id: int = note_id
        self.title: str = title
        self.content: str = content
        self.created_at: str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def __repr__(self) -> str:
        return f"<Note #{self.id}: {self.title}>"


# 2. Клас-Репозиторій
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


# --- 3. ІНТЕРАКТИВНЕ КЕРУВАННЯ В КОНСОЛІ ---
if __name__ == "__main__":
    repo = NoteRepository()

    while True:
        print("\n=== МЕНЮ ===")
        print("1. Створити нотатку")
        print("2. Показати всі нотатки")
        print("3. Прочитати нотатку за ID")
        print("0. Вийти")

        choice = input("Виберіть дію: ").strip()

        if choice == "1":
            title = input("Введіть заголовок: ").strip()
            content = input("Введіть текст нотатки: ").strip()
            if title and content:
                new_note = repo.add(title=title, content=content)
                print(f" Успішно створено нотатку #{new_note.id}")
            else:
                print(" Заголовок і текст не можуть бути порожніми!")

        elif choice == "2":
            notes = repo.get_all()
            if not notes:
                print(" Список нотаток порожній.")
            else:
                print("\n--- Список усіх нотаток ---")
                for note in notes:
                    print(f"#{note.id} | {note.title} ({note.created_at})")

        elif choice == "3":
            raw_id = input("Введіть ID нотатки: ").strip()
            if raw_id.isdigit():
                note_id = int(raw_id)
                note = repo.get_by_id(note_id)
                if note:
                    print(f"\n--- Нотатка #{note.id} ---")
                    print(f"Заголовок: {note.title}")
                    print(f"Текст:     {note.content}")
                    print(f"Створено:  {note.created_at}")
                else:
                    print(f" Нотатку з ID {note_id} не знайдено.")
            else:
                print(" ID має бути числом!")

        elif choice == "0":
            print("До побачення!")
            break

        else:
            print("Невідома команда, спробуйте ще раз.")