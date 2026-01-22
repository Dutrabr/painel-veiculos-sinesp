from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import auth, crimes, vehicles
from .backend_susep_endpoint import router as susep_router

app = FastAPI(title="SafeDrive RJ", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(crimes.router, prefix="/api/crimes", tags=["crimes"])
app.include_router(vehicles.router, prefix="/api/vehicles", tags=["vehicles"])
app.include_router(susep_router)


@app.get("/")
async def root():
    return {"app": "SafeDrive RJ", "version": "1.0.0", "status": "online"}

@app.get("/health")
async def health():
    return {"status": "healthy"}
