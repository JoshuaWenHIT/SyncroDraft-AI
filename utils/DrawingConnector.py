import cv2
import numpy as np
from skimage.morphology import skeletonize
from collections import deque


class DrawingConnector:
    def __init__(self, image_path):
        """
        初始化：读取图像并进行预处理
        """
        self.original_img = cv2.imread(image_path)
        if self.original_img is None:
            raise ValueError(f"无法读取图片: {image_path}")

        self.h, self.w = self.original_img.shape[:2]
        self.debug_img = self.original_img.copy()

        # 1. 转灰度并二值化 (假设白底黑字或黑底白字，统一转为黑底白线)
        gray = cv2.cvtColor(self.original_img, cv2.COLOR_BGR2GRAY)
        # 自适应阈值处理，提取线条
        binary = cv2.adaptiveThreshold(
            ~gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, -2
        )
        self.binary_map = binary

    def preprocess_lines(self, text_boxes_to_mask):
        """
        预处理：移除文本区域，生成只有线条的骨架图
        """
        # 复制一份二值图
        clean_lines = self.binary_map.copy()

        # 1. 抹除文字：将文本框区域涂黑，避免文字本身的笔画干扰路径搜索
        #    但是保留文本框边缘一点点，以便后续连接
        for x, y, w, h in text_boxes_to_mask:
            # 稍微缩小一点抹除范围，防止把刚接触的线头彻底抹没了
            pad = 2
            cv2.rectangle(
                clean_lines, (x + pad, y + pad), (x + w - pad, y + h - pad), 0, -1
            )

        # 2. 骨架化：将线条变细为 1 像素
        #    Skeletonize 比较耗时，但能保证拓扑结构准确
        print("正在提取线条骨架 (可能需要几秒)...")
        skeleton = skeletonize(clean_lines // 255).astype(np.uint8) * 255
        self.skeleton = skeleton
        return skeleton

    def find_matches(self, text_boxes, arrow_boxes):
        """
        主函数：输入文本框和箭头框，输出匹配对
        """
        # 先生成骨架
        text_bboxes = [box["bbox"] for box in text_boxes]
        arrow_bboxes = [box["bbox"] for box in arrow_boxes]
        self.preprocess_lines(text_bboxes)

        matches = []  # 存储结果 [(text_idx, arrow_idx), ...]

        # ID来源于输入的text_boxes和arrow_boxes的id字段
        for t_box in text_boxes:
            t_id = t_box["id"]  # 使用输入数据中的id字段
            print(f"正在搜索文本 ID {t_id} 的关联箭头...")
            found_arrow_indices = self._bfs_search(t_box["bbox"], arrow_bboxes)

            for a_idx in found_arrow_indices:
                a_id = arrow_boxes[a_idx]["id"]  # 使用输入数据中的id字段
                a_type = arrow_boxes[a_idx].get("type", "Unknown")  # 提取箭头类型
                matches.append(
                    {
                        "text_id": t_id,
                        "text_box": t_box["bbox"],
                        "arrow_id": a_id,
                        "arrow_type": a_type,  # 添加箭头类型
                        "arrow_box": arrow_bboxes[a_idx],
                    }
                )

        return matches

    def _bfs_search(self, start_box, target_boxes):
        """
        核心算法：从文本框出发，使用广度优先搜索(BFS)沿骨架寻找箭头
        """
        sx, sy, sw, sh = start_box

        # 1. 寻找入口点 (Seeds)
        #    在文本框周围扩充一定的像素，寻找所有接触文本框的骨架点
        search_padding = 25
        x1 = max(0, sx - search_padding)
        y1 = max(0, sy - search_padding)
        x2 = min(self.w, sx + sw + search_padding)
        y2 = min(self.h, sy + sh + search_padding)

        roi = self.skeleton[y1:y2, x1:x2]
        seed_points = np.argwhere(roi == 255)

        if len(seed_points) == 0:
            return []

        # 初始化 BFS 队列
        queue = deque()
        visited = set()

        # 将所有入口点加入队列 (转为全局坐标)
        for pt in seed_points:
            gy, gx = pt[0] + y1, pt[1] + x1
            queue.append((gy, gx))
            visited.add((gy, gx))

        found_targets = set()

        # 安全限制，防止死循环遍历全图
        max_steps = 10000
        steps = 0

        while queue and steps < max_steps:
            cy, cx = queue.popleft()
            steps += 1

            # 2. 检查是否命中箭头
            for i, (ax, ay, aw, ah) in enumerate(target_boxes):
                if i in found_targets:
                    continue
                # 稍微放宽碰撞检测 (Buffer)，保证接触即命中
                if (ax - 5) <= cx <= (ax + aw + 5) and (ay - 5) <= cy <= (ay + ah + 5):
                    found_targets.add(i)
                    # 可视化：画出连接路径点 (调试用)
                    self.debug_img[cy, cx] = [0, 0, 255]

            # 如果已经找到两个箭头(通常尺寸线两头各一个)，可以提前结束优化速度
            if len(found_targets) >= 1:
                break

            # 3. 沿骨架游走 (8邻域)
            for dy in [-1, 0, 1]:
                for dx in [-1, 0, 1]:
                    if dx == 0 and dy == 0:
                        continue
                    ny, nx = cy + dy, cx + dx

                    if 0 <= ny < self.h and 0 <= nx < self.w:
                        if self.skeleton[ny, nx] == 255 and (ny, nx) not in visited:
                            visited.add((ny, nx))
                            queue.append((ny, nx))

        return list(found_targets)

    def visualize(self, matches, arrow_boxes):
        """
        可视化结果并保存
        """
        vis_img = self.original_img.copy()

        # 画所有箭头框 (绿色)
        for m in matches:
            a_box = m["arrow_box"]
            a_type = m.get("arrow_type", "Unknown")  # 获取箭头类型
            x, y, w, h = a_box
            cv2.rectangle(vis_img, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(
                vis_img,
                f"A{m['arrow_id']}({a_type})",
                (x, y - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 0),
                2,
            )

        # 画文本框 (蓝色) 和 连接线
        for m in matches:
            t_box = m["text_box"]
            t_id = m["text_id"]
            a_box = m["arrow_box"]
            a_type = m.get("arrow_type", "Unknown")  # 获取箭头类型

            # 画文本框
            tx, ty, tw, th = t_box
            cv2.rectangle(vis_img, (tx, ty), (tx + tw, ty + th), (255, 0, 0), 2)
            cv2.putText(
                vis_img,
                f"T{t_id}",
                (tx, ty - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 0, 0),
                2,
            )

            # 画一条直线表示匹配关系 (红色虚线效果)
            t_center = (int(tx + tw / 2), int(ty + th / 2))
            a_center = (int(a_box[0] + a_box[2] / 2), int(a_box[1] + a_box[3] / 2))
            cv2.line(vis_img, t_center, a_center, (0, 0, 255), 2)

            # 在连线中间显示箭头类型
            mid_point = (
                (t_center[0] + a_center[0]) // 2,
                (t_center[1] + a_center[1]) // 2,
            )
            cv2.putText(
                vis_img,
                a_type,
                mid_point,
                cv2.FONT_HERSHEY_SIMPLEX,
                0.4,
                (0, 0, 255),
                1,
            )

        # cv2.imshow("Matches", vis_img)
        cv2.imwrite("result_matches.png", vis_img)
        print(f"结果已保存为 result_matches.png")
        cv2.waitKey(0)
        cv2.destroyAllWindows()


# ==========================================
#  请在下方修改你的输入数据
# ==========================================
if __name__ == "__main__":

    # 1. 图片路径 (请修改为你的文件名)
    img_path = "view_736420000_sd_page_1_view_1.png"

    # 2. 文本框列表 [x, y, w, h]
    #    (这里是示例数据，请替换为你 OCR 识别出的真实数据)
    #    例如图中的 "5X 2.00", "10.00"
    my_text_boxes = [
        {
            "id": 1111111,
            "bbox": [42, 241, 123, 51],
        },
        {
            "id": 2222222,
            "bbox": [61, 427, 96, 47],
        },
    ]
    # my_text_boxes = [
    #     [41,421,70,45],  # 假设这是 "10.00" 的位置
    # ]

    # 3. 箭头框列表 [x, y, w, h]
    #    (这里是示例数据，请替换为你检测到的箭头数据)
    my_arrow_boxes = [
        {
            "id": 1001,
            "type": "Horizontal",
            "bbox": [176, 308, 20, 23],
        },
        {
            "id": 1002,
            "type": "Vertical",
            "bbox": [179, 380, 16, 26],
        },
        {
            "id": 1003,
            "type": "Horizontal",
            "bbox": [99, 334, 18, 27],
        },
        {
            "id": 1004,
            "type": "Vertical",
            "bbox": [100, 542, 17, 26],
        },
    ]
    # my_arrow_boxes = [
    #     [67,474,17,27],  # 箭头1
    # ]
    # --- 执行代码 ---
    # try:
    matcher = DrawingConnector(img_path)

    # 开始匹配
    results = matcher.find_matches(my_text_boxes, my_arrow_boxes)

    # 打印文本结果
    print("\n--- 匹配结果 ---")
    for res in results:
        arrow_type = res.get("arrow_type", "Unknown")
        print(
            f"文本框 (ID {res['text_id']}) 匹配到了 -> 箭头 (ID {res['arrow_id']}, 类型: {arrow_type})"
        )

    # 显示图片结果
    matcher.visualize(results, my_arrow_boxes)

    # except Exception as e:
    #     print(f"发生错误: {e}")
    #     print("请检查图片路径是否正确，或者是否安装了 opencv-python 和 scikit-image")
