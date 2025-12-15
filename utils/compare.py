import json
import numpy as np
from Levenshtein import ratio as levenshtein_ratio
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from typing import Dict, List, Tuple, Optional

# 核心配置（可根据业务调整）
CORE_KEYS = ["uid", "category", "content", "embedding"]
FIELD_WEIGHTS = {  # 各字段在综合评分中的权重
    "category": 0.4,
    "content": 0.3,
    "embedding": 0.3
}
SIMILARITY_THRESHOLD = 0.8  # 综合相似度阈值，低于则判定为不匹配
TEXT_EMPTY_DEFAULT = 0.0  # content为空时的默认相似度
EMBEDDING_EMPTY_DEFAULT = 0.0  # embedding为空时的默认相似度


def load_json(file_path: str) -> List[Dict]:
    """加载JSON文件，校验核心字段"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        raise ValueError(f"加载JSON文件失败：{file_path}，错误：{str(e)}")

    # 校验每个标注的核心字段
    for idx, item in enumerate(data):
        missing_keys = [k for k in CORE_KEYS if k not in item]
        if missing_keys:
            raise ValueError(f"第{idx}个标注缺失核心字段：{missing_keys}")

    return data


def text_similarity(text1: str, text2: str) -> float:
    """
    计算文本相似度（融合编辑距离+TF-IDF余弦相似度）
    :param text1: 图纸A的content
    :param text2: 图纸B的content
    :return: 0-1之间的相似度值
    """
    # 处理空文本
    if not text1 or not text2:
        return TEXT_EMPTY_DEFAULT

    # 编辑距离相似度（字符级）
    lev_sim = levenshtein_ratio(text1.strip(), text2.strip())

    # TF-IDF余弦相似度（词级，需至少2个字符）
    if len(text1) < 2 or len(text2) < 2:
        tfidf_sim = lev_sim
    else:
        vectorizer = TfidfVectorizer(ngram_range=(1, 2))
        try:
            tfidf_matrix = vectorizer.fit_transform([text1, text2])
            tfidf_sim = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        except:
            tfidf_sim = lev_sim

    # 融合两种相似度（平衡字符级和词级特征）
    return (lev_sim + tfidf_sim) / 2


def embedding_cosine_similarity(emb1: List[float], emb2: List[float]) -> float:
    """
    计算embedding向量的余弦相似度
    :param emb1: 图纸A的embedding（列表形式）
    :param emb2: 图纸B的embedding（列表形式）
    :return: 0-1之间的相似度值
    """
    # 处理空embedding
    if not emb1 or not emb2:
        return EMBEDDING_EMPTY_DEFAULT

    # 转numpy数组并归一化（避免长度影响）
    vec1 = np.array(emb1).reshape(1, -1)
    vec2 = np.array(emb2).reshape(1, -1)

    # 归一化
    vec1 = vec1 / np.linalg.norm(vec1) if np.linalg.norm(vec1) != 0 else vec1
    vec2 = vec2 / np.linalg.norm(vec2) if np.linalg.norm(vec2) != 0 else vec2

    # 计算余弦相似度
    sim = cosine_similarity(vec1, vec2)[0][0]
    # 确保相似度在0-1之间（避免浮点误差导致负数）
    return max(0.0, min(1.0, sim))


def compare_single_annotation(anno_a: Dict, anno_b: Dict) -> Dict:
    """
    比对单个标注（A/B）的三个核心字段，计算综合评分
    :param anno_a: 图纸A的单个标注字典
    :param anno_b: 图纸B的单个标注字典
    :return: 比对结果字典
    """
    # 1. category比对（精确匹配）
    category_match = anno_a["category"] == anno_b["category"]
    category_sim = 1.0 if category_match else 0.0

    # 2. content比对（文本相似度）
    content_sim = text_similarity(anno_a["content"], anno_b["content"])

    # 3. embedding比对（向量余弦相似度）
    embedding_sim = embedding_cosine_similarity(anno_a["embedding"], anno_b["embedding"])

    # 4. 综合评分（加权求和）
    total_sim = (
            category_sim * FIELD_WEIGHTS["category"]
            + content_sim * FIELD_WEIGHTS["content"]
            + embedding_sim * FIELD_WEIGHTS["embedding"]
    )

    # 判定是否匹配（基于阈值）
    is_match = total_sim >= SIMILARITY_THRESHOLD

    return {
        "uid": anno_a["uid"],
        "category": {
            "a": anno_a["category"],
            "b": anno_b["category"],
            "match": category_match,
            "similarity": category_sim
        },
        "content": {
            "a": anno_a["content"],
            "b": anno_b["content"],
            "similarity": round(content_sim, 4)
        },
        "embedding": {
            "similarity": round(embedding_sim, 4)
        },
        "total_similarity": round(total_sim, 4),
        "is_match": is_match
    }


def compare_two_drawings(json_a_path: str, json_b_path: str) -> Dict:
    """
    比对两个图纸的JSON文件，生成完整比对报告
    :param json_a_path: 图纸A的JSON路径
    :param json_b_path: 图纸B的JSON路径
    :return: 完整比对报告
    """
    # 1. 加载并校验数据
    data_a = load_json(json_a_path)
    data_b = load_json(json_b_path)

    # 2. 构建UID到标注的映射（方便快速匹配）
    uid2anno_a = {anno["uid"]: anno for anno in data_a}
    uid2anno_b = {anno["uid"]: anno for anno in data_b}

    # 3. 提取所有UID，分类处理
    all_uids = set(uid2anno_a.keys()).union(set(uid2anno_b.keys()))
    missing_in_a = [uid for uid in all_uids if uid not in uid2anno_a]  # B有A无
    missing_in_b = [uid for uid in all_uids if uid not in uid2anno_b]  # A有B无
    common_uids = [uid for uid in all_uids if uid in uid2anno_a and uid in uid2anno_b]  # 共有的UID

    # 4. 比对共有UID的标注
    common_compare_results = []
    for uid in common_uids:
        res = compare_single_annotation(uid2anno_a[uid], uid2anno_b[uid])
        common_compare_results.append(res)

    # 5. 统计整体结果
    total_annotations = len(all_uids)
    matched_count = sum([1 for res in common_compare_results if res["is_match"]])
    common_count = len(common_uids)
    match_rate = matched_count / common_count if common_count > 0 else 0.0
    avg_similarity = np.mean([res["total_similarity"] for res in common_compare_results]) if common_count > 0 else 0.0

    # 6. 生成最终报告
    report = {
        "summary": {
            "total_annotations": total_annotations,
            "common_annotations": common_count,
            "missing_in_a": missing_in_a,  # B有A无的UID
            "missing_in_b": missing_in_b,  # A有B无的UID
            "matched_count": matched_count,
            "match_rate": round(match_rate, 4),
            "average_similarity": round(avg_similarity, 4),
            "overall_match": match_rate >= SIMILARITY_THRESHOLD  # 整体是否匹配（基于匹配率）
        },
        "detail": common_compare_results
    }

    return report


def save_report(report: Dict, save_path: str):
    """保存比对报告到JSON文件"""
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=4)


# ------------------- 示例调用 -------------------
if __name__ == "__main__":
    # 替换为实际的JSON文件路径
    JSON_A_PATH = "drawing_a.json"
    JSON_B_PATH = "drawing_b.json"
    REPORT_SAVE_PATH = "drawing_compare_report.json"

    try:
        # 执行比对
        compare_report = compare_two_drawings(JSON_A_PATH, JSON_B_PATH)

        # 打印摘要信息
        print("=== 图纸比对摘要 ===")
        print(f"总标注数：{compare_report['summary']['total_annotations']}")
        print(f"共有标注数：{compare_report['summary']['common_annotations']}")
        print(f"A缺失的UID：{compare_report['summary']['missing_in_a']}")
        print(f"B缺失的UID：{compare_report['summary']['missing_in_b']}")
        print(f"匹配数：{compare_report['summary']['matched_count']}")
        print(f"匹配率：{compare_report['summary']['match_rate']:.2%}")
        print(f"平均综合相似度：{compare_report['summary']['average_similarity']:.2%}")
        print(f"整体是否匹配：{compare_report['summary']['overall_match']}")

        # 保存详细报告
        save_report(compare_report, REPORT_SAVE_PATH)
        print(f"\n详细比对报告已保存至：{REPORT_SAVE_PATH}")

    except Exception as e:
        print(f"比对失败：{str(e)}")