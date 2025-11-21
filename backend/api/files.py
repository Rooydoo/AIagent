"""Files API endpoints."""
import shutil
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..config import settings

router = APIRouter()


class FileMove(BaseModel):
    source: str
    destination: str


class FileCopy(BaseModel):
    source: str
    destination: str


class FileDelete(BaseModel):
    path: str


class FileRename(BaseModel):
    old_path: str
    new_name: str


class FolderCreate(BaseModel):
    path: str


def get_safe_path(path: str) -> Path:
    """Validate and return safe path within allowed directories."""
    base_papers = Path(settings.papers_directory).resolve()
    base_outputs = Path(settings.outputs_directory).resolve()

    target = Path(path).resolve()

    if not (str(target).startswith(str(base_papers)) or
            str(target).startswith(str(base_outputs))):
        raise HTTPException(
            status_code=400,
            detail="許可されたディレクトリ外へのアクセスはできません"
        )

    return target


@router.post("/move")
async def move_file(move: FileMove):
    """Move a file."""
    source = get_safe_path(move.source)
    destination = get_safe_path(move.destination)

    if not source.exists():
        raise HTTPException(status_code=404, detail="ソースファイルが見つかりません")

    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), str(destination))

    return {"message": "ファイルを移動しました", "source": str(source), "destination": str(destination)}


@router.post("/copy")
async def copy_file(copy: FileCopy):
    """Copy a file."""
    source = get_safe_path(copy.source)
    destination = get_safe_path(copy.destination)

    if not source.exists():
        raise HTTPException(status_code=404, detail="ソースファイルが見つかりません")

    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(source), str(destination))

    return {"message": "ファイルをコピーしました", "source": str(source), "destination": str(destination)}


@router.post("/delete")
async def delete_file(delete: FileDelete):
    """Delete a file."""
    path = get_safe_path(delete.path)

    if not path.exists():
        raise HTTPException(status_code=404, detail="ファイルが見つかりません")

    if path.is_dir():
        raise HTTPException(status_code=400, detail="ディレクトリの削除はfolders APIを使用してください")

    path.unlink()
    return {"message": "ファイルを削除しました", "path": str(path)}


@router.post("/rename")
async def rename_file(rename: FileRename):
    """Rename a file."""
    old_path = get_safe_path(rename.old_path)

    if not old_path.exists():
        raise HTTPException(status_code=404, detail="ファイルが見つかりません")

    new_path = old_path.parent / rename.new_name
    old_path.rename(new_path)

    return {"message": "ファイル名を変更しました", "old": str(old_path), "new": str(new_path)}


@router.post("/folders/create")
async def create_folder(folder: FolderCreate):
    """Create a folder."""
    path = get_safe_path(folder.path)
    path.mkdir(parents=True, exist_ok=True)
    return {"message": "フォルダを作成しました", "path": str(path)}


@router.delete("/folders/{path:path}")
async def delete_folder(path: str, recursive: bool = False):
    """Delete a folder."""
    folder_path = get_safe_path(path)

    if not folder_path.exists():
        raise HTTPException(status_code=404, detail="フォルダが見つかりません")

    if not folder_path.is_dir():
        raise HTTPException(status_code=400, detail="指定されたパスはフォルダではありません")

    if recursive:
        shutil.rmtree(str(folder_path))
    else:
        try:
            folder_path.rmdir()
        except OSError:
            raise HTTPException(status_code=400, detail="フォルダが空ではありません。recursive=trueを指定してください")

    return {"message": "フォルダを削除しました", "path": str(folder_path)}
