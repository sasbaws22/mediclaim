from app.routes import audit, auth, claims,payments, reviews,users,policy,employer,provider,policyholder
from fastapi import FastAPI, APIRouter


from app.routes import users
from app.core.config import settings
from app.middleware import register_middleware 


version = "v1"
version_prefix =f"/{version}"

app = FastAPI(
    title="MedicalClaims API",
    description="API for MedicalClaims system",
    version=version,
    license_info={"name": "MIT License", "url": "https://opensource.org/license/mit"},
    contact={
        "url": "https://github.com/sasbaws22",
        "email": "ssako@faabsystems.com",
    },
    terms_of_service="https://example.com/tos",
    openapi_url=f"{version_prefix}/openapi.json",
    docs_url=f"{version_prefix}/docs",
    redoc_url=f"{version_prefix}/redoc"
) 

register_middleware(app)

# API router
api_router = APIRouter()
api_router.include_router(auth.router, prefix=f"{version_prefix}/auth", tags=["authentication"])
api_router.include_router(users.router, prefix=f"{version_prefix}/users", tags=["users"])
api_router.include_router(claims.router, prefix=f"{version_prefix}/claims", tags=["claims"])
api_router.include_router(reviews.router, prefix=f"{version_prefix}/reviews", tags=["reviews"])
api_router.include_router(payments.router, prefix=f"{version_prefix}/payments", tags=["payments"])
api_router.include_router(audit.router, prefix=f"{version_prefix}/audit", tags=["audit"])
api_router.include_router(policy.router, prefix=f"{version_prefix}/policy", tags=["Policy"]) 
api_router.include_router(employer.router, prefix=f"{version_prefix}/employer", tags=["Employer"]) 
api_router.include_router(policyholder.router, prefix=f"{version_prefix}/policyholders", tags=["Policyholders"])

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
def root():
    return {"message": "Welcome to MedicalClaims API"}

@app.get("/health")
def health_check():
    return {"status": "ok"}

api_router.include_router(provider.router, prefix=f"{version_prefix}/providers", tags=["Providers"])

