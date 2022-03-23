import torch

import pickle as pk
from torchvision.transforms.functional import resize
from torchvision.transforms import transforms as trn
from torch.utils.data import Dataset, DataLoader

import numpy as np
from extractor.models import MobileNet_Local


def resize_transform(size):
    return trn.Compose([
        trn.Resize((size, size)),
        trn.ToTensor(),
        trn.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])


class ListDataset(Dataset):
    def __init__(self, items, transform=None):
        super(ListDataset, self).__init__()
        self.items = items
        self.transform = transform

    def __getitem__(self, idx):
        item = self.items[idx]
        if self.transform is not None:
            item = self.transform(item)

        return item

    def __len__(self):
        return len(self.items)


class Extractor:
    def __init__(self, ckpt, cluster, batch=32, segment_length=5):
        self.model = MobileNet_Local().cuda()
        self.model.load_state_dict(torch.load(ckpt)['model_state_dict'])
        self.model.eval()

        self.loader = DataLoader(dataset=ListDataset(items=[],
                                                     transform=resize_transform(224)),
                                 batch_size=batch,
                                 shuffle=False)

        self.seg_len = segment_length

        self.kmeans = pk.load(open(cluster, "rb"))

    @torch.no_grad()
    def inference(self, images):
        self.loader.dataset.items = images

        features = np.concatenate([self.model(f.cuda()).cpu().numpy() for f in self.loader])  # [N, C, H, W]
        features = np.transpose(features, (0, 2, 3, 1))  # [N, H, W, C]
        features = features.reshape(-1, features.shape[3])  # [N*H*W, C]

        nearest_centroid = self.kmeans.predict(features)  # [N*H*W,]
        nearest_centroid = nearest_centroid.reshape(-1, 49)  # [N, H*W]

        bow = np.array([np.bincount(nc, minlength=20000) for nc in nearest_centroid]).astype(np.float32)  # [N, K]
        if bow.shape[0] % self.seg_len:
            repeat = self.seg_len - bow.shape[0] % self.seg_len
            bow = np.concatenate([bow, np.tile(bow[-1], reps=[repeat, 1])])

        bow = bow.reshape(-1, self.seg_len, bow.shape[-1])  # [N/S, S, K]
        bow_seg = np.sum(bow, axis=1)  # [N/S, K]
        bow_seg = bow_seg / (np.linalg.norm(bow_seg, ord=2, axis=1, keepdims=True) + 1e-6)

        return bow_seg
