import json
from typing import Dict, List, Any, Optional, Tuple


def load_json(file_path: str) -> List[Dict[str, Any]]:
    """加载JSON文件并返回解析后的列表"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"文件 {file_path} 未找到")
    except json.JSONDecodeError:
        raise ValueError(f"文件 {file_path} 不是有效的JSON格式")


def group_by_view(annotations: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """将标注信息按view字段分组"""
    view_groups = {}
    for anno in annotations:
        view = anno.get('view', 'unknown')
        if view not in view_groups:
            view_groups[view] = []
        view_groups[view].append(anno)
    return view_groups


def compare_view_annotations(a_annos: List[Dict[str, Any]], b_annos: List[Dict[str, Any]]) -> Dict[str, Any]:
    """比对单个view下的标注信息（先完成同category全量比对）"""
    b_annos_copy = [anno.copy() for anno in b_annos]
    view_diff = {
        "matched": [],  # 完全匹配的标注对
        "content_different": [],  # category/direction相同但content不同的标注对
        "a_only": [],  # A独有标注
        "b_only": [],  # B独有标注
        "match_candidates": {}  # 匹配候选追溯（便于排查）
    }

    for a_anno in a_annos:
        a_uid = a_anno.get('uid', 'unknown')
        a_category = a_anno.get('category')
        a_direction = a_anno.get('direction')
        a_content = a_anno.get('content')

        # 初始化该A标注的匹配候选追溯
        view_diff["match_candidates"][a_uid] = {
            "a_annotation": a_anno,
            "same_category_candidates": [],  # 所有同category的B候选
            "same_direction_candidates": [],  # 同category+同direction的B候选
            "final_match": None,  # 最终匹配的B标注
            "match_type": None  # 匹配类型：full_match/content_diff/none
        }

        # 步骤1：筛选B中所有同category的候选（完成同category全量比对）
        same_category_candidates = []
        for b_anno in b_annos_copy:
            if b_anno.get('category') == a_category:
                same_category_candidates.append(b_anno)
        view_diff["match_candidates"][a_uid]["same_category_candidates"] = same_category_candidates.copy()

        # 步骤2：在同category候选中，筛选同direction的次级候选
        same_direction_candidates = []
        for b_anno in same_category_candidates:
            if b_anno.get('direction') == a_direction:
                same_direction_candidates.append(b_anno)
        view_diff["match_candidates"][a_uid]["same_direction_candidates"] = same_direction_candidates.copy()

        # 步骤3：优先找完全匹配（category+direction+content均相同）
        matched_b_anno: Optional[Dict[str, Any]] = None
        match_index = -1
        match_type = None

        # 遍历所有同direction候选，找content完全匹配的
        for idx, b_anno in enumerate(b_annos_copy):
            if b_anno in same_direction_candidates and b_anno.get('content') == a_content:
                matched_b_anno = b_anno
                match_index = idx
                match_type = "full_match"
                break

        # 步骤4：若无完全匹配，找content不同的（category+direction相同）
        if matched_b_anno is None and len(same_direction_candidates) > 0:
            for idx, b_anno in enumerate(b_annos_copy):
                if b_anno in same_direction_candidates:
                    matched_b_anno = b_anno
                    match_index = idx
                    match_type = "content_diff"
                    break

        # 步骤5：处理匹配结果
        if match_index >= 0:
            del b_annos_copy[match_index]  # 移除已匹配的B标注，避免重复匹配
            view_diff["match_candidates"][a_uid]["final_match"] = matched_b_anno
            view_diff["match_candidates"][a_uid]["match_type"] = match_type

            if match_type == "full_match":
                view_diff["matched"].append({
                    "a_annotation": a_anno,
                    "b_annotation": matched_b_anno
                })
            elif match_type == "content_diff":
                view_diff["content_different"].append({
                    "diff_field": "content",
                    "a_content": a_content,
                    "b_content": matched_b_anno.get('content'),
                    "a_annotation": a_anno,
                    "b_annotation": matched_b_anno,
                    # 溯源关键信息
                    "trace_info": {
                        "a_uid": a_anno.get('uid'),
                        "a_view": a_anno.get('view'),
                        "a_bbox": a_anno.get('bbox'),
                        "b_uid": matched_b_anno.get('uid'),
                        "b_view": matched_b_anno.get('view'),
                        "b_bbox": matched_b_anno.get('bbox')
                    }
                })
        else:
            # 同category全量比对后仍无匹配，标记为A独有
            view_diff["a_only"].append({
                "annotation": a_anno,
                # 溯源关键信息
                "trace_info": {
                    "uid": a_anno.get('uid'),
                    "view": a_anno.get('view'),
                    "bbox": a_anno.get('bbox'),
                    "category": a_anno.get('category'),
                    "direction": a_anno.get('direction'),
                    "content": a_anno.get('content')
                }
            })

    # 剩余的B标注都是B独有，补充溯源信息
    view_diff["b_only"] = [{
        "annotation": b_anno,
        "trace_info": {
            "uid": b_anno.get('uid'),
            "view": b_anno.get('view'),
            "bbox": b_anno.get('bbox'),
            "category": b_anno.get('category'),
            "direction": b_anno.get('direction'),
            "content": b_anno.get('content')
        }
    } for b_anno in b_annos_copy]

    return view_diff


def cross_view_match(a_unmatched: List[Dict[str, Any]], b_unmatched: List[Dict[str, Any]]) -> Dict[str, Any]:
    """跨view比对未配对的标注（补充溯源信息）"""
    # 解析A未匹配项的原始标注（提取trace_info中的原始数据）
    a_unmatched_raw = [item['annotation'] for item in a_unmatched]
    b_unmatched_raw = [item['annotation'] for item in b_unmatched]

    b_unmatched_copy = [anno.copy() for anno in b_unmatched_raw]
    cross_result = {
        "cross_view_matched": [],  # 跨view匹配的标注对
        "final_a_only": [],  # 最终无匹配的A标注
        "final_b_only": []  # 最终无匹配的B标注
    }

    for a_anno in a_unmatched_raw:
        a_category = a_anno.get('category')
        a_content = a_anno.get('content')
        matched_b_idx = -1
        matched_b_anno = None

        # 跨view匹配：先全量比对同category候选，再判断content
        same_category_candidates = [b for b in b_unmatched_copy if b.get('category') == a_category]
        for idx, b_anno in enumerate(same_category_candidates):
            if b_anno.get('content') == a_content:
                matched_b_idx = b_unmatched_copy.index(b_anno)
                matched_b_anno = b_anno
                break

        if matched_b_idx >= 0:
            # 跨View匹配项（标注为"匹配差异"，便于溯源）
            cross_result["cross_view_matched"].append({
                "a_annotation": a_anno,
                "b_annotation": matched_b_anno,
                "a_view": a_anno.get('view', 'unknown'),
                "b_view": b_anno.get('view', 'unknown'),
                "match_rule": "category + content 一致（跨view）",
                # 溯源关键信息
                "trace_info": {
                    "a_uid": a_anno.get('uid'),
                    "a_view": a_anno.get('view'),
                    "a_bbox": a_anno.get('bbox'),
                    "a_category": a_anno.get('category'),
                    "a_direction": a_anno.get('direction'),
                    "b_uid": matched_b_anno.get('uid'),
                    "b_view": matched_b_anno.get('view'),
                    "b_bbox": matched_b_anno.get('bbox'),
                    "b_category": matched_b_anno.get('category'),
                    "b_direction": matched_b_anno.get('direction')
                }
            })
            del b_unmatched_copy[matched_b_idx]
        else:
            # 最终A独有，补充溯源信息
            cross_result["final_a_only"].append({
                "annotation": a_anno,
                "trace_info": {
                    "uid": a_anno.get('uid'),
                    "view": a_anno.get('view'),
                    "bbox": a_anno.get('bbox'),
                    "category": a_anno.get('category'),
                    "direction": a_anno.get('direction'),
                    "content": a_anno.get('content')
                }
            })

    # 最终B独有，补充溯源信息
    cross_result["final_b_only"] = [{
        "annotation": b_anno,
        "trace_info": {
            "uid": b_anno.get('uid'),
            "view": b_anno.get('view'),
            "bbox": b_anno.get('bbox'),
            "category": b_anno.get('category'),
            "direction": b_anno.get('direction'),
            "content": b_anno.get('content')
        }
    } for b_anno in b_unmatched_copy]

    return cross_result


def generate_diff_report(a_file: str, b_file: str, output_file: str = "diff_report.json") -> None:
    """生成完整的差异比对报告（含统一的溯源差异详情）"""
    # 加载并分组数据
    a_data = load_json(a_file)
    b_data = load_json(b_file)
    a_groups = group_by_view(a_data)
    b_groups = group_by_view(b_data)

    # 初始化差异报告（新增diff_details统一汇总差异）
    diff_report = {
        "file_info": {
            "base_file": a_file,
            "compare_file": b_file,
            "report_generated_time": str(__import__('datetime').datetime.now())  # 报告生成时间
        },
        "summary": {
            "total_views": 0,  # 总比对view数
            "views_with_diff": 0,  # 同View有差异的view数
            "same_view_matched": 0,  # 同View完全匹配标注数
            "same_view_content_diff": 0,  # 同View内容差异标注数
            "same_view_a_only": 0,  # 同View A独有标注数
            "same_view_b_only": 0,  # 同View B独有标注数
            "cross_view_matched": 0,  # 跨View匹配标注数
            "final_a_only_annotations": 0,  # 最终A独有标注数
            "final_b_only_annotations": 0  # 最终B独有标注数
        },
        "same_view_details": {},  # 同View比对详情（含候选追溯）
        "cross_view_details": {},  # 跨View比对详情
        # 核心新增：统一的差异详情汇总（便于溯源）
        "diff_details": {
            "same_view_content_different": [],  # 同View内容差异（直接修改类）
            "same_view_a_only": [],  # 同View A独有（跨View前）
            "same_view_b_only": [],  # 同View B独有（跨View前）
            "cross_view_matched": [],  # 跨View匹配（view不一致但内容一致）
            "final_a_only": [],  # 最终A独有（无任何匹配，需重点溯源）
            "final_b_only": []  # 最终B独有（无任何匹配，需重点溯源）
        }
    }

    # 同View比对
    all_views = set(a_groups.keys()).union(set(b_groups.keys()))
    diff_report["summary"]["total_views"] = len(all_views)
    global_a_unmatched = []
    global_b_unmatched = []

    for view in all_views:
        a_annos = a_groups.get(view, [])
        b_annos = b_groups.get(view, [])
        # print("______________________________________________________________")
        # print(a_annos)
        # print("______________________________________________________________")
        # print(b_annos)
        # print("______________________________________________________________")
        view_diff = compare_view_annotations(a_annos, b_annos)

        # 更新同View统计
        diff_report["summary"]["same_view_matched"] += len(view_diff["matched"])
        diff_report["summary"]["same_view_content_diff"] += len(view_diff["content_different"])
        diff_report["summary"]["same_view_a_only"] += len(view_diff["a_only"])
        diff_report["summary"]["same_view_b_only"] += len(view_diff["b_only"])
        diff_report["same_view_details"][view] = view_diff

        # 标记有差异的View
        if any([len(view_diff[key]) > 0 for key in ["content_different", "a_only", "b_only"]]):
            diff_report["summary"]["views_with_diff"] += 1

        # 收集未匹配项（用于跨View比对）
        global_a_unmatched.extend(view_diff["a_only"])
        global_b_unmatched.extend(view_diff["b_only"])

        # 核心：将同View差异信息整合到diff_details（溯源专用）
        diff_report["diff_details"]["same_view_content_different"].extend(view_diff["content_different"])
        diff_report["diff_details"]["same_view_a_only"].extend(view_diff["a_only"])
        diff_report["diff_details"]["same_view_b_only"].extend(view_diff["b_only"])

    # 跨View比对
    cross_result = cross_view_match(global_a_unmatched, global_b_unmatched)
    diff_report["summary"]["cross_view_matched"] = len(cross_result["cross_view_matched"])
    diff_report["summary"]["final_a_only_annotations"] = len(cross_result["final_a_only"])
    diff_report["summary"]["final_b_only_annotations"] = len(cross_result["final_b_only"])

    # 整理跨View详情
    diff_report["cross_view_details"] = cross_result
    # 核心：将跨View差异信息整合到diff_details（溯源专用）
    diff_report["diff_details"]["cross_view_matched"].extend(cross_result["cross_view_matched"])
    diff_report["diff_details"]["final_a_only"].extend(cross_result["final_a_only"])
    diff_report["diff_details"]["final_b_only"].extend(cross_result["final_b_only"])

    # 保存报告（ensure_ascii=False保证中文/特殊字符正常）
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(diff_report, f, ensure_ascii=False, indent=2)

    # 控制台输出（突出溯源关键信息）
    print(f"✅ 差异比对报告生成完成！")
    print(f"📊 比对汇总（溯源重点）：")
    print(f"   - 总比对View数：{diff_report['summary']['total_views']}")
    print(f"   - 同View内容差异数：{diff_report['summary']['same_view_content_diff']}（需核对content）")
    print(f"   - 跨View匹配数：{diff_report['summary']['cross_view_matched']}（view不同但内容一致）")
    print(f"   - 最终A独有数：{diff_report['summary']['final_a_only_annotations']}（无匹配，需重点溯源）")
    print(f"   - 最终B独有数：{diff_report['summary']['final_b_only_annotations']}（无匹配，需重点溯源）")
    print(f"📄 报告路径：{output_file}")
    print(f"🔍 溯源关键字段：diff_details下的trace_info（uid/view/bbox）")


if __name__ == "__main__":
    pass
    # 配置文件路径
    # SAMPLE_X_PATH = "../test_process/json_results/736420000_sd_merged_X.json"
    # SAMPLE_Y_PATH = "../test_process/json_results/736420000_sd_merged_Y.json"
    # REPORT_OUTPUT_PATH = "../test_process/json_results/compare_report.json"
    #
    # # 生成差异报告
    # generate_diff_report(SAMPLE_Y_PATH, SAMPLE_X_PATH, REPORT_OUTPUT_PATH)