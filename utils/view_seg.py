import cv2
import numpy as np
import os


def extract_subviews(image_path, first_name, output_dir):
    # 1. 读取图像
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"无法读取图像: {image_path}")

    # 创建一个副本用于画框调试 (以免污染用于抠图的原图数据)
    debug_img = img.copy()

    # 2. 预处理
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)

    # 3. 膨胀操作 (替换单行膨胀代码)
    # 3.1 定义定向内核 (可根据图纸稀疏度调整大小)
    # H_SIZE = 60, V_SIZE = 60 意味着它能在水平或垂直方向上连接 60 像素以内的距离
    H_SIZE = 60
    V_SIZE = 60

    # 强力水平内核：宽且扁，用于连接左右散落的尺寸标注
    kernel_h = cv2.getStructuringElement(cv2.MORPH_RECT, (H_SIZE, 5))
    # 强力垂直内核：窄且高，用于连接上下散落的尺寸标注
    kernel_v = cv2.getStructuringElement(cv2.MORPH_RECT, (5, V_SIZE))

    # 3.2 执行定向膨胀
    dilated_h = cv2.dilate(thresh, kernel_h, iterations=1)
    dilated_v = cv2.dilate(thresh, kernel_v, iterations=1)

    # 3.3 合并结果：逻辑“或”操作将两次膨胀的结果合并到一个 Mask 中
    dilated = cv2.bitwise_or(dilated_h, dilated_v)

    # 4. 查找轮廓
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not os.path.exists(os.path.join(output_dir)):
        os.makedirs(os.path.join(output_dir))

    position_file_path = os.path.join(output_dir, "positions.txt")
    with open(position_file_path, 'w') as pos_file:
        pos_file.write("ID,x,y,w,h,center_x,center_y\n")  # 写入表头

    view_count = 0

    # 对轮廓进行排序（从上到下，从左到右），方便对应
    bounding_boxes = [cv2.boundingRect(c) for c in contours]
    # 将 contours 和 boxes 打包在一起排序
    cnt_box_pairs = sorted(zip(contours, bounding_boxes), key=lambda b: (b[1][1], b[1][0]))

    for i, (cnt, (x, y, w, h)) in enumerate(cnt_box_pairs):
        # 过滤极小的噪点区域
        area = w * h
        if area < 5000:
            continue

        # --- A. 核心功能：Mask 精准抠图 ---

        # 1. 制作 Mask：黑底，只有当前轮廓区域是白色的
        mask = np.zeros_like(gray)
        cv2.drawContours(mask, [cnt], -1, 255, -1)

        # 2. 制作画布：全白背景
        result_canvas = np.full_like(img, 255)

        # 3. 像素拷贝：只把 Mask 范围内的像素从原图拷过去
        result_canvas[mask == 255] = img[mask == 255]

        # 4. 裁剪出最终图片 (加一点 Padding 留白)
        pad = 20
        x_new = max(0, x - pad)
        y_new = max(0, y - pad)
        w_new = min(img.shape[1] - x_new, w + 2 * pad)
        h_new = min(img.shape[0] - y_new, h + 2 * pad)

        final_view = result_canvas[y_new:y_new + h_new, x_new:x_new + w_new]

        # 保存分割出来的子视图
        pic_name = first_name.replace('view_', '', 1).rsplit('_', 2)[0]
        save_name = f"view_{view_count}.png"
        cv2.imwrite(f"{output_dir}/{pic_name}_{save_name}", final_view)

        # 计算中心点
        center_x = x + w / 2
        center_y = y + h / 2

        x_norm, y_norm, w_norm, h_norm, center_x_norm, center_y_norm = x / img.shape[1], y / img.shape[0], w / \
                                                                       img.shape[1], h / img.shape[0], center_x / \
                                                                       img.shape[1], center_y / img.shape[0]

        # 在保存分割出来的子视图前，先将位置信息写入txt文件
        with open(position_file_path, 'a') as pos_file:
            pos_file.write(
                f"{pic_name}_view_{view_count},{x_norm:.4f},{y_norm:.4f},{w_norm:.4f},{h_norm:.4f},{center_x_norm:.4f},{center_y_norm:.4f}\n")

        # # --- B. 可视化调试  ---
        #
        # # 在 debug_img 上画红色的矩形框 (BGR: 0, 0, 255)
        # # thickness=3 表示线宽
        # cv2.rectangle(debug_img, (x, y), (x + w, y + h), (0, 0, 255), 3)
        #
        # # 在框的左上角写上 ID 编号，方便对照
        # # 如果 y-10 太靠上超出了图片，就写在框内部 y+30
        # text_y = y - 10 if y - 10 > 10 else y + 30
        # cv2.putText(debug_img, f"ID: {view_count}", (x, text_y),
        #             cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

        view_count += 1

    # --- C. 保存调试总览图 ---
    # cv2.imwrite(f"{output_dir}/{first_name}/_debug_overview.png", debug_img)
    # 保存膨胀图，方便检查是否需要调整 kernel
    # cv2.imwrite(f"{output_dir}/{first_name}/_debug_dilated.png", dilated)

    print(f"Process completed and results saved in {output_dir}/{pic_name}_view_*.png")