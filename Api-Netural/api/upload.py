# api/upload.py
"""
文件上传 API — 支持自定义特征列 + 智能列映射（基于特征方案 schema）
"""
import uuid
import io
import csv
import json as _json
import logging
from collections import Counter
from typing import Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from core.data_manager import data_manager
from core.feature_schema import feature_schema_manager

router = APIRouter(prefix="/upload", tags=["文件上传"])
logger = logging.getLogger("upload")

MAX_FILE_SIZE = 50 * 1024 * 1024
ALLOWED_EXTENSIONS = {".csv", ".txt", ".json", ".xlsx", ".xls"}


# ===================== 列映射相关模型 =====================

class ColumnMappingRequest(BaseModel):
    """列映射请求：将文件列映射到 schema 角色"""
    # key = 文件列索引(0-based) 或 列名, value = schema角色
    # 角色格式: "feature:{feature_name}", "target", "brand"
    mappings: dict = Field(..., description="列映射关系 {文件列索引或列名: schema角色}")


# ===================== 列映射辅助函数 =====================

def _auto_detect_mapping(headers: list, schema: dict) -> dict:
    """
    自动检测列映射：用表头名称匹配 schema 中的特征名、目标名、品牌名。
    返回 {文件列索引: schema角色} 的映射关系。
    """
    feature_names = [f["name"] for f in schema["features"]]
    target_name = schema["target"]["name"]
    brand_name = schema["brand_column"]["name"]

    # 构建所有可能的列名匹配（不区分大小写，支持中英文标签）
    all_roles = {}
    for fname in feature_names:
        all_roles[fname.lower()] = f"feature:{fname}"
    all_roles[target_name.lower()] = "target"
    all_roles[brand_name.lower()] = "brand"

    # 也用中文标签匹配
    for f in schema["features"]:
        if f.get("label"):
            all_roles[f["label"]] = f"feature:{f['name']}"
    if schema["target"].get("label"):
        all_roles[schema["target"]["label"]] = "target"
    if schema["brand_column"].get("label"):
        all_roles[schema["brand_column"]["label"]] = "brand"

    mapping = {}
    matched_features = set()

    for idx, header in enumerate(headers):
        h = header.strip()
        # 精确匹配（不区分大小写）
        role = all_roles.get(h.lower()) or all_roles.get(h)
        if role:
            mapping[idx] = role
            if role.startswith("feature:"):
                matched_features.add(role.split(":", 1)[1])

    # 计算匹配率
    total_needed = len(feature_names) + 2  # features + target + brand
    matched_count = len(matched_features) + (1 if "target" in mapping.values() else 0) + (1 if "brand" in mapping.values() else 0)

    return {
        "mapping": mapping,
        "matched_count": matched_count,
        "total_needed": total_needed,
        "auto_ok": matched_count == total_needed,
    }


def _apply_column_mapping(data: list, headers: list, mapping: dict, schema: dict) -> list:
    """
    按照列映射关系重排数据。
    mapping: {文件列索引(0-based): "feature:{name}" | "target" | "brand"}
    返回重排后的数据行：[feature1, feature2, ..., target, brand]
    """
    feature_names = [f["name"] for f in schema["features"]]
    target_name = schema["target"]["name"]
    brand_name = schema["brand_column"]["name"]

    # 构建目标列顺序
    target_order = []
    for fname in feature_names:
        target_order.append(f"feature:{fname}")
    target_order.append("target")
    target_order.append("brand")

    # 反转 mapping: role -> file_col_index
    role_to_col = {}
    for col_idx, role in mapping.items():
        role_to_col[role] = int(col_idx) if isinstance(col_idx, (int, str)) and str(col_idx).isdigit() else col_idx

    # 如果映射用的是列名，转为索引
    for col_idx, role in mapping.items():
        if isinstance(col_idx, str) and not col_idx.isdigit():
            # 按列名查找索引
            for i, h in enumerate(headers):
                if h.strip() == col_idx.strip():
                    role_to_col[role] = i
                    break

    # 重排每一行
    reordered = []
    for row in data:
        new_row = []
        for role in target_order:
            col_idx = role_to_col.get(role)
            if col_idx is not None and 0 <= col_idx < len(row):
                new_row.append(row[col_idx])
            else:
                new_row.append(0.0)  # 缺失列填 0
        reordered.append(new_row)

    return reordered


def _reorder_data_by_mapping(data: list, mapping: dict, schema: dict) -> list:
    """
    根据映射关系重排数据到 schema 标准顺序。
    mapping key 为整数索引，value 为 "feature:xxx" | "target" | "brand"
    """
    feature_names = [f["name"] for f in schema["features"]]
    target_name = schema["target"]["name"]
    brand_name = schema["brand_column"]["name"]

    # 标准顺序
    standard_order = [f"feature:{fn}" for fn in feature_names] + ["target", "brand"]

    # role -> file column index
    role_to_idx = {}
    for idx_str, role in mapping.items():
        idx = int(idx_str) if isinstance(idx_str, str) else idx_str
        role_to_idx[role] = idx

    reordered = []
    for row in data:
        new_row = []
        for role in standard_order:
            src_idx = role_to_idx.get(role)
            if src_idx is not None and src_idx < len(row):
                new_row.append(row[src_idx])
            else:
                new_row.append(0.0)
        reordered.append(new_row)
    return reordered


# ===================== 解析文件表头 =====================

@router.post("/parse-header")
async def parse_file_header(
    file: UploadFile = File(...),
    schema_id: str = Query("default", description="特征方案ID")
):
    """
    解析上传文件的表头列名，自动匹配 schema 角色，返回映射建议。
    前端拿到后展示列映射 UI，用户确认后再调用 /upload 接口上传。
    """
    filename = file.filename or "unknown"
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"不支持的格式: '{ext}'")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(400, "文件超过 50MB")
    if len(content) == 0:
        raise HTTPException(400, "文件为空")

    schema = feature_schema_manager.get_schema(schema_id)
    if not schema:
        raise HTTPException(400, f"特征方案不存在: {schema_id}")

    feature_names = [f["name"] for f in schema["features"]]
    feature_labels = {f["name"]: f.get("label", "") for f in schema["features"]}
    target_name = schema["target"]["name"]
    target_label = schema["target"].get("label", "")
    brand_name = schema["brand_column"]["name"]
    brand_label = schema["brand_column"].get("label", "")

    headers = []
    total_rows = 0

    try:
        if ext in (".csv", ".txt"):
            text = None
            for enc in ("utf-8-sig", "gbk", "gb2312", "latin-1"):
                try:
                    text = content.decode(enc)
                    break
                except Exception:
                    continue
            if text is None:
                raise HTTPException(400, "编码无法识别")

            lines = [l.strip() for l in text.strip().replace("\r\n", "\n").split("\n") if l.strip()]
            if not lines:
                raise HTTPException(400, "文件为空")

            # 检测分隔符
            sep = ","
            if "\t" in lines[0]:
                sep = "\t"
            elif ";" in lines[0] and lines[0].count(";") > lines[0].count(","):
                sep = ";"

            headers = [v.strip() for v in lines[0].split(sep)]
            total_rows = len(lines) - 1

        elif ext in (".xlsx", ".xls"):
            try:
                import pandas as pd
                df = pd.read_excel(io.BytesIO(content), nrows=0)
                headers = list(df.columns.astype(str))
                # 获取总行数
                df_full = pd.read_excel(io.BytesIO(content))
                total_rows = len(df_full)
            except ImportError:
                raise HTTPException(500, "服务器未安装 pandas/openpyxl")

        elif ext == ".json":
            for enc in ("utf-8-sig", "gbk", "latin-1"):
                try:
                    text = content.decode(enc)
                    break
                except Exception:
                    continue
            obj = _json.loads(text)
            arr = obj.get("data", obj) if isinstance(obj, dict) else obj
            if isinstance(arr, list) and arr:
                if isinstance(arr[0], dict):
                    headers = list(arr[0].keys())
                elif isinstance(arr[0], (list, tuple)):
                    headers = [f"col_{i+1}" for i in range(len(arr[0]))]
            total_rows = len(arr) if isinstance(arr, list) else 0

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(400, f"解析表头失败: {str(e)}")

    if not headers:
        raise HTTPException(400, "无法读取文件列名")

    # 自动检测映射
    auto_result = _auto_detect_mapping(headers, schema)

    # 构建 schema 需求描述
    schema_requirements = {
        "features": [{"name": f["name"], "label": f.get("label", "")} for f in schema["features"]],
        "target": {"name": target_name, "label": target_label},
        "brand": {"name": brand_name, "label": brand_label},
    }

    return {
        "code": 200,
        "data": {
            "filename": filename,
            "file_headers": headers,
            "total_rows": total_rows,
            "schema_id": schema_id,
            "schema_name": schema["name"],
            "schema_requirements": schema_requirements,
            "auto_mapping": auto_result["mapping"],
            "matched_count": auto_result["matched_count"],
            "total_needed": auto_result["total_needed"],
            "auto_ok": auto_result["auto_ok"],
        }
    }


# ===================== 上传（支持列映射） =====================

@router.post("")
async def upload_file(
    file: UploadFile = File(...),
    schema_id: str = Query("default", description="特征方案ID"),
    column_mapping: str = Query("", description="列映射JSON，为空则按传统顺序解析")
):
    """上传训练数据文件，支持智能列映射或传统顺序解析"""
    filename = file.filename or "unknown"
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"不支持的格式: '{ext}'")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(400, "文件超过 50MB")
    if len(content) == 0:
        raise HTTPException(400, "文件为空")

    # ===== 获取特征方案 =====
    schema = feature_schema_manager.get_schema(schema_id)
    if not schema:
        raise HTTPException(400, f"特征方案不存在: {schema_id}")

    input_dim = len(schema["features"])
    target_name = schema["target"]["name"]
    brand_name = schema["brand_column"]["name"]
    feature_names = [f["name"] for f in schema["features"]]
    min_required_cols = input_dim + 2  # 特征 + 目标 + 品牌
    template_columns = feature_names + [target_name, brand_name]

    # 解析列映射参数
    parsed_mapping = None
    if column_mapping:
        try:
            parsed_mapping = _json.loads(column_mapping)
        except Exception:
            raise HTTPException(400, "column_mapping 参数格式错误，需要 JSON")

    file_id = str(uuid.uuid4())[:8]

    # ===== 解析文件 =====
    try:
        if ext in (".csv", ".txt"):
            data, parse_info, headers = _parse_csv_with_headers(content, filename)
        elif ext == ".json":
            data, parse_info, headers = _parse_json_with_headers(content)
        elif ext in (".xlsx", ".xls"):
            data, parse_info, headers = _parse_excel_with_headers(content)
        else:
            raise HTTPException(400, f"不支持: {ext}")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"解析异常: {filename}")
        raise HTTPException(400, f"解析失败: {str(e)}")

    if not data:
        detail = parse_info.get("reason", "未解析到有效数据")
        raise HTTPException(400, f"解析失败: {detail}")

    ncols = len(data[0])

    # ===== 应用列映射 =====
    if parsed_mapping:
        # 校验映射：确保所有必需角色都有映射
        mapped_roles = set(parsed_mapping.values())
        missing = []
        for fname in feature_names:
            if f"feature:{fname}" not in mapped_roles:
                missing.append(f"特征 {fname}")
        if "target" not in mapped_roles:
            missing.append(f"目标列 {target_name}")
        if "brand" not in mapped_roles:
            missing.append(f"品牌列 {brand_name}")
        if missing:
            raise HTTPException(400, f"列映射不完整，缺少: {', '.join(missing)}")

        # 校验映射的列索引在范围内
        for col_idx_str, role in parsed_mapping.items():
            col_idx = int(col_idx_str)
            if col_idx < 0 or col_idx >= ncols:
                raise HTTPException(400, f"列索引 {col_idx} 超出范围（文件共 {ncols} 列）")

        data = _reorder_data_by_mapping(data, parsed_mapping, schema)
        parse_info["column_mapping"] = parsed_mapping
        parse_info["mapping_applied"] = True
        logger.info(f"文件 {filename}: 应用列映射 {parsed_mapping}")
    else:
        # 传统模式：按位置顺序
        if ncols < min_required_cols:
            raise HTTPException(400,
                f"数据需要至少 {min_required_cols} 列（{input_dim} 个特征 + {target_name} + {brand_name}），"
                f"当前文件有 {ncols} 列。请使用列映射功能或调整文件列顺序。")

    # ===== 按 brandID 分组 =====
    grouped_data = {}
    for row in data:
        features = row[:input_dim]
        target = row[input_dim]
        brand = int(row[input_dim + 1])
        if brand not in grouped_data:
            grouped_data[brand] = []
        grouped_data[brand].append(features + [target])

    total_rows = len(data)
    brand_count = len(grouped_data)

    # 检查每个品牌是否有足够数据
    min_brand_rows = min(len(v) for v in grouped_data.values()) if grouped_data else 0
    min_train_rows = 70  # window_size(60) + 10
    if min_brand_rows < min_train_rows:
        small_brands = [str(b) for b, v in grouped_data.items() if len(v) < min_train_rows]
        raise HTTPException(400,
            f"品牌 {','.join(small_brands)} 数据不足 {min_train_rows} 行"
            f"（最少需要 {min_train_rows} 行才能训练）。"
            f"当前最小品牌只有 {min_brand_rows} 行。")

    data_manager.add_file(file_id, data, {
        "filename": filename,
        "num_cols": ncols,
        "num_rows": total_rows,
        "file_size": len(content),
        "columns": template_columns,
        "brand_count": brand_count,
        "brands": sorted(grouped_data.keys()),
        "grouped_data": grouped_data,
        "parse_info": parse_info,
        "schema_id": schema_id,
        "input_dim": input_dim,
        "feature_names": feature_names,
    })

    return {
        "code": 200, "msg": "上传成功", "file_id": file_id,
        "filename": filename, "num_rows": total_rows, "num_cols": ncols,
        "brand_count": brand_count, "brands": sorted(grouped_data.keys()),
        "schema_id": schema_id, "feature_names": feature_names,
        "input_dim": input_dim,
        "mapping_applied": parsed_mapping is not None,
    }


# ========== 文件列表 ==========
@router.get("/list")
async def list_uploaded_files():
    """列出所有已上传的文件"""
    files = data_manager.list_files()
    return {"code": 200, "data": files}


# ========== 删除文件 ==========
@router.delete("/{file_id}")
async def delete_file(file_id: str):
    f = data_manager.get_file(file_id)
    if not f:
        raise HTTPException(404, f"文件不存在: {file_id}")
    data_manager.remove_file(file_id)
    return {"code": 200, "msg": "删除成功"}


# ========== 预览 ==========
@router.get("/preview/{file_id}")
async def preview_file(file_id: str, limit: int = Query(10, ge=1, le=100)):
    f = data_manager.get_file(file_id)
    if not f:
        raise HTTPException(404, f"文件不存在: {file_id}")
    data = f["data"][:limit]
    meta = f["metadata"]
    columns = meta.get("columns", [f"col_{i+1}" for i in range(len(data[0]) if data else 0)])
    return {
        "code": 200,
        "columns": columns,
        "rows": data,
        "total": len(f["data"]),
        "schema_id": meta.get("schema_id", "default"),
        "feature_names": meta.get("feature_names", []),
    }


# ========== 下载模板 ==========
@router.get("/template")
async def download_template(
    format: str = Query("csv"),
    schema_id: str = Query("default", description="特征方案ID")
):
    """根据特征方案生成对应列结构的模板"""
    schema = feature_schema_manager.get_schema(schema_id)
    if not schema:
        schema = feature_schema_manager.get_schema("default")

    feature_names = [f["name"] for f in schema["features"]]
    target_name = schema["target"]["name"]
    brand_name = schema["brand_column"]["name"]
    header = feature_names + [target_name, brand_name]

    # 生成示例行（用默认值填充）
    default_values = [300.0, 203.0, 0.26, 20.0, 0.0, 14.5, 41.5, 0.0, 8767.1, 28.2, 40.6]
    sample_features = []
    for i in range(len(feature_names)):
        if i < len(default_values):
            sample_features.append(default_values[i])
        else:
            sample_features.append(0.0)

    sample_rows = [
        sample_features + [0.0, 13102002],
        sample_features + [0.1, 13102002],
        sample_features + [0.2, 13102003],
    ]

    if format == "xlsx":
        try:
            import pandas as pd
            df = pd.DataFrame(sample_rows, columns=header)
            buf = io.BytesIO()
            df.to_excel(buf, index=False, engine="openpyxl")
            buf.seek(0)
            return StreamingResponse(
                buf,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": "attachment; filename=upload_template.xlsx"}
            )
        except ImportError:
            raise HTTPException(500, "服务器未安装 openpyxl，请执行: pip install openpyxl")
        except Exception as e:
            raise HTTPException(500, f"生成 Excel 模板失败: {e}")
    else:
        # CSV
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(header)
        for row in sample_rows:
            writer.writerow(row)
        buf.seek(0)
        return StreamingResponse(
            io.BytesIO(buf.getvalue().encode("utf-8-sig")),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=upload_template.csv"}
        )


# ========== 解析函数 ==========

def _parse_csv_with_headers(content: bytes, filename: str):
    """解析 CSV，返回 (data, info, headers)。不做列数校验，交给调用方处理。"""
    text = None
    used_encoding = None
    for enc in ("utf-8-sig", "gbk", "gb2312", "latin-1"):
        try:
            text = content.decode(enc)
            used_encoding = enc
            break
        except Exception:
            continue
    if text is None:
        raise HTTPException(400, "编码无法识别，请用 UTF-8 保存")

    lines = [l.strip() for l in text.strip().replace("\r\n", "\n").split("\n") if l.strip()]
    if len(lines) < 2:
        raise HTTPException(400, "文件至少需要表头 + 一行数据")

    # 检测分隔符
    sep = ","
    if "\t" in lines[0]:
        sep = "\t"
    elif ";" in lines[0] and lines[0].count(";") > lines[0].count(","):
        sep = ";"

    # 第一行是否为表头
    first_parts = [v.strip() for v in lines[0].split(sep)]
    headers = []
    skip = 0
    try:
        [float(v) for v in first_parts]
    except (ValueError, TypeError):
        skip = 1
        headers = first_parts

    parsed_rows = []
    skipped_reasons = {"non_numeric": 0}
    for line in lines[skip:]:
        parts = [v.strip() for v in line.split(sep)]
        row = []
        has_non_numeric = False
        for v in parts:
            try:
                row.append(float(v))
            except (ValueError, TypeError):
                has_non_numeric = True
                break
        if has_non_numeric:
            skipped_reasons["non_numeric"] += 1
            continue
        parsed_rows.append(row)

    if not parsed_rows:
        reason = (f"所有 {len(lines) - skip} 行数据均被过滤。"
                  f"原因: {skipped_reasons['non_numeric']} 行含非数值。"
                  f"请确认文件数据行全部为数值。")
        return [], {"reason": reason}, headers

    col_counts = Counter(len(r) for r in parsed_rows)
    best_ncols = col_counts.most_common(1)[0][0]
    data = [r for r in parsed_rows if len(r) == best_ncols]

    info = {
        "encoding": used_encoding,
        "separator": sep,
        "skipped_header": skip == 1,
        "total_lines": len(lines) - skip,
        "valid_rows": len(data),
        "columns": best_ncols,
        "skipped": skipped_reasons,
    }
    logger.info(f"文件 {filename}: {len(data)} 行, {best_ncols} 列, 编码={used_encoding}")
    return data, info, headers


def _parse_json_with_headers(content: bytes):
    """解析 JSON，返回 (data, info, headers)"""
    for enc in ("utf-8-sig", "gbk", "latin-1"):
        try:
            text = content.decode(enc)
            break
        except Exception:
            continue
    else:
        raise HTTPException(400, "JSON 编码无法识别")

    try:
        obj = _json.loads(text)
    except _json.JSONDecodeError as e:
        raise HTTPException(400, f"JSON 格式错误: {e}")

    arr = obj.get("data", obj) if isinstance(obj, dict) else obj
    if not isinstance(arr, list) or not arr:
        raise HTTPException(400, "JSON 需要非空数组")

    headers = []
    data = []
    for row in arr:
        try:
            if isinstance(row, dict):
                if not headers:
                    headers = list(row.keys())
                data.append([float(v) for v in row.values()])
            elif isinstance(row, (list, tuple)):
                data.append([float(v) for v in row])
        except (ValueError, TypeError):
            continue

    if not data:
        return [], {"reason": "JSON 中无有效数值行"}, headers
    return data, {"valid_rows": len(data)}, headers


def _parse_excel_with_headers(content: bytes):
    """解析 Excel，返回 (data, info, headers)"""
    try:
        import pandas as pd
    except ImportError:
        raise HTTPException(500, "服务器未安装 pandas，请执行: pip install pandas openpyxl")

    try:
        df = pd.read_excel(io.BytesIO(content))
    except Exception as e:
        raise HTTPException(400, f"Excel 读取失败: {e}")

    if df.empty:
        raise HTTPException(400, "Excel 为空")

    headers = list(df.columns.astype(str))
    data = []
    skipped = 0
    for _, row in df.iterrows():
        r = []
        ok = True
        for v in row.values:
            try:
                r.append(float(v))
            except (ValueError, TypeError):
                ok = False
                break
        if ok:
            data.append(r)
        else:
            skipped += 1

    if not data:
        return [], {"reason": f"Excel 中无有效数据行（共 {len(df)} 行, 跳过 {skipped} 行）。"}, headers
    return data, {"valid_rows": len(data), "skipped": skipped}, headers
