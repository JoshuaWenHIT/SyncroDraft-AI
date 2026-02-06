import json
import cv2
import os
import shutil
from drawing_server import log_utils

# ====================== 配置参数======================
JSON_FILE_PATH = "./test_process/json_results/compare_report.json"  # JSON文件路径
IMAGE_FOLDER = "./data/image_data"  # 原始图片所在文件夹
OUTPUT_FOLDER = "./test_process/annotated_images"  # 标注后图片保存文件夹
POSITION_FOLDER = "./test_process/sub_views"
# 颜色定义
RED = (0, 0, 255)  # same_view_content_different 用红框
BLUE = (255, 0, 0)  # same_view_b_only 用蓝框
ORANGE = (0, 128, 255)  # same_view_a_only 用橙框
BOX_THICKNESS = 2  # 框的粗细


# ====================== 工具函数 ======================
def create_folder(folder_path):
    """创建文件夹（如果不存在）"""
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)


def copy_image(image_path, output_path):
    """复制图片"""
    if not os.path.exists(image_path):
        log_utils.log(f"图片不存在")
        return

    # 复制图片
    shutil.copy2(image_path, output_path)
    # print(f"✅ 图片复制完成：{output_path}")


def read_positions_file(file_path):
    """
    从positions.txt文件中读取子视图的位置信息
    :param file_path: positions.txt文件路径
    :return: 包含子视图ID和相应位置信息的字典
    """
    positions = {}
    with open(file_path, "r") as f:
        next(f)  # positions.tx文件第一行是信息的名称，不需要读取
        for line in f.readlines():
            parts = line.strip().split(",")
            # positions.tx文件中含含ID, x, y, w, h, center_x, center_y
            positions[parts[0]] = {
                "x": float(parts[1]),
                "y": float(parts[2]),
                "w": float(parts[3]),
                "h": float(parts[4]),
                "center_x": float(parts[5]),
                "center_y": float(parts[6]),
            }
    return positions


def draw_bbox_on_image(image_path, bbox, color, positions_info):
    """
    在图片上绘制矩形框
    :param image_path: 原始图片路径
    :param bbox: 边界框字典, 包含x, y, width, height
    :param color: 框的颜色(BGR)
    :param positions_info: 视图的归一化坐标，方便后续bbox还原到原始程程图纸
    """
    # 检查图片是否存在
    if not os.path.exists(image_path):
        log_utils.log(f"⚠️ 图片不存在：{image_path}")
        return

    # 读取图片
    img = cv2.imread(image_path)
    original_h, original_w = img.shape[:2]
    if img is None:
        log_utils.log(f"⚠️ 无法读取图片：{image_path}")
        return

    pad = 20  # 在子视图分割的代码./utils/view_seg.py中，为了使分割出来的子视图不要紧贴边界，在边界上加上一定的padding，这里同样需要考虑减掉这个padding

    view_x = positions_info["x"] * original_w
    view_y = positions_info["y"] * original_h
    bbox_x = bbox["x"] - pad
    bbox_y = bbox["y"] - pad
    bbox_w = bbox["width"]
    bbox_h = bbox["height"]

    new_bbox = {
        "x": view_x + bbox_x,
        "y": view_y + bbox_y,
        "width": bbox_w,
        "height": bbox_h,
    }

    new_bbox["x"] = max(0, min(original_w - new_bbox["width"], new_bbox["x"]))
    new_bbox["y"] = max(0, min(original_h - new_bbox["height"], new_bbox["y"]))

    x = int(new_bbox["x"])
    y = int(new_bbox["y"])
    # 计算矩形右下角坐标（cv2.rectangle需要左上角和右下角）
    x2 = int(x + new_bbox["width"])
    y2 = int(y + new_bbox["height"])

    # 绘制矩形框
    cv2.rectangle(img, (x, y), (x2, y2), color, BOX_THICKNESS)

    # 保存标注后的图片
    cv2.imwrite(image_path, img)


def process_annotations(json_data, image_folder, output_folder, position_file_folder):
    """
    处理所有标注项
    :param json_data: 解析后的JSON数据
    :param image_folder: 原始图片文件夹
    :param output_folder: 标注后图片保存文件夹
    """
    # 创建输出文件夹
    create_folder(output_folder)

    item_list = []
    uid_list = []
    view_list = []
    bbox_list = []
    color_list = []

    # 1. 处理 same_view_content_different（红框）
    content_diff = json_data.get("diff_details", {}).get(
        "same_view_content_different", []
    )
    if isinstance(content_diff, list):
        # print("\n===== 处理 same_view_content_different(红框)=====")
        for item in content_diff:
            # 提取必要字段
            if "a_annotation" in item:
                uid = item.get("a_annotation", {}).get("uid")
                view = item.get("a_annotation", {}).get("view")
                bbox = item.get("a_annotation", {}).get("bbox")

            # 检查字段是否完整
            if not all([uid, view, bbox]):
                log_utils.log(f"⚠️ 字段缺失，跳过项：{item}")
                continue

            item_list.append("same_view_content_different")
            uid_list.append(uid)
            view_list.append(view)
            bbox_list.append(bbox)
            color_list.append(RED)

    # 2. 处理 same_view_a_only（蓝框）
    a_only = json_data.get("diff_details", {}).get("same_view_a_only", [])
    if isinstance(a_only, list):
        # print("\n===== 处理 same_view_a_only(蓝框)=====")
        for item in a_only:
            # 提取必要字段
            if "annotation" in item:
                uid = item.get("annotation", {}).get("uid")
                view = item.get("annotation", {}).get("view")
                bbox = item.get("annotation", {}).get("bbox")

            # 检查字段是否完整
            if not all([uid, view, bbox]):
                log_utils.log(f"⚠️ 字段缺失，跳过项：{item}")
                continue

            item_list.append("same_view_a_only")
            uid_list.append(uid)
            view_list.append(view)
            bbox_list.append(bbox)
            color_list.append(BLUE)

    # 3. 处理 same_view_b_only（橙框）
    b_only = json_data.get("diff_details", {}).get("same_view_b_only", [])
    if isinstance(b_only, list):
        # print("\n===== 处理 same_view_b_only(橙框)=====")
        for item in b_only:
            # 提取必要字段
            if "annotation" in item:
                uid = item.get("annotation", {}).get("uid")
                view = item.get("annotation", {}).get("view")
                bbox = item.get("annotation", {}).get("bbox")

            # 检查字段是否完整
            if not all([uid, view, bbox]):
                log_utils.log(f"⚠️ 字段缺失，跳过项：{item}")
                continue

            item_list.append("same_view_b_only")
            uid_list.append(uid)
            view_list.append(view)
            bbox_list.append(bbox)
            color_list.append(ORANGE)

    # 4. 还原子视图bbox到原始图片
    # print("\n===== 还原子视图bbox到原始图片 =====")
    name = "_".join(uid.split("_")[:2])

    # 可视化
    position_info_dict = {}
    image_name_dict = {}
    for image in os.listdir(image_folder):
        if image.startswith(f"{name}"):
            image_basename = os.path.splitext(image)[0]
            position_info = read_positions_file(
                os.path.join(position_file_folder, image_basename, "positions.txt")
            )
            position_info_dict[image_basename] = position_info
            if image_basename.startswith(f"{name}_revision"):
                image_name_dict["revision"] = image_basename
            else:
                image_name_dict["original"] = image_basename
            copy_image(
                os.path.join(image_folder, image), os.path.join(output_folder, image)
            )

    for item, uid, view, bbox, color in zip(
        item_list, uid_list, view_list, bbox_list, color_list
    ):
        if item == "same_view_content_different":
            image_file = image_name_dict["revision"] + ".png"
            img_input_path = os.path.join(output_folder, image_file)
            view_position_info = position_info_dict[image_name_dict["revision"]][uid]
            draw_bbox_on_image(img_input_path, bbox, color, view_position_info)
        elif item == "same_view_a_only":
            image_file = image_name_dict["revision"] + ".png"
            img_input_path = os.path.join(output_folder, image_file)
            view_position_info = position_info_dict[image_name_dict["revision"]][uid]
            draw_bbox_on_image(img_input_path, bbox, color, view_position_info)
        elif item == "same_view_b_only":
            image_file = image_name_dict["original"] + ".png"
            img_input_path = os.path.join(output_folder, image_file)
            view_position_info = position_info_dict[image_name_dict["original"]][uid]
            draw_bbox_on_image(img_input_path, bbox, color, view_position_info)


def json_vis(json_file_path, image_folder, output_folder, position_file_folder):
    # 1. 读取JSON文件
    try:
        with open(json_file_path, "r", encoding="utf-8") as f:
            json_data = json.load(f)
        log_utils.log("JSON文件读取成功")
    except FileNotFoundError:
        log_utils.log(f"错误:JSON文件不存在 - {json_file_path}")
        exit(1)
    except json.JSONDecodeError:
        log_utils.log(f"错误:JSON文件格式无效 - {json_file_path}")
        exit(1)

    # 2. 处理标注
    process_annotations(json_data, image_folder, output_folder, position_file_folder)

    log_utils.log("\n所有标注处理完成！")


# ====================== 主程序 ======================
if __name__ == "__main__":
    json_vis(JSON_FILE_PATH, IMAGE_FOLDER, OUTPUT_FOLDER, POSITION_FOLDER)
    # # 1. 读取JSON文件
    # try:
    #     with open(JSON_FILE_PATH, "r", encoding="utf-8") as f:
    #         json_data = json.load(f)
    #     print("JSON文件读取成功")
    # except FileNotFoundError:
    #     print(f"错误:JSON文件不存在 - {JSON_FILE_PATH}")
    #     exit(1)
    # except json.JSONDecodeError:
    #     print(f"错误:JSON文件格式无效 - {JSON_FILE_PATH}")
    #     exit(1)
    #
    # # 2. 处理标注
    # process_annotations(json_data, IMAGE_FOLDER, OUTPUT_FOLDER)
    #
    # print("\n所有标注处理完成！")
