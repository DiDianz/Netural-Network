# api/feature.py
"""
特征方案 CRUD API
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from core.feature_schema import feature_schema_manager

router = APIRouter(prefix="/feature", tags=["特征方案管理"])


class FeatureItem(BaseModel):
    name: str = Field(..., min_length=1, max_length=64, description="特征列名（英文标识）")
    label: str = Field("", max_length=128, description="特征中文名称")
    weight: float = Field(1.0, ge=0.0, le=10.0, description="权重 0~10")


class TargetItem(BaseModel):
    name: str = Field("out_moist", description="目标列名")
    label: str = Field("出口水分", description="目标中文名称")


class BrandColumnItem(BaseModel):
    name: str = Field("brandID", description="品牌列名")
    label: str = Field("品牌标识", description="品牌中文名称")


class CreateSchemaRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    description: str = Field("", max_length=512)
    features: list[FeatureItem] = Field(..., min_length=1)
    target: TargetItem = Field(default_factory=TargetItem)
    brand_column: BrandColumnItem = Field(default_factory=BrandColumnItem)


class UpdateSchemaRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    features: Optional[list[FeatureItem]] = None
    target: Optional[TargetItem] = None
    brand_column: Optional[BrandColumnItem] = None


class CopySchemaRequest(BaseModel):
    new_name: Optional[str] = None


class UpdateWeightsRequest(BaseModel):
    weights: dict[str, float] = Field(..., description="{feature_name: weight}")


@router.get("/schema/list")
async def list_schemas():
    schemas = feature_schema_manager.list_schemas()
    return {"code": 200, "data": schemas}


@router.get("/schema/{schema_id}")
async def get_schema(schema_id: str):
    schema = feature_schema_manager.get_schema(schema_id)
    if not schema:
        raise HTTPException(404, f"方案不存在: {schema_id}")
    return {"code": 200, "data": schema}


@router.get("/schema/{schema_id}/columns")
async def get_column_description(schema_id: str):
    """获取方案的列结构描述（含列顺序、表头示例），用于前端提示用户"""
    desc = feature_schema_manager.get_column_description(schema_id)
    if not desc:
        raise HTTPException(404, f"方案不存在: {schema_id}")
    return {"code": 200, "data": desc}


@router.post("/schema")
async def create_schema(body: CreateSchemaRequest):
    features = [f.model_dump() for f in body.features]
    target = body.target.model_dump()
    brand_col = body.brand_column.model_dump()
    names = [f["name"] for f in features]
    if len(names) != len(set(names)):
        raise HTTPException(400, "特征列名不能重复")
    schema = feature_schema_manager.create_schema(
        name=body.name, features=features, target=target,
        brand_column=brand_col, description=body.description,
    )
    return {"code": 200, "data": schema, "msg": f"方案 '{body.name}' 创建成功"}


@router.put("/schema/{schema_id}")
async def update_schema(schema_id: str, body: UpdateSchemaRequest):
    kwargs = {}
    if body.name is not None:
        kwargs["name"] = body.name
    if body.description is not None:
        kwargs["description"] = body.description
    if body.features is not None:
        features = [f.model_dump() for f in body.features]
        names = [f["name"] for f in features]
        if len(names) != len(set(names)):
            raise HTTPException(400, "特征列名不能重复")
        kwargs["features"] = features
    if body.target is not None:
        kwargs["target"] = body.target.model_dump()
    if body.brand_column is not None:
        kwargs["brand_column"] = body.brand_column.model_dump()
    try:
        schema = feature_schema_manager.update_schema(schema_id, **kwargs)
    except ValueError as e:
        raise HTTPException(400, str(e))
    if not schema:
        raise HTTPException(404, f"方案不存在: {schema_id}")
    return {"code": 200, "data": schema, "msg": "更新成功"}


@router.delete("/schema/{schema_id}")
async def delete_schema(schema_id: str):
    try:
        ok = feature_schema_manager.delete_schema(schema_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    if not ok:
        raise HTTPException(404, f"方案不存在: {schema_id}")
    return {"code": 200, "msg": "删除成功"}


@router.post("/schema/{schema_id}/copy")
async def copy_schema(schema_id: str, body: CopySchemaRequest = None):
    new_name = body.new_name if body else None
    schema = feature_schema_manager.copy_schema(schema_id, new_name)
    if not schema:
        raise HTTPException(404, f"源方案不存在: {schema_id}")
    return {"code": 200, "data": schema, "msg": f"已复制为 '{schema['name']}'"}


@router.put("/schema/{schema_id}/weights")
async def update_weights(schema_id: str, body: UpdateWeightsRequest):
    schema = feature_schema_manager.get_schema(schema_id)
    if not schema:
        raise HTTPException(404, f"方案不存在: {schema_id}")
    features = schema["features"]
    for f in features:
        if f["name"] in body.weights:
            w = body.weights[f["name"]]
            if not (0.0 <= w <= 10.0):
                raise HTTPException(400, f"权重须在 0~10 之间: {f['name']}={w}")
            f["weight"] = w
    try:
        updated = feature_schema_manager.update_schema(schema_id, features=features)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"code": 200, "data": updated, "msg": "权重更新成功"}


@router.get("/schema/{schema_id}/weights")
async def get_weights(schema_id: str):
    weights = feature_schema_manager.get_weights(schema_id)
    if not weights:
        raise HTTPException(404, f"方案不存在: {schema_id}")
    return {"code": 200, "data": weights}
