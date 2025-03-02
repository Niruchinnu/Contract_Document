from fastapi import FastAPI
from Document import router as document_router
from database import engine, Base
from Auth import router as auth_router

Base.metadata.create_all(bind=engine)

app = FastAPI()

# Include routers
app.include_router(document_router.router)
app.include_router(auth_router.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to FastAPI with MySQL!"}
