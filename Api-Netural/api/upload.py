# api/upload.py
import uuid
import io
import csv
import logging
from collections import Counter
from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import StreamingResponse
from core.data_manager import data_manager

router = APIRouter(prefix="/upload", tags=["文件上传"])
logger = logging.getLogger("upload")

MAX_FILE_SIZE = 50 * 1024 * 1024
ALLOWED_EXTENSIONS = {".csv", ".txt", ".json", ".xlsx", ".xls"}

INPUT_DIM = 11
WINDOW_SIZE = 60
MIN_TRAIN_ROWS = WINDOW_SIZE + 10  # 70

FEATURE_COLUMNS = [
    "proc_steam_vol", "proc_air_temp",
    "input_moist", "input_moist_SP", "moist_remove",
    "out_moist_SP", "out_temp",
    "mat_flow_PV", "total_mat_flow",
    "env_temp", "env_moist"
]

TEMPLATE_COLUMNS = FEATURE_COLUMNS + ["out_moist", "brandID"]


@router.post("")
async def upload_file(file: UploadFile = File(...)):
    filename = file.filename or "unknown"
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"不支持的格式: '{ext}'")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(400, "文件超过 50MB")
    if len(content) == 0:
        raise HTTPException(400, "文件为空")

    file_id = str(uuid.uuid4())[:8]

    try:
        if ext in (".csv", ".txt"):
            data, parse_info = _parse_csv(content, filename)
        elif ext == ".json":
            data, parse_info = _parse_json(content)
        elif ext in (".xlsx", ".xls"):
            data, parse_info = _parse_excel(content)
        else:
            raise HTTPException(400, f"不支持: {ext}")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"解析异常: {filename}")
        raise HTTPException(400, f"解析失败: {str(e)}")

    if not data:
        detail = parse_info.get("reason", "未解析到有效数据")
        raise HTTPException(400, f"解析失败: {detail}。请确认文件格式正确（至少13列数值数据）。")

    ncols = len(data[0])

    if ncols < 13:
        raise HTTPException(400,
            f"数据需要至少13列（11个特征 + out_moist + brandID），当前文件有 {ncols} 列。")

    # 按 brandID 分组
    grouped_data = {}
    for row in data:
        features = row[:INPUT_DIM]
        target = row[INPUT_DIM]
        brand = int(row[INPUT_DIM + 1])
        if brand not in grouped_data:
            grouped_data[brand] = []
        grouped_data[brand].append(features + [target])

    total_rows = len(data)
    brand_count = len(grouped_data)

    # ===== 关键：检查每个品牌是否有足够数据 =====
    min_brand_rows = min(len(v) for v in grouped_data.values()) if grouped_data else 0
    if min_brand_rows < MIN_TRAIN_ROWS:
        small_brands = [str(b) for b, v in grouped_data.items() if len(v) < MIN_TRAIN_ROWS]
        raise HTTPException(400,
            f"品牌 {','.join(small_brands)} 数据不足 {MIN_TRAIN_ROWS} 行（最少需要 {MIN_TRAIN_ROWS} 行才能训练）。"
            f"当前最小品牌只有 {min_brand_rows} 行。")

    data_manager.add_file(file_id, data, {
        "filename": filename,
        "num_cols": ncols,
        "num_rows": total_rows,
        "file_size": len(content),
        "columns": TEMPLATE_COLUMNS[:ncols] if ncols <= len(TEMPLATE_COLUMNS) else [f"col_{i+1}" for i in range(ncols)],
        "brand_count": brand_count,
        "brands": sorted(grouped_data.keys()),
        "grouped_data": grouped_data,
        "parse_info": parse_info
    })

    return {
        "code": 200, "msg": "上传成功", "file_id": file_id,
        "filename": filename, "num_rows": total_rows, "num_cols": ncols,
        "brand_count": brand_count, "brands": sorted(grouped_data.keys())
    }


def _parse_csv(content: bytes, filename: str):
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
    skip = 0
    try:
        [float(v) for v in first_parts]
    except (ValueError, TypeError):
        skip = 1

    # 收集所有行，只保留能全部转成 float 且列数 >= 13 的行
    parsed_rows = []
    skipped_reasons = {"non_numeric": 0, "too_few_cols": 0}
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
        if len(row) < 13:
            skipped_reasons["too_few_cols"] += 1
            continue
        parsed_rows.append(row)

    if not parsed_rows:
        reason = (f"所有 {len(lines) - skip} 行数据均被过滤。"
                  f"原因: {skipped_reasons['non_numeric']} 行含非数值, "
                  f"{skipped_reasons['too_few_cols']} 行列数不足13列。"
                  f"请确认文件格式（表头+数据，每行13列纯数值）。")
        return [], {"reason": reason}

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
        "skipped": skipped_reasons
    }
    logger.info(f"文件 {filename}: {len(data)} 行, {best_ncols} 列, 编码={used_encoding}")
    return data, info


def _parse_json(content: bytes):
    import json
    for enc in ("utf-8-sig", "gbk", "latin-1"):
        try:
            text = content.decode(enc)
            break
        except Exception:
            continue
    else:
        raise HTTPException(400, "JSON 编码无法识别")

    try:
        obj = json.loads(text)
    except json.JSONDecodeError as e:
        raise HTTPException(400, f"JSON 格式错误: {e}")

    arr = obj.get("data", obj) if isinstance(obj, dict) else obj
    if not isinstance(arr, list) or not arr:
        raise HTTPException(400, "JSON 需要非空数组")

    data = []
    for row in arr:
        try:
            if isinstance(row, dict):
                data.append([float(v) for v in row.values()])
            elif isinstance(row, (list, tuple)):
                data.append([float(v) for v in row])
        except (ValueError, TypeError):
            continue

    if not data:
        return [], {"reason": "JSON 中无有效数值行"}
    return data, {"valid_rows": len(data)}


def _parse_excel(content: bytes):
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
        if ok and len(r) >= 13:
            data.append(r)
        else:
            skipped += 1

    if not data:
        return [], {"reason": f"Excel 中无有效数据行（共 {len(df)} 行, 跳过 {skipped} 行, 有效 0 行）。请确保至少13列数值。"}
    return data, {"valid_rows": len(data), "skipped": skipped}


# ========== 下载模板 ==========
@router.get("/template")
async def download_template(format: str = Query("csv")):
    header = TEMPLATE_COLUMNS

    sample_rows = [
        [300.0, 203.0, 0.26, 20.0, 0.0, 14.5, 41.5, 0.0, 8767.1, 28.2, 40.6, 0.0, 13102002],
        [299.5, 202.8, 0.28, 20.0, 0.0, 14.5, 41.3, 4550.0, 8767.1, 28.2, 40.7, 0.0, 13102002],
        [299.0, 202.5, 0.30, 20.0, 0.0, 14.5, 41.1, 4550.0, 8767.1, 28.3, 40.7, 0.0, 13102002],
        [298.5, 202.2, 0.32, 20.0, 0.0, 14.5, 40.9, 4550.0, 8767.1, 28.3, 40.8, 0.0, 13102003],
        [298.0, 202.0, 0.34, 20.0, 0.0, 14.5, 40.7, 4550.0, 8767.1, 28.4, 40.8, 0.0, 13102003],
    ]

    if format == "xlsx":
        try:
            import pandas as pd

            # ===== 核心修复：直接写 BytesIO，不用临时文件 =====
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

    # CSV 模板
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(header)
    for row in sample_rows:
        writer.writerow(row)
    csv_bytes = output.getvalue().encode("utf-8-sig")
    return StreamingResponse(
        io.BytesIO(csv_bytes),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=upload_template.csv"}
    )


@router.get("/list")
async def list_files():
    return {"code": 200, "data": data_manager.list_files()}


@router.get("/preview/{file_id}")
async def preview_file(file_id: str):
    f = data_manager.get_file(file_id)
    if not f:
        raise HTTPException(404, "文件不存在")
    return {
        "code": 200,
        "data": f["data"][:20],
        "metadata": f["metadata"],
        "brands": f["metadata"].get("brands", [])
    }


@router.delete("/{file_id}")
async def delete_file(file_id: str):
    if not data_manager.get_file(file_id):
        raise HTTPException(404, "文件不存在")
    data_manager.remove_file(file_id)
    return {"code": 200, "msg": "删除成功"}
