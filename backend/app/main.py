from typing import Annotated

from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.database import get_session
from backend.app.schemas import HealthRead

app = FastAPI(title="CARE-PACK Backend", version="0.1.0")
DatabaseSession = Annotated[Session, Depends(get_session)]


@app.get("/health", response_model=HealthRead)
def health(session: DatabaseSession) -> HealthRead:
    session.execute(text("SELECT 1"))
    return HealthRead(status="ok", database="connected")
