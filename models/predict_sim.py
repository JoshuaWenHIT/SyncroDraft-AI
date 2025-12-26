import torch
import torch.backends.cudnn as cudnn
import numpy as np
import pandas as pd
import os

cudnn.benchmark = False
cudnn.deterministic = True

from models.load_config import load_config

config = load_config('./config/config_sim.yaml')
CLASS_NAMES = config['CLASSNAME']
device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")


def predict_sim(model, dataloaders, threshold, scale, output_path, name):
    predict_list = []
    model.eval()
    for batch_img1, batch_img2, paths1, paths2 in dataloaders:
        batch_img1 = batch_img1.to(device)
        batch_img2 = batch_img2.to(device)
        with torch.no_grad():
            outputs1 = model(batch_img1)
            outputs2 = model(batch_img2)
            feat1 = torch.nn.functional.normalize(outputs1, p=2, dim=1)
            feat2 = torch.nn.functional.normalize(outputs2, p=2, dim=1)
            cos_sim = torch.sum(feat1 * feat2, dim=1)
            logits = cos_sim * scale  # scale factor
            probs = torch.sigmoid(logits).cpu().numpy()

        for i in range(len(paths1)):
            is_same = probs[i] > threshold
            predict_list.append({
                'image1': os.path.splitext(os.path.basename(paths1[i]))[0],
                'image2': os.path.splitext(os.path.basename(paths2[i]))[0],
                'similarity_score': probs[i],
                'is_same': is_same,
                'label': 'same' if is_same else 'different'
            })

    df = pd.DataFrame(predict_list)
    csv_path = os.path.join(output_path, f'{name}_predict_sim.csv')
    df.to_csv(csv_path, index=False)