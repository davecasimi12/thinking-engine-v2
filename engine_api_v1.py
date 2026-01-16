from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# import routers
from router.nicole_strategist_v1 import router as nicole_router
from router.jon_executor_v1 import router as jon_router
from router.maya_coach_v1 import router as maya_router
from router.sam_analytics_v1 import router as sam_router
from router.kai_creative_v1 import router as kai_router

app = FastAPI(
    title="Nivora Thinking Engine API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}

app.include_router(nicole_router, prefix="/nicole", tags=["Nicole"])
app.include_router(jon_router, prefix="/jon", tags=["Jon"])
app.include_router(maya_router, prefix="/maya", tags=["Maya"])
app.include_router(sam_router, prefix="/sam", tags=["Sam"])
app.include_router(kai_router, prefix="/kai", tags=["Kai"])