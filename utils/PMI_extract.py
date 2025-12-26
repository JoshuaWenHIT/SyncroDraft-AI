import os
import json
from ultralytics import YOLO
import math
from pathlib import Path
from utils.DrawingConnector import DrawingConnector
import cv2
import torch
from torchvision import models, transforms
from PIL import Image
import torch.nn as nn
import sys
from utils.demo_element_tools import DOLPHIN
from utils.content_process import process_image_content

# ================= LINE分类配置 =================
LINE_CLASSIFY_MODEL_PATH = './weights/best_line_classify_1.pth'
LINE_CLASS_NAMES = ['asymmetric', 'basic', 'liner', 'reference', 'symmetric']


def load_line_classify_model():
    """
    加载LINE分类模型
    """
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

    # 重新构建模型结构
    model = models.resnet18(weights=None)
    num_ftrs = model.fc.in_features
    model.fc = nn.Linear(num_ftrs, len(LINE_CLASS_NAMES))

    # 加载训练好的权重
    model.load_state_dict(torch.load(LINE_CLASSIFY_MODEL_PATH, map_location=device))
    model.to(device)
    model.eval()

    return model, device


def classify_line_image(model, device, image_path):
    """
    对单张LINE图像进行分类
    """
    try:
        # 图片预处理 (必须与训练集 val 阶段一致)
        transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ])

        # 读取图片并推理
        image = Image.open(image_path).convert('RGB')
        image_tensor = transform(image).unsqueeze(0).to(device)  # 增加 batch 维度

        with torch.no_grad():
            outputs = model(image_tensor)
            # 获取概率
            probs = torch.nn.functional.softmax(outputs, dim=1)
            conf, preds = torch.max(probs, 1)

        idx = preds.item()
        return LINE_CLASS_NAMES[idx], conf.item()
    except Exception as e:
        print(f"分类图像 {image_path} 时出错: {e}")
        return "line", 0.0  # 出错时返回默认值


def detect_arrow(model, img_path, output_dir, conf=0.3):
    """
    【函数1】常规检测
    返回格式：xywh (Top-Left 左上角坐标)
    """
    # 推理
    results = model.predict(
        source=img_path,
        conf=conf,
        save=True,
        project=output_dir,
        name='std_detection',
        exist_ok=True,
        show=False
    )

    detected_data = []

    # 获取图像文件名（不包含扩展名），用于生成唯一ID
    img_stem = Path(img_path).stem

    for result in results:
        # 获取 xywh (默认为 center_x, center_y, w, h)
        boxes_xywh = result.boxes.xywh.cpu().numpy()
        boxes_cls = result.boxes.cls.cpu().numpy()
        boxes_conf = result.boxes.conf.cpu().numpy()

        for i in range(len(boxes_xywh)):
            cx, cy, w, h = boxes_xywh[i]

            # --- 转换核心：中心点 -> 左上角 ---
            x_top_left = cx - (w / 2)
            y_top_left = cy - (h / 2)

            cls_id = int(boxes_cls[i])
            cls_name = model.names[cls_id]

            # 生成唯一ID
            unique_id = f"{img_stem}_{cls_name}_{i:04d}"

            detected_data.append({
                "id": unique_id,  # 添加唯一ID
                "class_id": cls_id,
                "class_name": cls_name,
                # 返回 [x_tl, y_tl, w, h]
                "bbox_xywh": [int(x_top_left), int(y_top_left), int(w), int(h)],
                "conf": round(float(boxes_conf[i]), 4)
            })

    return detected_data


def detect_obb_lines(model, img_path, output_dir, conf=0.25):
    """
    【函数2】旋转检测 (输出所有OBB类别)
    返回格式：xywh (Top-Left 左上角坐标) + Angle
    """
    img_stem = Path(img_path).stem
    results = model.predict(
        source=img_path,
        conf=conf,
        save=True,
        project=output_dir,
        name='obb_detection',
        exist_ok=True,
        show=False,
        imgsz=1024
    )

    obb_data = []
    result = results[0]

    if result.obb is None:
        return obb_data

    # 获取原始图像
    original_img = result.orig_img

    # 获取 OBB 数据: center_x, center_y, w, h, rotation
    r_boxes = result.obb.xywhr.cpu().numpy()
    scores = result.obb.conf.cpu().numpy()
    cls = result.obb.cls.cpu().numpy()

    for i in range(len(r_boxes)):
        class_name = model.names[int(cls[i])]

        cx, cy, w, h, rotation_rad = r_boxes[i]
        # print(r_boxes[i])
        rotation_deg = math.degrees(rotation_rad)

        # --- 转换核心：中心点 -> 左上角 ---
        # 注意：这里的"左上角"是基于矩形自身坐标系的，配合 angle 使用才有意义
        x_top_left = cx - (w / 2)
        y_top_left = cy - (h / 2)

        x0 = int(round(x_top_left))
        y0 = int(round(y_top_left))
        w_i = int(round(w))
        h_i = int(round(h))

        # 2. 边界裁剪（非常关键）
        x1 = max(0, x0)
        y1 = max(0, y0)
        x2 = min(original_img.shape[1], x0 + w_i)
        y2 = min(original_img.shape[0], y0 + h_i)
        # print(x1, y1, x2, y2)
        unique_id = f"{img_stem}_{class_name}_{i:04d}"

        # 保存检测到的目标图像（除了ex类）
        if class_name != "ex" and original_img is not None:
            try:
                if x1 < x2 and y1 < y2:
                    # 裁剪图像
                    cropped_img = original_img[y1:y2, x1:x2]
                    # cropped_img = original_img[x1:x2, y1:y2]

                    # 创建保存目录
                    cropped_save_dir = os.path.join(output_dir, "cropped_objects")
                    os.makedirs(cropped_save_dir, exist_ok=True)

                    # 生成保存文件名，格式为：736420000_sd_view_5_b_line_0001.jpg
                    cropped_filename = f"{unique_id}.jpg"
                    cropped_save_path = os.path.join(cropped_save_dir, cropped_filename)

                    # 保存裁剪后的图像
                    if cropped_img.size > 0:  # 确保裁剪后的图像不为空
                        cv2.imwrite(cropped_save_path, cropped_img)
                        print(f"已保存检测目标图像: {cropped_save_path}")
            except Exception as e:
                print(f"保存检测目标图像时出错: {e}")

        obb_data.append({
            "id": unique_id,
            "class_name": class_name,
            # 返回 [x_tl, y_tl, w, h]
            "bbox_xywh": [float(f"{v:.2f}") for v in [x_top_left, y_top_left, w, h]],
            "angle": round(rotation_deg, 2),
            "conf": round(float(scores[i]), 4)
        })

    return obb_data


def generate_json_output(img_path, res_obb, matches, save_dir, line_classifier_model=None, line_classifier_device=None, ocr_model=None):
    """
    生成指定格式的JSON文件，对line类型进行细分类
    """
    # 从图像文件名中提取uid和view
    img_stem = Path(img_path).stem

    # 解析文件名，格式如: 736420000_sd_view_1_a
    # uid应该是: 736420000_sd_view_1
    # view应该是: a
    if "_" in img_stem:
        # 分割文件名，最后一个下划线部分是view，其余部分是uid
        parts = img_stem.split("_")
        view = parts[-1]  # 最后一部分是view
        uid = "_".join(parts[:-1])  # 其余部分组合成uid
    else:
        uid = img_stem
        view = "1"

    # 创建一个文本ID到箭头方向的映射（仅用于line类型）
    text_arrow_direction_map = {}
    for match in matches:
        text_arrow_direction_map[match["text_id"]] = match["arrow_type"].lower()

    # 创建一个结果列表
    json_results = []

    # 处理OBB检测结果(res_obb) - 包括所有类别
    for item in res_obb:
        # 为每个OBB检测结果创建JSON条目
        if item["class_name"] == "ex":
            continue

        # 默认类别和方向
        category = item["class_name"]
        direction = "none"  # 默认为"none"

        cropped_objects_dir = os.path.join(save_dir, "cropped_objects")
        cropped_image_path = os.path.join(cropped_objects_dir, f"{item['id']}.jpg")

        # 如果是line类型，进行细分类
        if item["class_name"] == "line":
            # 构造裁剪图像的路径


            # 如果找到了对应的裁剪图像，则进行分类
            if os.path.exists(cropped_image_path) and line_classifier_model is not None:
                classified_type, confidence = classify_line_image(line_classifier_model, line_classifier_device,
                                                                  cropped_image_path)
                category = classified_type
                print(f"ID {item['id']} 的line分类为: {classified_type} (置信度: {confidence:.4f})")
            else:
                print(f"未找到裁剪图像 {cropped_image_path} 或分类模型未加载，使用默认line分类")

        text_content = process_image_content(cropped_image_path, element_type="text", ocr_model=ocr_model)

        entry = {
            "uid": uid,
            "view": view,
            "category": category,
            "direction": direction,  # 默认为"none"
            "content": text_content,
            "bbox": {
                "x": item["bbox_xywh"][0],
                "y": item["bbox_xywh"][1],
                "width": item["bbox_xywh"][2],
                "height": item["bbox_xywh"][3]
            }
        }

        # 如果是line类型，检查是否有匹配的箭头方向
        if item["class_name"] == "line":
            # 查找匹配的箭头方向
            if item["id"] in text_arrow_direction_map:
                # 使用匹配箭头的方向
                direction = text_arrow_direction_map[item["id"]]
                entry["direction"] = direction

        json_results.append(entry)

    # 保存JSON文件
    json_filename = f"{img_stem}_result.json"
    json_filedir = os.path.join(save_dir, "json_results")
    os.makedirs(json_filedir, exist_ok=True)  # 创建目录，如果已存在则不会报错

    json_filepath = os.path.join(json_filedir, json_filename)

    with open(json_filepath, 'w', encoding='utf-8') as f:
        json.dump(json_results, f, indent=2, ensure_ascii=False)

    print(f"JSON结果已保存到: {json_filepath}")
    return json_results


def process_single_image(img_path, model_arrow, model_obb, save_root, line_classifier_model=None,
                         line_classifier_device=None, ocr_model=None):
    """
    处理单张图像
    """
    print(f"\n>>> 正在处理图像: {img_path}")

    try:
        # 1. 测试常规检测 (Top-Left xywh) - 仅用于line类型的箭头匹配
        print("\n>>> 常规检测结果:")
        res_arrow = detect_arrow(model_arrow, str(img_path), save_root)
        for r in res_arrow:
            print(f"ID: {r['id']}, Type: {r['class_name']}, Box(TL): {r['bbox_xywh']}")

        # 2. 测试 OBB 检测 (Top-Left xywh + Angle) - 输出所有类别
        print("\n>>> 旋转检测结果:")
        res_obb = detect_obb_lines(model_obb, str(img_path), save_root)
        for r in res_obb:
            print(f"ID: {r['id']}, Type: {r['class_name']}, Box(TL): {r['bbox_xywh']}, Angle: {r['angle']}")

        # 准备文本框和箭头框数据供匹配使用
        # 仅对line类型进行箭头匹配
        line_text_boxes = []
        for item in res_obb:
            # 只有line类型才参与箭头匹配
            if item["class_name"] == "line":
                # 确保边界框坐标是整数类型
                bbox = [int(coord) for coord in item["bbox_xywh"]]
                line_text_boxes.append({
                    "id": item["id"],
                    "bbox": bbox
                })

        # 仅使用箭头检测结果中需要匹配的部分
        arrow_boxes_for_matching = []
        for item in res_arrow:
            # 确保边界框坐标是整数类型
            bbox = [int(coord) for coord in item["bbox_xywh"]]
            arrow_boxes_for_matching.append({
                "id": item["id"],
                "bbox": bbox,
                "type": item["class_name"]  # 添加类型信息
            })

        # 只有当存在line类型文本框时才执行匹配
        matches = []
        if line_text_boxes:
            matcher = DrawingConnector(str(img_path))
            # 开始匹配（仅对line类型）
            matches = matcher.find_matches(line_text_boxes, arrow_boxes_for_matching)

            # 打印文本结果
            print("\n--- 匹配结果 ---")
            for res in matches:
                print(
                    f"文本框 (ID {res['text_id']}) 匹配到了 -> 箭头 (ID {res['arrow_id']}, 类型: {res['arrow_type']})")

            # 保存可视化结果
            # matcher.visualize(matches, arrow_boxes_for_matching)
        else:
            print("\n>>> 没有line类型的对象，跳过箭头匹配过程")

        # 生成指定格式的JSON文件
        print("\n>>> 生成JSON文件...")
        json_results = generate_json_output(img_path, res_obb, matches, save_root, line_classifier_model,
                                            line_classifier_device, ocr_model)
        print(f"生成了 {len(json_results)} 个JSON条目")

        return True
    except Exception as e:
        print(f"处理图像 {img_path} 时出错: {e}")
        import traceback
        traceback.print_exc()
        return False


# ==========================================
#  调用测试
# ==========================================
def process_once(img_folder, save_root):
    arrow_model_path = './weights/best_arrow_det.pt'
    obb_model_path = './weights/best_line_det.pt'
    ocr_model_path = './weights/hf_model'
    # 支持的图像格式
    supported_formats = ('.png', '.jpg', '.jpeg', '.bmp', '.tiff')

    try:
        # 加载LINE分类模型
        print("正在加载LINE分类模型...")
        line_classifier_model, line_classifier_device = load_line_classify_model()
        print("LINE分类模型加载完成")

        # 加载检测模型
        print("正在加载检测模型...")
        model_arrow = YOLO(arrow_model_path)
        model_obb = YOLO(obb_model_path)
        print("检测模型加载完成")

        # 加载OCR识别模型

        print("正在加载OCR识别模型...")
        ocr_model = DOLPHIN(ocr_model_path)
        print("OCR识别模型加载完成")

        # 获取文件夹中所有图像文件
        img_paths = []
        if os.path.isdir(img_folder):
            for file in os.listdir(img_folder):
                if file.lower().endswith(supported_formats):
                    img_paths.append(os.path.join(img_folder, file))
            print(f"找到 {len(img_paths)} 个图像文件")
        else:
            print(f"指定的路径不是一个有效的文件夹: {img_folder}")
            exit(1)

        # 处理所有图像
        success_count = 0
        for img_path in img_paths:
            if process_single_image(Path(img_path), model_arrow, model_obb, save_root, line_classifier_model,
                                    line_classifier_device, ocr_model):
                success_count += 1

        print(f"\n处理完成！成功处理 {success_count}/{len(img_paths)} 张图像。")

    except Exception as e:
        print(f"运行出错: {e}")
        import traceback

        traceback.print_exc()

def PMI_extract(img_folder_1, img_folder_2, save_root):
    process_once(img_folder_1, save_root)
    process_once(img_folder_2, save_root)