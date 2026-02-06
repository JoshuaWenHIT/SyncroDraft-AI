import torch
from torchvision import transforms
from torch.utils.data import Dataset, DataLoader
import torch.backends.cudnn as cudnn

from models.load_model import load_model
from models.load_config import load_config
from models.predict_cls import predict_cls
from models.predict_sim import predict_sim
from utils.pic_seg import process_image
from utils.view_seg import extract_subviews
from utils.subview_cls import load_positions, classify_three_views

import itertools
import argparse
import os
from PIL import Image

import warnings

warnings.filterwarnings("ignore")

cudnn.benchmark = False
cudnn.deterministic = True

config = load_config("./config/config_cls.yaml")
IMG_SIZE = config["DATA"]["IMG_SIZE"] if config["DATA"]["IMG_SIZE"] else (224, 224)
# CLASS_NAMES = config['CLASSNAME']
device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

data_transforms = transforms.Compose(
    [
        transforms.Resize(IMG_SIZE),  # resize
        # transforms.RandomAdjustSharpness(5.0), #sharpen image
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ]
)


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


class ClassDataset(Dataset):
    def __init__(self, image_paths, transform):
        self.image_paths = image_paths
        self.transform = transform

    def __len__(self):
        return len(self.image_paths)

    def __getitem__(self, idx):
        # path = self.image_paths[idx]
        image = Image.open(self.image_paths[idx])
        image = self.transform(image)
        return image, self.image_paths[idx]


class PairDataset(Dataset):
    def __init__(self, paths1, paths2, transform):
        assert len(paths1) == len(
            paths2
        ), f"Number of images in img1 ({len(paths1)}) != img2 ({len(paths2)})"
        self.paths1 = paths1
        self.paths2 = paths2
        self.transform = transform

    def __len__(self):
        return len(self.paths1)

    def __getitem__(self, idx):
        img1 = Image.open(self.paths1[idx])
        img2 = Image.open(self.paths2[idx])
        img1 = self.transform(img1)
        img2 = self.transform(img2)
        return img1, img2, self.paths1[idx], self.paths2[idx]


def main(image_path, output_path, predict_batch, align_threshold):
    # 1. 分割视图区域和非视图区域
    image_name = image_path.rsplit("/", 1)[-1]
    image_first_name = os.path.splitext(image_name)[0]
    output_path_segmentation = os.path.join(
        output_path, "segmentation", image_first_name
    )
    print(f"Processing {image_name}")
    process_image(image_path, output_path_segmentation)

    # 2. 提取子视图
    output_path_subviews = os.path.join(output_path, "sub_views", image_first_name)
    for filename in os.listdir(output_path_segmentation):
        # ext = os.path.splitext(filename)[1].lower()
        seg_first_name = os.path.splitext(filename)[0]
        seg_first_word = seg_first_name.split("_")[0]
        if seg_first_word == "view":
            print(f"Processing {filename}")
            segmentation_path = os.path.join(output_path_segmentation, filename)
            extract_subviews(segmentation_path, seg_first_name, output_path_subviews)

    # 3. 子视图分类
    class_model = load_model("./config/config_cls.yaml")
    class_model = class_model.to(device)
    class_model.eval()

    if os.path.isdir(output_path_subviews):
        view_paths = [
            os.path.join(output_path_subviews, i)
            for i in os.listdir(output_path_subviews)
            if i.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".gif"))
        ]
    elif os.path.isfile(output_path_subviews):
        view_paths = [output_path_subviews]

    output_path_class = os.path.join(output_path, "classified_views", image_first_name)
    class_dataset = ClassDataset(view_paths, data_transforms)
    class_dataloaders = DataLoader(
        class_dataset, batch_size=predict_batch, shuffle=False
    )
    predict_cls(class_model, class_dataloaders, output_path_class)
    print(
        f"Classification completed for {image_name}, results saved in {output_path_class}"
    )

    # 4. 三视图和截面图处理
    output_path_for_det = os.path.join(
        output_path, "views_for_detection", image_first_name
    )
    position_file_path = os.path.join(output_path_subviews, "positions.txt")
    section_path = os.path.join(output_path_class, "section_subviews")
    three_view_path = os.path.join(output_path_class, "three_view_subviews")
    alignment_threshold = align_threshold
    if not os.path.exists(output_path_for_det):
        os.makedirs(output_path_for_det)

    # 加载坐标
    pos_map = load_positions(position_file_path)
    if not pos_map:
        print("No position data loaded. Exiting.")
        return

    # 处理 Section Subviews (剖面图)
    if os.path.exists(section_path):
        section_files = [
            f for f in os.listdir(section_path) if f.lower().endswith(".png")
        ]
        for fname in section_files:
            # Section 直接标记
            section_image = Image.open(os.path.join(section_path, fname))
            section_image_name = os.path.splitext(fname)[0]
            section_image.save(
                os.path.join(output_path_for_det, f"{section_image_name}_section.png")
            )
        print(f"Processed {len(section_files)} section views.")

    # 处理 Three View Subviews (三视图)
    if os.path.exists(three_view_path):
        three_view_files = [
            f for f in os.listdir(three_view_path) if f.lower().endswith(".png")
        ]

        if len(three_view_files) > 0:
            # 进行几何分类
            classification = classify_three_views(
                three_view_files, pos_map, alignment_threshold
            )

            # 保存结果
            for fname, v_type in classification.items():
                three_view_image = Image.open(os.path.join(three_view_path, fname))
                three_view_image_name = os.path.splitext(fname)[0]
                three_view_image.save(
                    os.path.join(
                        output_path_for_det, f"{three_view_image_name}_{v_type}.png"
                    )
                )

            print(f"Processed {len(three_view_files)} three-view files.")

    print(f"All done. Results saved in {output_path_for_det}")

    return output_path_for_det


def similarity_predict(
    image_path1, image_path2, output_path, predict_batch, sim_threshold, name
):
    output_path_sim = os.path.join(output_path, "similarity_results")
    if not os.path.exists(output_path_sim):
        os.makedirs(output_path_sim)

    sim_model = load_model("./config/config_sim.yaml")
    sim_model = sim_model.to(device)
    sim_model.eval()

    files1 = sorted([f for f in os.listdir(image_path1)])
    files2 = sorted([f for f in os.listdir(image_path2)])

    if not files1 or not files2:
        raise ValueError("One or both folders are empty!")

    paths1, paths2 = [], []
    for f1, f2 in itertools.product(files1, files2):
        paths1.append(os.path.join(image_path1, f1))
        paths2.append(os.path.join(image_path2, f2))

    print(f"Found {len(paths1)} image pairs to compare.")

    sim_dataset = PairDataset(paths1, paths2, data_transforms)
    sim_dataloaders = DataLoader(sim_dataset, batch_size=predict_batch, shuffle=False)
    predict_sim(
        sim_model,
        sim_dataloaders,
        threshold=sim_threshold,
        scale=10.0,
        output_path=output_path_sim,
        name=name,
    )
    print(
        f"Predict completed! Result is saved in {output_path_sim}/{name}_predict_sim.csv"
    )


def image_preprocess(
    image_path1, image_path2, output_path, predict_batch, align_threshold, sim_threshold
):
    # args = get_parse()
    # if not os.path.exists(args.output_dir):
    #     os.makedirs(args.output_dir)
    print("=========================================")
    det_path1 = main(image_path1, output_path, predict_batch, align_threshold)
    print("=========================================")
    det_path2 = main(image_path2, output_path, predict_batch, align_threshold)
    print("=========================================")

    name_for_sim = os.path.basename(det_path1)
    name_for_sim = name_for_sim.rsplit("_", 2)[0]

    similarity_predict(
        det_path1, det_path2, output_path, predict_batch, sim_threshold, name_for_sim
    )


if __name__ == "__main__":
    args = get_parse()
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)

    image_preprocess(
        args.image_path1,
        args.image_path2,
        args.output_dir,
        args.batch_predict,
        args.alignment_threshold,
        args.similarity_threshold,
    )

    # print("=========================================")
    # det_path1 = main(args.image_path1, args.output_dir, args.batch_predict, args.alignment_threshold)
    # print("=========================================")
    # det_path2 = main(args.image_path2, args.output_dir, args.batch_predict, args.alignment_threshold)
    # print("=========================================")
    #
    # name_for_sim = os.path.basename(det_path1)
    # name_for_sim = name_for_sim.rsplit('_', 2)[0]
    #
    # # 5. 相似度预测
    # output_path_sim = os.path.join(args.output_dir, "similarity_results")
    # if not os.path.exists(output_path_sim):
    #     os.makedirs(output_path_sim)
    #
    # sim_model = load_model('./config/config_sim.yaml')
    # sim_model = sim_model.to(device)
    # sim_model.eval()
    #
    # files1 = sorted([f for f in os.listdir(det_path1)])
    # files2 = sorted([f for f in os.listdir(det_path2)])
    #
    # if not files1 or not files2:
    #     raise ValueError("One or both folders are empty!")
    #
    # paths1, paths2 = [], []
    # for f1, f2 in itertools.product(files1, files2):
    #     paths1.append(os.path.join(det_path1, f1))
    #     paths2.append(os.path.join(det_path2, f2))
    #
    # print(f"Found {len(paths1)} image pairs to compare.")
    #
    # sim_dataset = PairDataset(paths1, paths2, data_transforms)
    # sim_dataloaders = DataLoader(sim_dataset, batch_size=args.batch_predict, shuffle=False)
    # predict_sim(sim_model, sim_dataloaders, threshold=args.similarity_threshold, scale=10.0,
    #             output_path=output_path_sim, name=name_for_sim)
    # print(f"Predict completed! Result is saved in {output_path_sim}/{name_for_sim}_predict_sim.csv")
