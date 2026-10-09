from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from starlette.exceptions import HTTPException as StarletteHTTPException

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from progress_fitness_api.core.limiter import Limit

from progress_fitness_api.routers.users import router as user_router
from progress_fitness_api.routers.plan import router as plan_router

app = FastAPI(title="Progress Fit API")

# routers
for router in (user_router, plan_router):
    app.include_router(router)


# Exception Handler
app.state.limiter = Limit

app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_error(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": f"Rate Limit Exceeded: {exc.detail}"},
    )


@app.exception_handler(StarletteHTTPException)
async def http_error(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail},
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    err = exc.errors()[0]
    field = err["loc"][-1]
    return JSONResponse(status_code=422, content={"message": f"{field}: {err['msg']}"})


@app.get("/")
def health_check():
    return {"status": "ok"}
