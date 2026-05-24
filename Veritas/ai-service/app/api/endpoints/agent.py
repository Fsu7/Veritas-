from fastapi import APIRouter

router = APIRouter()


@router.post("/analyze")
async def analyze():
    return {"message": "Agent analyze endpoint - to be implemented"}
