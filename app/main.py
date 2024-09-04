from fastapi import FastAPI
from app.api.v1.endpoints.get_authorization import router as auth_router
from app.api.v1.endpoints.data_preprocessing import router as preprocess_router

import os

app = FastAPI()

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

app.include_router(auth_router, prefix="/auth")
app.include_router(preprocess_router, prefix='/preprocess')