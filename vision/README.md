# YC Vision — 물품 인식 모델 학습

[프로젝트 홈](../README.md) · [비전 시스템 설계](../docs/ko/05_VISION_DESIGN.md) · [데이터셋 안내](yolo_dataset/README.md)

SAM2로 영상 프레임을 자동 라벨링하고, Ultralytics YOLO instance segmentation 모델을 학습한 뒤 이미지·영상·USB 카메라에서 추론하는 독립 파이프라인입니다. 웹 제어센터·`chan` 서버와는 아직 연결되지 않은 별도 실행 도구입니다.

## 파일과 하위 폴더

| 파일·폴더 | 내용 |
|---|---|
| [sam2_autolabel_video.py](sam2_autolabel_video.py) | SAM2 기반 영상 프레임 자동 라벨링 |
| [train_yolo.py](train_yolo.py) | CUDA GPU 필수 YOLO segmentation 학습 |
| [infer_yolo.py](infer_yolo.py) | CPU 전용 추론 (이미지·영상·USB 카메라) |
| [best.pt](best.pt) | 학습된 최종 가중치 |
| [yolo_dataset/](yolo_dataset/README.md) | 클래스 정의와 데이터셋 분할 설정 |
| [requirements.txt](requirements.txt) | Python 의존성 |

## Classes

| ID | Class |
|---:|---|
| 0 | `car_key` |
| 1 | `lip_balm` |
| 2 | `watch` |

## 사용 방법

Python 3.10 이상을 권장합니다.

```bash
python -m venv .venv
source .venv/bin/activate      # Windows CMD: .venv\Scripts\activate.bat
pip install -r requirements.txt
```

> Raspberry Pi에서는 64-bit Raspberry Pi OS를 권장합니다. PyTorch 설치가 실패하면 사용 중인 Raspberry Pi OS와 Python 버전에 맞는 PyTorch wheel을 먼저 설치하세요.

### 학습

학습은 NVIDIA CUDA GPU를 강제로 사용합니다. CUDA가 없으면 CPU로 자동 전환하지 않고 오류를 발생시킵니다.

```bash
python train_yolo.py                    # 기본: yolo26n-seg.pt, epochs 100, imgsz 640, batch 16, device 0
python train_yolo.py --test-after-train  # 학습 후 test split까지 평가
```

최고 성능 가중치는 `runs/segment/car_key_lip_balm_watch/weights/best.pt`에 저장됩니다.

### 추론 — CPU 전용

`infer_yolo.py`와 `best.pt`를 같은 폴더에 두면 자동으로 가중치를 찾습니다. 라즈베리 파이를 고려해 CPU로 고정되어 있습니다.

```bash
python infer_yolo.py image.jpg
python infer_yolo.py video.mp4
python infer_yolo.py 0        # USB 카메라 index, q 또는 Esc로 종료
```

결과는 `runs/inference/predict/`에 저장됩니다.

### SAM2 자동 라벨링 (선택)

```bash
pip install torch torchvision huggingface-hub
pip install git+https://github.com/facebookresearch/sam2.git
```

`sam2_autolabel_video.py` 상단의 `CLASS_NAME`, `USER_VIDEO_PATH`를 대상에 맞게 수정한 뒤 실행합니다.

## Dataset

YOLO segmentation 라벨 형식(`class_id x1 y1 x2 y2 ... xn yn`)을 사용하며, 클래스별로 약 `train:val:test = 7:2:1` 비율로 분할했습니다.

| Class | Train | Val | Test | Total |
|---|---:|---:|---:|---:|
| `car_key` | 202 | 58 | 28 | 288 |
| `lip_balm` | 210 | 60 | 30 | 300 |
| `watch` | 199 | 57 | 28 | 284 |
| **Total** | **611** | **175** | **86** | **872** |

## 다른 모듈과의 관계

- [chan/yolo_demo.py](../chan/yolo_demo.py)는 사전 학습된 COCO 클래스 `yolo11n.pt`로 실시간 라이브 데모를 보여줍니다. 이 폴더의 `best.pt`는 `car_key`·`lip_balm`·`watch` 전용으로 직접 학습한 별도 모델이며, 두 모델은 아직 통합되지 않았습니다.
- [비전 시스템 설계](../docs/ko/05_VISION_DESIGN.md)의 "단계적 확장" 6단계(`YOLO 등 일반 객체 탐지를 보조 수단으로 추가`)에 해당하는 실제 학습 결과물입니다. marker 기반 좌표 변환·로봇 좌표 연결과는 아직 연결되지 않았습니다.
- 웹 제어센터의 [비전 화면](../views/README.md)은 여전히 `mocks/`의 임의 좌표를 사용합니다. 이 모델의 추론 결과를 화면·`Execution Engine`에 연결하는 작업은 향후 계획입니다.

## 알아둘 점

- 학습 스크립트는 CUDA가 없으면 즉시 오류로 중단됩니다. Raspberry Pi 등 CPU 전용 장치에서는 추론(`infer_yolo.py`)만 실행하세요.
- `yolo_dataset/images/`, `yolo_dataset/labels/`, `runs/`, `sam2_labels/`, `videos/` 등 원본 영상·라벨링 결과·학습 로그는 용량 문제로 저장소에 포함하지 않습니다(`.gitignore` 참고). 필요한 경우 각 담당자가 별도로 보관·공유합니다.
- `best.pt`는 현재 학습된 최종 가중치 1개만 추적합니다. 재학습 시 새 가중치로 덮어쓰기 전에 필요하면 별도 파일명으로 백업하세요.
