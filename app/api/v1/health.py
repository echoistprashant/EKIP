from fastapi import APIRouter

router = APIRouter()


@router.get("/health" , tags=["Health"])
async def health_check() -> dict[str,str]:
    return{
        "status": "ok",
        "app": "EKIP",
        "version": "0.1.0"
        }