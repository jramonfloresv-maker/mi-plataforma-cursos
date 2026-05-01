from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from ..database import get_db
from .. import models, schemas, auth

router = APIRouter(prefix="/projects", tags=["Proyectos - Kanban"])


# ==================== PROYECTOS ====================

@router.post("/")
def create_project(
        project: schemas.ProjectCreate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(auth.get_current_user)
):
    """
    Crear un nuevo proyecto
    """
    db_project = models.Project(
        name=project.name,
        description=project.description,
        owner_id=current_user.id,
        due_date=project.due_date
    )
    db.add(db_project)
    db.commit()
    db.refresh(db_project)

    return db_project


@router.get("/", response_model=List[schemas.ProjectResponse])
def list_projects(
        skip: int = 0,
        limit: int = 100,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(auth.get_current_user)
):
    """
    Listar todos los proyectos del usuario
    """
    projects = db.query(models.Project).filter(
        models.Project.owner_id == current_user.id
    ).offset(skip).limit(limit).all()

    return projects


@router.get("/{project_id}", response_model=schemas.ProjectResponse)
def get_project(
        project_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(auth.get_current_user)
):
    """
    Obtener un proyecto con todas sus tareas
    """
    project = db.query(models.Project).filter(
        models.Project.id == project_id,
        models.Project.owner_id == current_user.id
    ).first()

    if not project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")

    return project


@router.put("/{project_id}")
def update_project(
        project_id: int,
        project_update: schemas.ProjectCreate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(auth.get_current_user)
):
    """
    Actualizar un proyecto
    """
    project = db.query(models.Project).filter(
        models.Project.id == project_id,
        models.Project.owner_id == current_user.id
    ).first()

    if not project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")

    project.name = project_update.name
    project.description = project_update.description
    project.due_date = project_update.due_date

    db.commit()
    db.refresh(project)

    return project


@router.delete("/{project_id}")
def delete_project(
        project_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(auth.get_current_user)
):
    """
    Eliminar un proyecto (y todas sus tareas)
    """
    project = db.query(models.Project).filter(
        models.Project.id == project_id,
        models.Project.owner_id == current_user.id
    ).first()

    if not project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")

    db.delete(project)
    db.commit()

    return {"message": "Proyecto eliminado exitosamente"}


# ==================== TAREAS ====================

@router.post("/{project_id}/tasks")
def create_task(
        project_id: int,
        task: schemas.TaskCreate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(auth.get_current_user)
):
    """
    Crear una nueva tarea en un proyecto
    """
    # Verificar que el proyecto existe y pertenece al usuario
    project = db.query(models.Project).filter(
        models.Project.id == project_id,
        models.Project.owner_id == current_user.id
    ).first()

    if not project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")

    # Obtener el orden máximo actual
    max_order = db.query(models.Task).filter(
        models.Task.project_id == project_id
    ).count()

    db_task = models.Task(
        title=task.title,
        description=task.description,
        status=task.status,
        priority=task.priority,
        order=max_order,
        project_id=project_id,
        assignee_id=task.assignee_id,
        due_date=task.due_date
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)

    return db_task


@router.put("/tasks/{task_id}")
def update_task(
        task_id: int,
        task_update: schemas.TaskCreate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(auth.get_current_user)
):
    """
    Actualizar una tarea
    """
    task = db.query(models.Task).join(models.Project).filter(
        models.Task.id == task_id,
        models.Project.owner_id == current_user.id
    ).first()

    if not task:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")

    task.title = task_update.title
    task.description = task_update.description
    task.status = task_update.status
    task.priority = task_update.priority
    task.assignee_id = task_update.assignee_id
    task.due_date = task_update.due_date

    db.commit()
    db.refresh(task)

    return task


@router.patch("/tasks/{task_id}/status")
def update_task_status(
        task_id: int,
        status: str = Query(..., pattern="^(todo|in_progress|review|done)$"),
        db: Session = Depends(get_db),
        current_user: models.User = Depends(auth.get_current_user)
):
    """
    Cambiar el estado de una tarea (útil para drag & drop en Kanban)
    """
    task = db.query(models.Task).join(models.Project).filter(
        models.Task.id == task_id,
        models.Project.owner_id == current_user.id
    ).first()

    if not task:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")

    task.status = status
    db.commit()

    return {"message": f"Tarea movida a '{status}'", "task_id": task_id}


@router.delete("/tasks/{task_id}")
def delete_task(
        task_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(auth.get_current_user)
):
    """
    Eliminar una tarea
    """
    task = db.query(models.Task).join(models.Project).filter(
        models.Task.id == task_id,
        models.Project.owner_id == current_user.id
    ).first()

    if not task:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")

    db.delete(task)
    db.commit()

    return {"message": "Tarea eliminada exitosamente"}


# ==================== REORDENAR TAREAS (DRAG & DROP) ====================

@router.post("/tasks/reorder")
def reorder_tasks(
        task_order: List[dict],
        db: Session = Depends(get_db),
        current_user: models.User = Depends(auth.get_current_user)
):
    """
    Reordenar tareas después de drag & drop
    Espera una lista como: [{"task_id": 1, "order": 0, "status": "todo"}, ...]
    """
    for item in task_order:
        task = db.query(models.Task).join(models.Project).filter(
            models.Task.id == item["task_id"],
            models.Project.owner_id == current_user.id
        ).first()

        if task:
            task.order = item.get("order", task.order)
            task.status = item.get("status", task.status)

    db.commit()

    return {"message": "Tareas reordenadas exitosamente"}


# ==================== ESTADÍSTICAS ====================

@router.get("/stats/kanban")
def get_kanban_stats(
        db: Session = Depends(get_db),
        current_user: models.User = Depends(auth.get_current_user)
):
    """
    Obtener estadísticas del tablero Kanban
    """
    tasks = db.query(models.Task).join(models.Project).filter(
        models.Project.owner_id == current_user.id
    ).all()

    stats = {
        "todo": len([t for t in tasks if t.status == "todo"]),
        "in_progress": len([t for t in tasks if t.status == "in_progress"]),
        "review": len([t for t in tasks if t.status == "review"]),
        "done": len([t for t in tasks if t.status == "done"]),
        "total": len(tasks),
        "completion_rate": 0
    }

    if stats["total"] > 0:
        stats["completion_rate"] = round(stats["done"] / stats["total"] * 100, 2)

    return stats