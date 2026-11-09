# -*- coding: utf-8 -*-
"""人脸检测：YuNet 深度模型（主）+ Haar 级联（兜底）
   输出归一化人脸框，用于裁剪定位 + 衣服区采样
"""
import os
import numpy as np
import cv2

HERE = os.path.dirname(os.path.abspath(__file__))
CV = os.path.join(HERE, "cvdata")
YUNET = os.path.join(CV, "yunet.onnx")

_haar = None
for fn in ("haarcascade_frontalface_default.xml", "haarcascade_frontalface_alt2.xml"):
    p = os.path.join(cv2.data.haarcascades, fn)
    if os.path.exists(p):
        c = cv2.CascadeClassifier(p)
        if not c.empty():
            _haar = c
            break


def _yunet(img_bgr, minsz):
    if not os.path.exists(YUNET) or os.path.getsize(YUNET) < 50000:
        return []
    h, w = img_bgr.shape[:2]
    try:
        det = cv2.FaceDetectorYN.create(YUNET, "", (w, h),
                                        score_threshold=0.45, nms_threshold=0.3, top_k=20)
        det.setInputSize((w, h))
        _, faces = det.detect(img_bgr)
    except Exception:
        return []
    if faces is None:
        return []
    out = []
    for f in faces:
        x, y, fw, fh = f[:4]
        if fw < minsz or fh < minsz:
            continue
        out.append((float(x), float(y), float(fw), float(fh), float(f[14])))
    return out


def _haar_det(img_gray, minsz):
    if _haar is None:
        return []
    h, w = img_gray.shape[:2]
    ms = int(max(16, round(minsz)))
    mx = int(min(w, h) * 0.92)
    if mx <= ms:
        return []
    faces = _haar.detectMultiScale(img_gray, scaleFactor=1.07, minNeighbors=6,
                                   minSize=(ms, ms), maxSize=(mx, mx))
    return [(float(x), float(y), float(fw), float(fh), 0.5) for x, y, fw, fh in faces]


def detect_face(path_or_im, min_frac=0.012, want_single=True):
    """返回 dict（最大/最可信的一张）或 None"""
    if isinstance(path_or_im, str):
        img = cv2.imread(path_or_im)
        if img is None:
            return None
    else:
        img = np.asarray(path_or_im.convert("RGB"))[:, :, ::-1].copy()
    H0, W0 = img.shape[:2]
    if min(H0, W0) < 60:
        return None
    sc = 1000.0 / max(H0, W0)
    if sc < 1:
        img = cv2.resize(img, (int(W0 * sc), int(H0 * sc)), interpolation=cv2.INTER_AREA)
    h, w = img.shape[:2]
    minsz = max(16.0, min(w, h) * min_frac)

    found = _yunet(img, minsz)
    how = "yunet"
    if not found:
        g = cv2.equalizeHist(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY))
        found = _haar_det(g, minsz)
        how = "haar"
    if not found:
        return None

    # 选“最大且靠上”的那张（主角通常更近）
    def score(f):
        x, y, fw, fh, s = f
        return (fw * fh) ** 0.5 * (0.55 + 0.45 * s) * (1.0 - (y / h) * 0.30)

    x, y, fw, fh, s = max(found, key=score)
    return {"fx": float((x + fw / 2) / w), "fy": float((y + fh / 2) / h),
            "fw": float(fw / w), "fh": float(fh / h),
            "farea": float(fw * fh / (w * h)),
            "chin": float(min(0.995, (y + fh * 1.10) / h)),
            "ratio": float(fw / fh) if fh > 0 else 1.0,
            "n": len(found), "how": how, "score": round(s, 3)}


def cloth_region(d):
    """由人脸框推衣服采样区"""
    half = max(d["fw"] * 1.10, 0.15)
    x0 = max(0.0, d["fx"] - half); x1 = min(1.0, d["fx"] + half)
    y0 = min(0.995, d["chin"] + 0.010)
    y1 = min(1.0, d["chin"] + 0.52)
    if y1 - y0 < 0.05:
        y0, y1 = 0.40, 0.90
    return x0, y0, x1, y1
