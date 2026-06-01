import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.automation_workflow import AutomationWorkflow
from app.models.category import Category
from app.schemas.automation_workflow import (
    AutomationWorkflowCreate,
    AutomationWorkflowRead,
    AutomationWorkflowUpdate,
)

router = APIRouter(prefix="/automation-workflows", tags=["Automation Workflows"])


async def get_categories_by_ids(category_ids: list[uuid.UUID], db: AsyncSession) -> list[Category]:
    if not category_ids:
        return []

    result = await db.execute(select(Category).where(Category.id.in_(category_ids)))
    categories = result.scalars().all()

    found_ids = {category.id for category in categories}
    missing_ids = [str(category_id) for category_id in category_ids if category_id not in found_ids]
    if missing_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid category_ids: {', '.join(missing_ids)}",
        )

    category_by_id = {category.id: category for category in categories}
    return [category_by_id[category_id] for category_id in category_ids]


@router.post("", response_model=AutomationWorkflowRead, status_code=status.HTTP_201_CREATED)
async def create_automation_workflow(
    workflow_data: AutomationWorkflowCreate,
    db: AsyncSession = Depends(get_db),
):
    payload = workflow_data.model_dump(exclude={"category_ids"}, by_alias=False)
    workflow = AutomationWorkflow(**payload)
    workflow.categories = await get_categories_by_ids(workflow_data.category_ids, db)
    db.add(workflow)
    await db.commit()

    created = await db.execute(
        select(AutomationWorkflow)
        .options(selectinload(AutomationWorkflow.categories))
        .where(AutomationWorkflow.id == workflow.id)
    )
    return created.scalar_one()


@router.get("", response_model=list[AutomationWorkflowRead])
async def list_automation_workflows(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AutomationWorkflow)
        .options(selectinload(AutomationWorkflow.categories))
        .order_by(AutomationWorkflow.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


@router.get("/{workflow_id}", response_model=AutomationWorkflowRead)
async def get_automation_workflow(workflow_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AutomationWorkflow)
        .options(selectinload(AutomationWorkflow.categories))
        .where(AutomationWorkflow.id == workflow_id)
    )
    workflow = result.scalar_one_or_none()
    if workflow is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Automation workflow not found")
    return workflow


@router.patch("/{workflow_id}", response_model=AutomationWorkflowRead)
async def update_automation_workflow(
    workflow_id: uuid.UUID,
    workflow_data: AutomationWorkflowUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AutomationWorkflow)
        .options(selectinload(AutomationWorkflow.categories))
        .where(AutomationWorkflow.id == workflow_id)
    )
    workflow = result.scalar_one_or_none()
    if workflow is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Automation workflow not found")

    update_data = workflow_data.model_dump(exclude_unset=True, by_alias=False)
    category_ids = update_data.pop("category_ids", None)
    if category_ids is not None:
        workflow.categories = await get_categories_by_ids(category_ids, db)

    for field, value in update_data.items():
        setattr(workflow, field, value)

    await db.commit()

    updated = await db.execute(
        select(AutomationWorkflow)
        .options(selectinload(AutomationWorkflow.categories))
        .where(AutomationWorkflow.id == workflow.id)
    )
    return updated.scalar_one()


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_automation_workflow(workflow_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AutomationWorkflow).where(AutomationWorkflow.id == workflow_id))
    workflow = result.scalar_one_or_none()
    if workflow is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Automation workflow not found")

    await db.delete(workflow)
    await db.commit()
    return None
