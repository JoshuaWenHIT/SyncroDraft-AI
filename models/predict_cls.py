import torch
import torch.backends.cudnn as cudnn
import numpy as np
import pandas as pd
import PIL.Image as Image
import os

cudnn.benchmark = False
cudnn.deterministic = True

from models.load_config import load_config

config = load_config("./config/config_cls.yaml")
CLASS_NAMES = config["CLASSNAME"]
device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")


def save_image_to_folder(image, folder_path, filename):
    """
    将图片保存到指定文件夹中。
    :param image: PIL Image object
    :param folder_path: 目标文件夹路径
    :param filename: 文件名
    """
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    image.save(os.path.join(folder_path, filename))


def predict_cls(model, dataloaders, output_dir):
    predict_list = []
    path_list = []
    for images, image_paths in dataloaders:
        images = images.to(device)

        with torch.no_grad():
            outputs = model(images)
            _, preds = torch.max(outputs, 1)

        predict_list += [CLASS_NAMES[i] for i in list(preds.cpu().detach().numpy())]
        path_list += [image_paths[i] for i in range(len(image_paths))]

    for i in range(len(path_list)):
        pred_class = predict_list[i]
        original_image = Image.open(path_list[i])
        pic_name = os.path.splitext(os.path.basename(path_list[i]))[0]
        save_image_to_folder(
            original_image, os.path.join(output_dir, pred_class), f"{pic_name}.png"
        )
