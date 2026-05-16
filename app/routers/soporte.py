from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import SupportMessage, UserRoleEnum
from ..schemas import CreateSupportMessageRequest
from ..security import get_current_user, require_role
from ..models import User

router = APIRouter(prefix="/soporte", tags=["soporte"])


@router.post("", status_code=201)
def send_support_message(
    body: CreateSupportMessageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    msg = SupportMessage(
        from_user_id=current_user.id,
        from_username=current_user.username,
        from_role=current_user.role.value,
        institution_id=current_user.institution_id,
        message=body.message.strip(),
    )
    db.add(msg)
    db.commit()
    return {"ok": True}
