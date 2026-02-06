from utils.image_preprocess import image_preprocess
from utils.PMI_extract import PMI_extract
from tools.merge_json import merge_main
from utils.compare import generate_diff_report
from utils.json_to_excel import json_to_excel
from tools.json_vis import json_vis
import argparse
import os

def get_parse():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--image_path1", type=str, default="./data/image_data/736420000_sd_page_1.png"
    )
    parser.add_argument(
        "--image_path2",
        type=str,
        default="./data/image_data/736420000_sd_revision_page_1.png",
    )
    parser.add_argument("--output_dir", type=str, default="./test_process")
    parser.add_argument("--batch_predict", type=int, default=1)
    parser.add_argument("--alignment_threshold", type=float, default=0.05)
    parser.add_argument("--similarity_threshold", type=float, default=0.9)
    args = parser.parse_args()
    return args

# --- 新增封装函数 ---
def run_compare_logic(args):
    """
    核心比对逻辑封装。
    args 可以是 argparse.Namespace 对象，也可以是 Django 构造的模拟对象。
    """
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)

    # 1. 图像预处理与视图分割
    image_preprocess(
        args.image_path1,
        args.image_path2,
        args.output_dir,
        args.batch_predict,
        args.alignment_threshold,
        args.similarity_threshold,
    )

    # 2. 中间特征提取过程
    image_fold1 = os.path.join(
        args.output_dir,
        "views_for_detection",
        os.path.basename(args.image_path1).split(".")[0],
    )
    image_fold2 = os.path.join(
        args.output_dir,
        "views_for_detection",
        os.path.basename(args.image_path2).split(".")[0],
    )
    PMI_extract(image_fold1, image_fold2, args.output_dir)

    # 3. 合并 JSON 与生成比对报告
    # 注意：这里 image_prefix 的逻辑依赖于你的文件名格式（如 736420000_...）
    image_prefix = os.path.basename(args.image_path1).split("_")[0] + "_sd"
    json_results_path = os.path.join(args.output_dir, "json_results")
    final_results_path = os.path.join(args.output_dir, "final_results")
    report_json_path = os.path.join(
        json_results_path, "{}_compare_report.json".format(image_prefix)
    )
    
    merge_main(image_prefix, json_results_path=json_results_path)

    # -------------------------------------------------------------------------
    # 👇【修改2】核心路径逻辑：判断是 Django 调用还是本地运行
    # -------------------------------------------------------------------------
    # 默认路径逻辑 (保持原样)
    default_report_path = os.path.join(
        json_results_path, "{}_compare_report.json".format(image_prefix)
    )

    # 检查 args 里是否有 views.py 传过来的 output_file
    if hasattr(args, 'output_file') and args.output_file:
        # 如果有，优先使用它！这样 views.py 才能找到文件并读取统计数据
        report_json_path = args.output_file
        #log_utils.log(f"检测到指定输出路径，报告将保存至: {report_json_path}")
    else:
        # 如果没有（本地单独运行），使用默认逻辑
        report_json_path = default_report_path
        #log_utils.log(f"使用默认输出路径: {report_json_path}")
    # -------------------------------------------------------------------------

    # 4. 生成差异报告与 Excel
    generate_diff_report(
        a_file=os.path.join(json_results_path, "{}_merged_Y.json".format(image_prefix)),
        b_file=os.path.join(json_results_path, "{}_merged_X.json".format(image_prefix)),
        output_file=report_json_path,
    )
    
    json_to_excel(
        json_file=report_json_path,
        excel_file=os.path.join(
            final_results_path, "{}_merged.xlsx".format(image_prefix)
        ),
    )

    # 5. 结果可视化
    image_folder = os.path.dirname(args.image_path1)
    output_folder = os.path.join(args.output_dir, "annotated_images")
    position_file_folder = os.path.join(args.output_dir, "sub_views")
    json_vis(report_json_path, image_folder, output_folder, position_file_folder)
    
    return True

# --- 保持原有入口 ---
if __name__ == "__main__":
    args = get_parse()
    run_compare_logic(args)