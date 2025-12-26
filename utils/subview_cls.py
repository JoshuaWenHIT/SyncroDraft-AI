import os

def load_positions(filepath):
    """
    读取 position.txt 文件，返回一个字典。
    Key: Image ID (string, e.g., '736420000_sd_view_3')
    Value: {'center_x': float, 'center_y': float}
    """
    pos_map = {}
    if not os.path.exists(filepath):
        print(f"Error: Position file not found at {filepath}")
        return pos_map

    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line: continue

            parts = line.split(',')
            # 格式: ID,x,y,w,h,center_x,center_y
            if len(parts) >= 7:
                img_id = parts[0]
                try:
                    cx = float(parts[5])
                    cy = float(parts[6])
                    pos_map[img_id] = {'cx': cx, 'cy': cy}
                except ValueError:
                    continue
    return pos_map


def classify_three_views(file_list, pos_map, alignment_threshold):
    """
    利用几何位置关系判断三视图类型。
    """
    if len(file_list) != 3:
        print(f"Warning: Expected 3 files, found {len(file_list)}")
        return {f: 'unknown' for f in file_list}

    # 准备数据
    views_data = []
    for fname in file_list:
        img_id = os.path.splitext(fname)[0]  # 去掉 .png 得到 ID
        if img_id in pos_map:
            views_data.append({
                'filename': fname,
                'cx': pos_map[img_id]['cx'],
                'cy': pos_map[img_id]['cy']
            })
        else:
            print(f"Warning: ID {img_id} not found in position.txt")
            return {f: 'unknown' for f in file_list}

    result_map = {}
    front_view = None

    # 1. 寻找正视图 (b)
    # 正视图应该与一个视图 X 坐标接近 (俯视图)，与另一个视图 Y 坐标接近 (侧视图)
    for i, v_curr in enumerate(views_data):
        has_v_neighbor = False  # 垂直邻居 (X相近)
        has_h_neighbor = False  # 水平邻居 (Y相近)

        for j, v_other in enumerate(views_data):
            if i == j: continue

            dx = abs(v_curr['cx'] - v_other['cx'])
            dy = abs(v_curr['cy'] - v_other['cy'])

            if dx < alignment_threshold: has_v_neighbor = True
            if dy < alignment_threshold: has_h_neighbor = True

        if has_v_neighbor and has_h_neighbor:
            front_view = v_curr
            result_map[v_curr['filename']] = 'b'  # 正视图
            break

    # 兜底：如果找不到完美的中心点，通常这表明数据有误，这里简单处理
    if front_view is None:
        print("Warning: Could not identify Front View (b) geometrically.")
        return {f: 'unknown' for f in file_list}

    # 2. 寻找俯视图 (a) 和 侧视图 (c)
    for item in views_data:
        if item['filename'] == front_view['filename']:
            continue

        dx = abs(item['cx'] - front_view['cx'])
        dy = abs(item['cy'] - front_view['cy'])

        # 与正视图 X 对齐的是俯视图 (a)
        if dx < alignment_threshold:
            result_map[item['filename']] = 'a'
        # 与正视图 Y 对齐的是侧视图 (c)
        elif dy < alignment_threshold:
            result_map[item['filename']] = 'c'
        else:
            result_map[item['filename']] = 'unknown'

    return result_map