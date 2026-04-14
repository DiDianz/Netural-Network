# schemas/auth.py
from pydantic import BaseModel, Field

class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=30, description="用户名")
    password: str = Field(..., min_length=1, max_length=50, description="密码")
    code: str = Field(default="", description="验证码")
    uuid: str = Field(default="", description="验证码UUID")

class LoginResponse(BaseModel):
    token: str
    expire_time: str

class CaptchaResponse(BaseModel):
    img: str        # Base64 图片
    uuid: str       # 验证码ID
