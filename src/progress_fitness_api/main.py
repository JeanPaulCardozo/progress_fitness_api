from fastapi import FastAPI, requests
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from progress_fitness_api.routers.users import router as user_router

app = FastAPI(title="Progress Fit API")

app.include_router(user_router)

@app.exception_handler(RequestValidationError)
async def validation_error(request: requests, exc: RequestValidationError):
    err = exc.errors()[0]
    field = err["loc"][-1]
    return JSONResponse(status_code=422, content={"message": f"{field}: {err['msg']}"})


@app.get("/")
def health_check():
    return {"status": "ok"}
