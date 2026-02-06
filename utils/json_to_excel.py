import json
import pandas as pd
from pandas import ExcelWriter


def flatten_dict(d, parent_key="", sep="_"):
    """将嵌套字典扁平化为单层字典"""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def process_diff_details(diff_details):
    """处理diff_details中的各个部分并转换为DataFrame列表"""
    dfs = []
    sheet_names = []

    for key, items in diff_details.items():
        if not items:  # 跳过空列表
            continue

        sheet_names.append(key)
        processed_items = []

        for item in items:
            # 扁平化每个项目
            flat_item = flatten_dict(item)
            processed_items.append(flat_item)

        # 创建DataFrame
        df = pd.DataFrame(processed_items)
        dfs.append(df)

    return dfs, sheet_names


def json_to_excel(json_file, excel_file):
    """将JSON文件中的diff_details转换为Excel文件"""
    # 读取JSON文件
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 提取diff_details
    diff_details = data.get("diff_details", {})

    # 处理数据
    dfs, sheet_names = process_diff_details(diff_details)

    # 写入Excel
    with ExcelWriter(excel_file, engine="openpyxl") as writer:
        for df, sheet_name in zip(dfs, sheet_names):
            # 截断过长的工作表名称（Excel限制为31个字符）
            truncated_name = sheet_name[:31]
            df.to_excel(writer, sheet_name=truncated_name, index=False)

            # 调整列宽
            worksheet = writer.sheets[truncated_name]
            for column_cells in worksheet.columns:
                length = max(len(str(cell.value)) for cell in column_cells)
                worksheet.column_dimensions[column_cells[0].column_letter].width = min(
                    length + 2, 50
                )


if __name__ == "__main__":
    # 输入JSON文件路径和输出Excel文件路径
    json_file_path = "compare_report.json"
    excel_file_path = "diff_details_report.xlsx"

    # 转换为Excel
    json_to_excel(json_file_path, excel_file_path)
    print(f"已成功将diff_details提取到Excel文件: {excel_file_path}")
