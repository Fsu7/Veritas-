from fastapi import APIRouter

router = APIRouter()


@router.get("/status")
async def model_status():
    return {"message": "Model status endpoint - to be implemented"}
