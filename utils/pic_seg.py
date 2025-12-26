import cv2
import numpy as np
import os


def process_image(input_path, output_dir):
    """
    单张图像处理逻辑
    :param input_path: 输入图像的路径
    :param output_dir: 输出目录，用于保存处理后的图像
    """
    # 创建输出目录（如果不存在）
    os.makedirs(output_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(input_path))[0]

    # 读取输入图像（灰度图）
    image = cv2.imread(input_path, cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise ValueError(f"Can't read image: {input_path}")

    # 二值化处理
    _, binary_image = cv2.threshold(image, 1, 255, cv2.THRESH_BINARY)

    # 连通组件分析
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
        binary_image, connectivity=8
    )

    if num_labels < 2:
        raise ValueError("未检测到任何前景连通区域")

    # 找到面积最大的连通域（跳过背景 label=0）
    max_area = 0
    max_label = 1
    for i in range(1, num_labels):
        area = stats[i, cv2.CC_STAT_AREA]
        if area > max_area:
            max_area = area
            max_label = i

    # 构建最大连通域的掩膜
    max_component_mask = np.zeros_like(labels, dtype=np.uint8)
    max_component_mask[labels == max_label] = 255

    # 查找外部轮廓
    contours, _ = cv2.findContours(
        max_component_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    if not contours:
        raise ValueError("未找到有效轮廓")

    # 选择面积最大的轮廓
    largest_contour = max(contours, key=cv2.contourArea)

    # 用精确轮廓掩膜提取内部内容（更精细的 view）
    mask_full = np.zeros_like(image, dtype=np.uint8)
    cv2.drawContours(mask_full, [largest_contour], -1, 255, thickness=cv2.FILLED)
    precise_view = cv2.bitwise_and(image, mask_full)

    # 背景填充为白色
    precise_view_filled = precise_view.copy()
    precise_view_filled[mask_full == 0] = 255

    # 分割frame部分
    precise_frame = np.ones_like(image) * 255
    precise_frame[mask_full == 0] = image[mask_full == 0]

    output_view = os.path.join(output_dir, f"view_{base_name}.png")
    output_frame = os.path.join(output_dir, f"frame_{base_name}.png")
    cv2.imwrite(output_view, precise_view_filled)
    cv2.imwrite(output_frame, precise_frame)

    print(f"Process completed and results saved in {output_dir}")
