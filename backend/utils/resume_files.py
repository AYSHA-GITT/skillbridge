"""
Uploaded resume files on disk.

Resume.file_path is stored relative to the backend directory (uploads/resumes/<id>_<uuid>.<ext>).
Account deletion removes the files of the deleted student; `flask resumes prune-orphans`
removes files that no longer belong to any account (left behind before cleanup existed).
"""
import logging
import os
from typing import Iterable, List, Tuple

from flask import current_app

logger = logging.getLogger("skillbridge.resume_files")


def uploads_dir() -> str:
    return current_app.config.get('UPLOAD_FOLDER') or os.path.join(current_app.root_path, 'uploads', 'resumes')


def resolve_resume_path(file_path: str) -> str:
    """Absolute path for a stored Resume.file_path (relative paths are relative to the backend dir)."""
    if not file_path:
        return ""
    if os.path.isabs(file_path):
        return file_path
    return os.path.join(current_app.root_path, file_path)


def delete_resume_files(paths: Iterable[str]) -> int:
    """Delete the given resume files (stored or absolute paths). Never raises; returns count removed."""
    removed = 0
    for p in paths:
        full = resolve_resume_path(p)
        if not full:
            continue
        # Safety: only ever delete inside the uploads folder
        if os.path.commonpath([os.path.abspath(full), os.path.abspath(uploads_dir())]) != os.path.abspath(uploads_dir()):
            logger.warning("Refusing to delete file outside uploads folder: %s", full)
            continue
        try:
            if os.path.isfile(full):
                os.remove(full)
                removed += 1
        except OSError as e:
            logger.warning("Could not delete resume file %s: %s", full, e)
    return removed


def find_orphan_resume_files() -> Tuple[List[str], List[dict]]:
    """Files in the uploads folder not referenced by any Resume row, and
    Resume rows whose file is missing on disk."""
    from models import Resume
    folder = uploads_dir()
    referenced = {}
    for r in Resume.query.all():
        if r.file_path:
            referenced[os.path.basename(r.file_path)] = r
    on_disk = set(os.listdir(folder)) if os.path.isdir(folder) else set()
    orphans = sorted(os.path.join(folder, f) for f in on_disk - set(referenced) if os.path.isfile(os.path.join(folder, f)))
    missing = [{"resume_id": r.id, "student_id": r.student_id, "file_path": r.file_path}
               for name, r in referenced.items() if name not in on_disk]
    return orphans, missing
