import time

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
    parser.add_argument('--image_path1', type=str, default='./data/image_data/740601001_sd_page_1.png')
    parser.add_argument('--image_path2', type=str, default='./data/image_data/740601001_sd_revision_1_page_1.png')
    parser.add_argument('--image_path3', type=str, default='./data/image_data/740601001_sd_revision_2_page_1.png')
    parser.add_argument('--output_dir', type=str, default='./test_process')
    parser.add_argument('--batch_predict', type=int, default=1)
    parser.add_argument('--alignment_threshold', type=float, default=0.05)
    parser.add_argument('--similarity_threshold', type=float, default=0.9)
    args = parser.parse_args()
    return args
    # 736420000
    # 1715761214

if __name__ == '__main__':
    # time.time()
    start_time = time.time()
    args = get_parse()
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)

    # 输入3张对比图像处理，将工程图纸中视图的部分分割并预处理，给第二阶段目标检测使用
    # 同时，将两张工程图纸对应的三视图和截面图比对相似度，并保存到csv文件
    image_preprocess(args.image_path1, args.image_path2, args.image_path3, args.output_dir, args.batch_predict, args.alignment_threshold, args.similarity_threshold)

    # 中间为目标检测、箭头方向检测、OCR提取、json生成等过程
    image_fold1 = os.path.join(args.output_dir, "views_for_detection" ,os.path.basename(args.image_path1).split('.')[0])
    image_fold2 = os.path.join(args.output_dir, "views_for_detection", os.path.basename(args.image_path2).split('.')[0])
    image_fold3 = os.path.join(args.output_dir, "views_for_detection", os.path.basename(args.image_path3).split('.')[0])
    PMI_extract(image_fold1, image_fold2, image_fold3, args.output_dir)

    # 合并json，获取比对结果，输出比对结果表格
    image_prefix = args.image_path1.split('/')[-1].split('_')[0] + '_sd'
    json_results_path = os.path.join(args.output_dir, "json_results")
    final_results_path = os.path.join(args.output_dir, "final_results")
    report_json_path_1 = os.path.join(json_results_path, "{}_compare_report_X-Y.json".format(image_prefix))
    report_json_path_2 = os.path.join(json_results_path, "{}_compare_report_X-Z.json".format(image_prefix))
    report_json_path_3 = os.path.join(json_results_path, "{}_compare_report_Y-Z.json".format(image_prefix))
    merge_main(image_prefix, json_results_path=json_results_path)

    # 需要注意，a_file的输入是带有"revision"的修改图片的json文件，
    # b_file的输入是没有修改的图片的json文件
    generate_diff_report(
        a_file=os.path.join(json_results_path, "{}_merged_Y.json".format(image_prefix)),
        b_file=os.path.join(json_results_path, "{}_merged_X.json".format(image_prefix)),
        output_file=report_json_path_1
    )

    generate_diff_report(
        a_file=os.path.join(json_results_path, "{}_merged_Z.json".format(image_prefix)),
        b_file=os.path.join(json_results_path, "{}_merged_X.json".format(image_prefix)),
        output_file=report_json_path_2
    )

    generate_diff_report(
        a_file=os.path.join(json_results_path, "{}_merged_Z.json".format(image_prefix)),
        b_file=os.path.join(json_results_path, "{}_merged_Y.json".format(image_prefix)),
        output_file=report_json_path_3
    )

    json_to_excel(
        json_file=report_json_path_1,
        excel_file=os.path.join(final_results_path, "{}_merged_X-Y.xlsx".format(image_prefix))
    )

    json_to_excel(
        json_file=report_json_path_2,
        excel_file=os.path.join(final_results_path, "{}_merged_X-Z.xlsx".format(image_prefix))
    )

    json_to_excel(
        json_file=report_json_path_3,
        excel_file=os.path.join(final_results_path, "{}_merged_Y-Z.xlsx".format(image_prefix))
    )
    # compare_report.json转到原始大图比对结果可视化
    image_folder = os.path.dirname(args.image_path1)
    output_folder_1 = os.path.join(args.output_dir, "annotated_images/X-Y")
    output_folder_2 = os.path.join(args.output_dir, "annotated_images/X-Z")
    output_folder_3 = os.path.join(args.output_dir, "annotated_images/Y-Z")
    position_file_folder = os.path.join(args.output_dir, "sub_views")
    json_vis(report_json_path_1, image_folder, output_folder_1, position_file_folder)
    json_vis(report_json_path_2, image_folder, output_folder_2, position_file_folder)
    json_vis(report_json_path_3, image_folder, output_folder_3, position_file_folder)
    end_time = time.time()
    time_elapsed = end_time - start_time
    print("Time elapsed: {}".format(time_elapsed))
