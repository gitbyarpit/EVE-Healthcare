from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.database import get_db
from app.core.logging import get_logger
from app.models.models import DiagnosticCentre, DiagnosticTest
from app.schemas.schemas import CentreCreate, CentreOut, TestCreate, TestOut, PaginatedResponse

router = APIRouter(prefix="/centres", tags=["centres"])
logger = get_logger(__name__)


@router.post("/", response_model=CentreOut, status_code=status.HTTP_201_CREATED)
def create_centre(payload: CentreCreate, db: Session = Depends(get_db)):
    centre = DiagnosticCentre(name=payload.name, location=payload.location)
    db.add(centre)
    db.commit()
    db.refresh(centre)
    logger.info("Centre created: %s (%s)", centre.name, centre.id)
    return centre


@router.get("/", response_model=PaginatedResponse[CentreOut])
def list_centres(
    location: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    base_query = db.query(DiagnosticCentre)
    if location:
        base_query = base_query.filter(DiagnosticCentre.location.ilike(f"%{location}%"))
    total = base_query.count()
    # selectinload avoids the JOIN-based row-multiplication problem that
    # joinedload would cause when combined with LIMIT/OFFSET.
    items = (
        base_query
        .options(selectinload(DiagnosticCentre.tests))
        .offset(skip)
        .limit(limit)
        .all()
    )
    return PaginatedResponse(
        items=items, total=total, skip=skip, limit=limit,
        has_next=(skip + limit) < total,
    )


@router.get("/{centre_id}", response_model=CentreOut)
def get_centre(centre_id: str, db: Session = Depends(get_db)):
    centre = (
        db.query(DiagnosticCentre)
        .options(joinedload(DiagnosticCentre.tests))
        .filter(DiagnosticCentre.id == centre_id)
        .first()
    )
    if not centre:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Centre not found")
    return centre


@router.post("/{centre_id}/tests", response_model=TestOut, status_code=status.HTTP_201_CREATED)
def add_test_to_centre(centre_id: str, payload: TestCreate, db: Session = Depends(get_db)):
    centre = db.get(DiagnosticCentre, centre_id)
    if not centre:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Centre not found")

    test = DiagnosticTest(centre_id=centre_id, name=payload.name, price=payload.price)
    db.add(test)
    db.commit()
    db.refresh(test)
    logger.info("Test '%s' added to centre %s", test.name, centre_id)
    return test


@router.get("/{centre_id}/tests", response_model=list[TestOut])
def list_tests_for_centre(centre_id: str, db: Session = Depends(get_db)):
    centre = db.get(DiagnosticCentre, centre_id)
    if not centre:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Centre not found")
    return db.query(DiagnosticTest).filter(DiagnosticTest.centre_id == centre_id).all()
