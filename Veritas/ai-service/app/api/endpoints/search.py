from fastapi import APIRouter

router = APIRouter()


@router.post("/")
async def search():
    return {"message": "Search endpoint - to be implemented"}
