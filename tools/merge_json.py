# import json
# from typing import List, Optional
#
#
# def merge_json_files(
#         input_files: List[str],
#         output_file: str,
#         encoding: str = "utf-8",
#         indent: int = 4,
#         deduplicate: bool = False,
#         unique_key: Optional[str] = None
# ) -> None:
#     """
#     合并多个JSON文件（每个文件内容为字典列表）为一个JSON文件
#
#     参数:
#         input_files: 输入JSON文件路径列表（如 ["file1.json", "file2.json"]）
#         output_file: 输出合并后JSON文件的路径
#         encoding: 文件读写编码，默认utf-8
#         indent: JSON输出缩进，默认4（增强可读性）
#         deduplicate: 是否对字典去重，默认False
#         unique_key: 去重的唯一标识键（如"id"），若为None则按字典完整内容去重；
#                     仅当deduplicate=True时生效
#
#     异常:
#         FileNotFoundError: 输入文件不存在
#         json.JSONDecodeError: 文件不是合法的JSON格式
#         TypeError: JSON内容不是字典列表
#     """
#     # 初始化合并后的列表
#     merged_data = []
#
#     # 遍历所有输入文件
#     for file_path in input_files:
#         try:
#             # 读取并解析JSON文件
#             with open(file_path, "r", encoding=encoding) as f:
#                 try:
#                     file_data = json.load(f)
#                 except json.JSONDecodeError as e:
#                     raise json.JSONDecodeError(
#                         f"文件 {file_path} 不是合法的JSON格式: {str(e)}",
#                         e.doc, e.pos
#                     ) from e
#
#             # 验证数据类型（必须是字典列表）
#             if not isinstance(file_data, list):
#                 raise TypeError(f"文件 {file_path} 的内容不是列表（要求字典列表）")
#
#             for item in file_data:
#                 if not isinstance(item, dict):
#                     raise TypeError(
#                         f"文件 {file_path} 中包含非字典元素: {item}（要求字典列表）"
#                     )
#
#             # 将当前文件的字典列表加入合并列表
#             merged_data.extend(file_data)
#             print(f"成功读取文件: {file_path} (包含 {len(file_data)} 条数据)")
#
#         except FileNotFoundError:
#             raise FileNotFoundError(f"输入文件不存在: {file_path}")
#         except Exception as e:
#             raise Exception(f"处理文件 {file_path} 时出错: {str(e)}") from e
#
#     # 去重处理（如果开启）
#     if deduplicate and merged_data:
#         if unique_key:
#             # 按指定唯一键去重（保留首次出现的元素）
#             seen_keys = set()
#             deduplicated_data = []
#             for item in merged_data:
#                 # 检查唯一键是否存在
#                 if unique_key not in item:
#                     raise KeyError(
#                         f"字典中缺少指定的唯一键 '{unique_key}': {item}"
#                     )
#                 key_value = item[unique_key]
#                 if key_value not in seen_keys:
#                     seen_keys.add(key_value)
#                     deduplicated_data.append(item)
#         else:
#             # 按字典完整内容去重（将字典转为有序元组作为标识）
#             seen_items = set()
#             deduplicated_data = []
#             for item in merged_data:
#                 # 将字典转为排序后的键值对元组（保证无序字典的唯一性）
#                 item_tuple = tuple(sorted(item.items()))
#                 if item_tuple not in seen_items:
#                     seen_items.add(item_tuple)
#                     deduplicated_data.append(item)
#
#         merged_data = deduplicated_data
#         print(f"去重后剩余数据条数: {len(merged_data)}")
#
#     # 写入合并后的JSON文件
#     try:
#         with open(output_file, "w", encoding=encoding) as f:
#             json.dump(merged_data, f, ensure_ascii=False, indent=indent)
#         print(f"\n合并完成！输出文件: {output_file}")
#         print(f"总计合并数据条数: {len(merged_data)}")
#     except Exception as e:
#         raise Exception(f"写入输出文件 {output_file} 时出错: {str(e)}") from e
#
#
# # ------------------- 示例用法 -------------------
# if __name__ == "__main__":
#     # 1. 基础用法（仅合并，不去重）
#     input_files_2 = [
#         "../test_process/json_results/736420000_sd_view_1_a_result.json",
#         "../test_process/json_results/736420000_sd_view_3_section_result.json",
#         "../test_process/json_results/736420000_sd_view_4_c_result.json",
#         "../test_process/json_results/736420000_sd_view_5_b_result.json"
#     ]
#     input_files_1 = [
#         "../test_process/json_results/736420000_sd_revision_view_1_a_result.json",
#         "../test_process/json_results/736420000_sd_revision_view_3_section_result.json",
#         "../test_process/json_results/736420000_sd_revision_view_4_c_result.json",
#         "../test_process/json_results/736420000_sd_revision_view_5_b_result.json"
#     ]
#     output_file_1 = "../test_process/json_results/merged_json_X.json"
#     output_file_2 = "../test_process/json_results/merged_json_Y.json"
#     try:
#         merge_json_files(
#             input_files=input_files_1,
#             output_file=output_file_1,
#             encoding="utf-8",
#             indent=4
#         )
#         merge_json_files(
#             input_files=input_files_2,
#             output_file=output_file_2,
#             encoding="utf-8",
#             indent=4
#         )
#     except Exception as e:
#         print(f"合并失败: {str(e)}")
#
#     # 2. 带去重的用法（按唯一键id去重）
#     # merge_json_files(
#     #     input_files=input_files,
#     #     output_file="merged_data_deduplicated.json",
#     #     deduplicate=True,
#     #     unique_key="id"
#     # )
#
#     # 3. 按字典完整内容去重
#     # merge_json_files(
#     #     input_files=input_files,
#     #     output_file="merged_data_full_deduplicated.json",
#     #     deduplicate=True
#     # )

import os
import json
import hashlib

def raw_str_hash(content):
    return hashlib.md5(content.encode('utf-8')).hexdigest()

def merge_json_files(file_list):
    """
    合并多个JSON文件的内容
    - 数组：拼接所有元素
    - 字典：合并键值对（后读入的文件覆盖同名键）
    - 类型不匹配时抛出异常
    """
    if not file_list:
        return {}
    # print("------------------------------------")
    # print(file_list)
    # print("------------------------------------")
    merged_data = None
    for file_path in file_list:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            raise ValueError(f"读取文件{file_path}失败：{str(e)}")

        if merged_data is None:
            merged_data = data
        else:
            if isinstance(merged_data, list) and isinstance(data, list):
                merged_data.extend(data)
            elif isinstance(merged_data, dict) and isinstance(data, dict):
                merged_data.update(data)
            else:
                raise TypeError(
                    f"文件{file_path}的JSON类型（{type(data)}）与已合并内容类型（{type(merged_data)}）不匹配，无法合并"
                )
    return merged_data


def get_common_prefix(image_prefix, file_list):
    """从文件名列表中提取公共前缀（如736420000_sd）"""
    if not file_list:
        return "merged"

    # 取第一个文件作为基准，分割出公共前缀
    first_file = file_list[0]
    if '_revision_' in first_file:
        # 带revision的文件：按_revision_分割取前半部分
        prefix = first_file.split('_revision_')[0]
    else:
        # 不带revision的文件：按_view_分割取前半部分
        prefix = first_file.split('_view_')[0]
    return prefix


def merge_main(image_prefix, json_results_path):
    # 初始化两个列表，分别存储带/不带revision的JSON文件
    revision_1_files = []
    revision_2_files = []
    normal_files = []

    # 遍历当前目录的文件，分类存储
    for filename in os.listdir(json_results_path):
        if not filename.endswith('.json'):
            continue  # 只处理JSON文件

        if '_revision_1' in filename and image_prefix in filename:
            revision_1_files.append(os.path.join(json_results_path, filename))
        elif '_revision_2' in filename and image_prefix in filename:
            revision_2_files.append(os.path.join(json_results_path, filename))
        elif '_merged_' not in filename and '_revision_' not in filename and 'compare_' not in filename and image_prefix in filename:
            normal_files.append(os.path.join(json_results_path, filename))

    # 提取公共前缀（优先从带revision的文件提取，若无则从普通文件提取）
    common_prefix = get_common_prefix(image_prefix, revision_1_files if revision_1_files else normal_files)

    # 合并带revision_1的文件，输出Y后缀
    if revision_1_files:
        merged_revision = merge_json_files(revision_1_files)
        merged_revision_1 = sorted(merged_revision, key=lambda x: x["content"], reverse=True)
        output_y = f"{common_prefix}_merged_Y.json"
        with open(output_y, 'w', encoding='utf-8') as f:
            json.dump(merged_revision_1, f, ensure_ascii=False, indent=2)
        print(f"✅ 已合并带revision_1的文件：{output_y}")
        print(f"   源文件：{', '.join(revision_1_files)}")

    # 合并带revision_2的文件，输出Y后缀
    if revision_2_files:
        merged_revision = merge_json_files(revision_2_files)
        merged_revision_2 = sorted(merged_revision, key=lambda x: x["content"], reverse=True)
        output_y = f"{common_prefix}_merged_Z.json"
        with open(output_y, 'w', encoding='utf-8') as f:
            json.dump(merged_revision_2, f, ensure_ascii=False, indent=2)
        print(f"✅ 已合并带revision_2的文件：{output_y}")
        print(f"   源文件：{', '.join(revision_2_files)}")

    # 合并不带revision的文件，输出X后缀
    if normal_files:
        merged_normal = merge_json_files(normal_files)
        merged_normal = sorted(merged_normal, key=lambda x: x["content"], reverse=True)
        output_x = f"{common_prefix}_merged_X.json"
        with open(output_x, 'w', encoding='utf-8') as f:
            json.dump(merged_normal, f, ensure_ascii=False, indent=2)
        print(f"\n✅ 已合并所有普通文件：{output_x}")
        print(f"   源文件：{', '.join(normal_files)}")

    if not revision_1_files and not revision_2_files and not normal_files:
        print("⚠️  当前目录未找到任何JSON文件！")


if __name__ == "__main__":
    merge_main(image_prefix="736420000_sd", json_results_path="/home/lab1523-4090/JoshuaWen/Code/Drawing-Comparison/test_process/json_results")
    print("\n📌 合并完成！")