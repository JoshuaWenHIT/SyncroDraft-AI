import json
import pandas as pd
from pandas import ExcelWriter
import os
from openpyxl.styles import Font

def flatten_dict(d, parent_key='', sep='_'):
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

def json_to_excel_2(json_file, excel_file):
    """将JSON文件中的diff_details转换为Excel文件"""
    # 读取JSON文件
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 提取diff_details
    diff_details = data.get('diff_details', {})

    # 处理数据
    dfs, sheet_names = process_diff_details(diff_details)

    # 写入Excel
    with ExcelWriter(excel_file, engine='openpyxl') as writer:
        for df, sheet_name in zip(dfs, sheet_names):
            # 截断过长的工作表名称（Excel限制为31个字符）
            truncated_name = sheet_name[:31]
            df.to_excel(writer, sheet_name=truncated_name, index=False)

            # 调整列宽
            worksheet = writer.sheets[truncated_name]
            for column_cells in worksheet.columns:
                length = max(len(str(cell.value)) for cell in column_cells)
                worksheet.column_dimensions[column_cells[0].column_letter].width = min(length + 2, 50)


# ========== 新增：提取核心处理逻辑为公共函数 ==========
def _process_single_json(json_file):
    """
    处理单个JSON文件，返回合并后的行数据、加粗行索引、最大列数
    复用原有json_to_excel的核心逻辑
    """
    # 读取JSON文件
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 提取diff_details
    diff_details = data.get('diff_details', {})

    # 处理数据（获取各工作表的DataFrame和名称）
    dfs, sheet_names = process_diff_details(diff_details)
    total_blocks = len(dfs)  # 新增：记录数据块总数，用于判断是否为最后一个块
    # 步骤1：计算所有sheet的最大列数（避免列错位）
    max_cols = max(len(df.columns) for df in dfs) if dfs else 0

    # 步骤2：构建合并数据（sheet名称行 + 原生列名行 + 内容行）
    merged_rows = []  # 用列表存储所有行数据（更灵活控制列数）
    bold_row_indices = []  # 记录需要加粗的行号（列名行）
    current_row = 0  # 记录当前行号（用于后续加粗）

    for idx, (df, sheet_name) in enumerate(zip(dfs, sheet_names)):  # 新增idx索引，用于判断是否加空行
        # 1. 添加sheet名称标识行（仅第一列显示名称，补全到最大列数）
        sheet_name_row = [sheet_name] + [''] * (max_cols - 1)
        merged_rows.append(sheet_name_row)
        current_row += 1

        # 2. 添加原生列名行（保留该sheet的列名，补全到最大列数）
        col_names = list(df.columns) + [''] * (max_cols - len(df.columns))
        merged_rows.append(col_names)
        bold_row_indices.append(current_row)  # 记录列名行号，后续加粗
        current_row += 1

        # 3. 添加该sheet的内容行（补全到最大列数）
        for _, row in df.iterrows():
            content_row = list(row) + [''] * (max_cols - len(df.columns))
            merged_rows.append(content_row)
            current_row += 1

        if idx < total_blocks - 1:
            empty_row = [''] * max_cols  # 全空行，列数与最大列数一致
            merged_rows.append(empty_row)
            current_row += 1  # 空行也要同步更新行号，保证加粗行索引准确

    # 转为DataFrame（列名用通用名称，不影响最终展示）
    merged_df = pd.DataFrame(merged_rows, columns=[f'列{i + 1}' for i in range(max_cols)])

    return merged_df, bold_row_indices, max_cols


# ========== 新增：处理三个JSON文件，输出含三个sheet的Excel ==========
def json_to_excel(json_file1, json_file2, json_file3, excel_file):
    """
    输入三个JSON文件路径，输出一个Excel文件（包含三个sheet，每个sheet对应一个JSON）
    每个sheet的生成逻辑与原json_to_excel完全一致
    """
    # 定义三个JSON文件的列表，方便遍历
    json_files = [json_file1, json_file2, json_file3]

    with ExcelWriter(excel_file, engine='openpyxl') as writer:
        for json_file in json_files:
            # 调用公共函数处理单个JSON
            merged_df, bold_row_indices, max_cols = _process_single_json(json_file)

            # 生成当前JSON对应的sheet名称（基于JSON文件最后一级命名）
            json_basename = os.path.basename(json_file)
            sheet_name = os.path.splitext(json_basename)[0]
            truncated_sheet_name = sheet_name[:31]  # 截断Excel限制的31字符

            # 写入当前sheet
            merged_df.to_excel(writer, sheet_name=truncated_sheet_name, index=False, header=False)

            # 获取当前sheet对象，设置格式（加粗+列宽）
            worksheet = writer.sheets[truncated_sheet_name]

            # 1. 列名行加粗
            bold_font = Font(bold=True)
            for row_idx in bold_row_indices:
                for col in range(1, max_cols + 1):
                    cell = worksheet.cell(row=row_idx + 1, column=col)
                    cell.font = bold_font

            # 2. 调整列宽
            for column_cells in worksheet.columns:
                length = max(len(str(cell.value)) if cell.value is not None else 0 for cell in column_cells)
                worksheet.column_dimensions[column_cells[0].column_letter].width = min(length + 2, 50)

# def json_to_excel(json_file, excel_file):
#     """将JSON文件中的diff_details转换为Excel文件（保留原生列名+列名行加粗+sheet名称标识）"""
#     # 读取JSON文件
#     with open(json_file, 'r', encoding='utf-8') as f:
#         data = json.load(f)
#
#     # 提取diff_details
#     diff_details = data.get('diff_details', {})
#
#     # 处理数据（获取各工作表的DataFrame和名称）
#     dfs, sheet_names = process_diff_details(diff_details)
#     total_blocks = len(dfs)  # 新增：记录数据块总数，用于判断是否为最后一个块
#     # ========== 步骤1：计算所有sheet的最大列数（避免列错位） ==========
#     max_cols = max(len(df.columns) for df in dfs) if dfs else 0
#
#     # ========== 步骤2：构建合并数据（sheet名称行 + 原生列名行 + 内容行） ==========
#     merged_rows = []  # 用列表存储所有行数据（更灵活控制列数）
#     bold_row_indices = []  # 记录需要加粗的行号（列名行）
#     current_row = 0  # 记录当前行号（用于后续加粗）
#
#     for idx, (df, sheet_name) in enumerate(zip(dfs, sheet_names)):  # 新增idx索引，用于判断是否加空行
#         # 1. 添加sheet名称标识行（仅第一列显示名称，补全到最大列数）
#         sheet_name_row = [sheet_name] + [''] * (max_cols - 1)
#         merged_rows.append(sheet_name_row)
#         current_row += 1
#
#         # 2. 添加原生列名行（保留该sheet的列名，补全到最大列数）
#         col_names = list(df.columns) + [''] * (max_cols - len(df.columns))
#         merged_rows.append(col_names)
#         bold_row_indices.append(current_row)  # 记录列名行号，后续加粗
#         current_row += 1
#
#         # 3. 添加该sheet的内容行（补全到最大列数）
#         for _, row in df.iterrows():
#             content_row = list(row) + [''] * (max_cols - len(df.columns))
#             merged_rows.append(content_row)
#             current_row += 1
#
#         if idx < total_blocks - 1:
#             empty_row = [''] * max_cols  # 全空行，列数与最大列数一致
#             merged_rows.append(empty_row)
#             current_row += 1  # 空行也要同步更新行号，保证加粗行索引准确
#
#     # 将合并后的行数据转为DataFrame（列名用通用名称，不影响最终展示）
#     merged_df = pd.DataFrame(merged_rows, columns=[f'列{i+1}' for i in range(max_cols)])
#
#     # ========== 生成新的工作表名称 ==========
#     json_basename = os.path.basename(json_file)
#     new_sheet_name = os.path.splitext(json_basename)[0]
#     truncated_sheet_name = new_sheet_name[:31]
#
#     # ========== 写入Excel并设置格式（列名行加粗+调整列宽） ==========
#     with ExcelWriter(excel_file, engine='openpyxl') as writer:
#         merged_df.to_excel(writer, sheet_name=truncated_sheet_name, index=False, header=False)
#
#         # 获取工作表对象
#         worksheet = writer.sheets[truncated_sheet_name]
#
#         # 1. 对列名行设置加粗格式（注意：Excel行号从1开始，需+1）
#         bold_font = Font(bold=True)
#         for row_idx in bold_row_indices:
#             # 遍历该行的所有列，设置加粗
#             for col in range(1, max_cols + 1):
#                 cell = worksheet.cell(row=row_idx + 1, column=col)
#                 cell.font = bold_font
#
#         # 2. 调整列宽
#         for column_cells in worksheet.columns:
#             length = max(len(str(cell.value)) if cell.value is not None else 0 for cell in column_cells)
#             worksheet.column_dimensions[column_cells[0].column_letter].width = min(length + 2, 50)

if __name__ == "__main__":
    # 输入JSON文件路径和输出Excel文件路径
    json_file_path = "compare_report.json"
    excel_file_path = "diff_details_report.xlsx"

    # 转换为Excel
    json_to_excel(json_file_path, excel_file_path)
    print(f"已成功将diff_details提取到Excel文件: {excel_file_path}")