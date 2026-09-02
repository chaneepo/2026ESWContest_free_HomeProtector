# 데이터셋 설정

[프로젝트 홈](../../README.md) · [상위 안내](../README.md)

YOLO segmentation 학습에 사용하는 클래스 정의와 분할 경로 설정입니다.

## 파일과 하위 폴더

| 파일·폴더 | 내용 |
|---|---|
| [data.yaml](data.yaml) | 클래스 이름과 `images/{train,val,test}` 경로 정의 |

## 사용 방법

[train_yolo.py](../train_yolo.py)가 이 파일을 읽어 학습 대상 클래스와 데이터 경로를 구성합니다. 실제 이미지는 `images/train`, `images/val`, `images/test`에, 라벨은 `labels/{train,val,test}`에 두는 표준 YOLO 폴더 구조를 가정합니다.

## 알아둘 점

원본 이미지·라벨 파일(`images/`, `labels/`)은 용량 문제로 저장소에 포함하지 않았습니다. 클래스별 장수와 분할 비율은 [상위 README의 Dataset 표](../README.md#dataset)를 참고하세요.
