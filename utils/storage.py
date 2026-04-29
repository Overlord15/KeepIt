"""
NoteStorage — persistent JSON store, identical schema to the original.
"""

import os, json, uuid
from datetime import datetime
from kivy.utils import platform


def get_storage_path():
    if platform == 'android':
        from android.storage import app_storage_path
        return os.path.join(app_storage_path(), 'notes.json')
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), 'notes.json')


def make_note(title='', body='', checklist=None, images=None,
              color_index=0, pinned=False):
    now = datetime.now().isoformat()
    return {
        'id':          str(uuid.uuid4()),
        'title':       title,
        'body':        body,
        'checklist':   checklist or [],
        'images':      images    or [],
        'color_index': color_index,
        'pinned':      pinned,
        'created_at':  now,
        'updated_at':  now,
    }


class NoteStorage:
    def __init__(self):
        self.path   = get_storage_path()
        self._notes = []
        self.load()

    # ── I/O ──────────────────────────────────────────────────────────────────
    def load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r', encoding='utf-8') as f:
                    self._notes = json.load(f)
                return
            except Exception as e:
                print(f'[Storage] Load error: {e}')
        self._notes = self._sample_notes()
        self.save()

    def save(self):
        try:
            with open(self.path, 'w', encoding='utf-8') as f:
                json.dump(self._notes, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f'[Storage] Save error: {e}')

    # ── Queries ───────────────────────────────────────────────────────────────
    def all(self):      return list(self._notes)
    def pinned(self):   return [n for n in self._notes if n.get('pinned')]
    def others(self):   return [n for n in self._notes if not n.get('pinned')]

    def get(self, note_id):
        return next((n for n in self._notes if n['id'] == note_id), None)

    def search(self, query):
        q = query.lower()
        return [n for n in self._notes
                if q in n.get('title','').lower()
                or q in n.get('body','').lower()
                or any(q in i.get('text','').lower()
                       for i in n.get('checklist',[]))]

    # ── Mutations ─────────────────────────────────────────────────────────────
    def add(self, note):
        self._notes.insert(0, note)
        self.save()

    def update(self, note):
        note['updated_at'] = datetime.now().isoformat()
        for i, n in enumerate(self._notes):
            if n['id'] == note['id']:
                self._notes[i] = note
                self.save()
                return
        self.add(note)

    def delete(self, note_id):
        self._notes = [n for n in self._notes if n['id'] != note_id]
        self.save()

    def delete_many(self, note_ids):
        ids = set(note_ids)
        self._notes = [n for n in self._notes if n['id'] not in ids]
        self.save()

    def toggle_pin(self, note_id):
        n = self.get(note_id)
        if n:
            n['pinned'] = not n.get('pinned', False)
            self.update(n)

    def duplicate(self, note_id):
        n = self.get(note_id)
        if n:
            copy = dict(n)
            copy['id']         = str(uuid.uuid4())
            copy['pinned']     = False
            now = datetime.now().isoformat()
            copy['created_at'] = now
            copy['updated_at'] = now
            copy['title']      = copy.get('title','') + ' (copy)' if copy.get('title') else ''
            self._notes.insert(0, copy)
            self.save()

    # ── Sample data ───────────────────────────────────────────────────────────
    def _sample_notes(self):
        return [
            make_note(
                title='Welcome to KeepIt!',
                body='Your Google Keep clone built with Kivy.\nTap + to add a note.\nLong-press a card to select.',
                pinned=True, color_index=6,
            ),
            make_note(
                title='Grocery List',
                checklist=[
                    {'text': 'Milk',   'checked': True},
                    {'text': 'Eggs',   'checked': False},
                    {'text': 'Bread',  'checked': False},
                    {'text': 'Butter', 'checked': True},
                ],
                color_index=4,
            ),
            make_note(
                title='Project Ideas',
                body='1. Build a Kivy app\n2. Learn machine learning\n3. Deploy to Android',
                color_index=3,
            ),
            make_note(
                title='',
                body='Remember to buy birthday gift for mom 🎂',
                color_index=8,
            ),
            make_note(
                title='Recipe — Pasta',
                body='Boil water\nAdd salt\nCook pasta 8 mins\nMake sauce with tomatoes',
                color_index=2,
            ),
        ]
