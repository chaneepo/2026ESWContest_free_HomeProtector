# CARE-PACK 카메라 촬영·SAM2 마스킹 실행 가이드

이 문서는 U20CAM으로 물품 영상을 촬영하고, 녹화 결과를 확인한 뒤 SAM2로 사진 한
장을 마스킹하는 전체 과정을 설명합니다. 모든 프로젝트 코드는
`/home/tracelab/chan`에 둡니다.

## 1. 라즈베리파이 접속

현재 사용 중인 주소가 `192.168.0.73`일 때 다음과 같이 접속합니다.

```bash
ssh tracelab@192.168.0.73
cd /home/tracelab/chan
```

IP가 바뀌면 실제 라즈베리파이 주소로 변경합니다. 비밀번호는 Git이나 문서에
기록하지 않습니다.

## 2. 카메라 연결 확인

```bash
v4l2-ctl --list-devices
v4l2-ctl -d /dev/video0 --list-formats-ext
```

U20CAM이 `/dev/video0`에 나타나고 `MJPG 1280x720 30fps`가 표시되면 현재 설정을
그대로 사용할 수 있습니다.

카메라 데이터 수신만 간단히 검사하려면:

```bash
v4l2-ctl -d /dev/video0 \
  --set-fmt-video=width=1280,height=720,pixelformat=MJPG \
  --set-parm=30

v4l2-ctl -d /dev/video0 \
  --stream-mmap=4 \
  --stream-count=100 \
  --stream-to=/dev/null
```

## 3. 실시간 카메라 확인과 사진 저장

라즈베리파이 데스크톱에 로그인된 상태에서 실행합니다.

```bash
cd /home/tracelab/chan
python3 media_viewer.py --camera 0
```

- `s`: 현재 원본 프레임을 사진으로 저장
- `q` 또는 `ESC`: 종료

사진은 `/home/tracelab/carepack-dataset/snapshots`에 저장됩니다. 같은 사용자의 SSH
세션에서 실행하면 뷰어가 활성 그래픽 세션을 자동으로 찾아 라즈베리파이 모니터에
창을 표시합니다.

## 4. 물품 영상 촬영

아래는 립밤을 45초 동안 촬영하는 예시입니다.

```bash
mkdir -p /home/tracelab/carepack-dataset/raw/lip_balm

ffmpeg -nostdin \
  -f v4l2 \
  -input_format mjpeg \
  -video_size 1280x720 \
  -framerate 30 \
  -i /dev/video0 \
  -t 45 \
  -c:v copy \
  /home/tracelab/carepack-dataset/raw/lip_balm/lip_balm_01.mkv
```

다른 물품은 폴더와 파일 이름만 변경합니다.

```text
raw/medication/medication_01.mkv
raw/car_key/car_key_01.mkv
raw/lipstick/lipstick_01.mkv
raw/lip_balm/lip_balm_01.mkv
```

같은 물품을 다시 촬영할 때 기존 파일을 덮어쓰지 말고 `_02`, `_03`처럼 번호를
늘립니다.

촬영할 때는 다음을 지킵니다.

- 대상이 화면 밖으로 잘리지 않게 합니다.
- 관련 없는 물품은 화면에서 치웁니다.
- 대상과 색이 다른 단순한 배경을 사용합니다.
- 앞·뒤·옆면, 가까운 거리·먼 거리, 손에 든 상태를 천천히 보여줍니다.
- 비슷한 클래스는 제품 글자와 고유한 형태가 잘 보이게 촬영합니다.

## 5. 녹화 영상과 사진 보기

최신순 목록에서 번호를 선택합니다.

```bash
cd /home/tracelab/chan
python3 media_viewer.py
```

특정 파일을 바로 열 수도 있습니다.

```bash
python3 media_viewer.py \
  /home/tracelab/carepack-dataset/raw/lip_balm/lip_balm_01.mkv
```

영상 조작키:

- `SPACE`: 일시정지 또는 계속 재생
- `a`, `d`: 5초 전 또는 후로 이동
- `r`: 처음부터 다시 재생
- `q` 또는 `ESC`: 종료

GUI를 사용할 수 없는 원격 환경에서는 맥으로 파일을 복사해 확인할 수 있습니다.
다음 명령은 맥 터미널에서 실행합니다.

```bash
scp tracelab@192.168.0.73:/home/tracelab/carepack-dataset/raw/lip_balm/lip_balm_01.mkv ~/Downloads/
open ~/Downloads/lip_balm_01.mkv
```

## 6. 영상 정상 여부 검사

기본 정보를 확인합니다.

```bash
ffprobe -v error \
  -select_streams v:0 \
  -show_entries format=filename,duration,size:stream=codec_name,width,height,avg_frame_rate \
  -of default=noprint_wrappers=1 \
  /home/tracelab/carepack-dataset/raw/lip_balm/lip_balm_01.mkv
```

전체 프레임을 끝까지 읽어봅니다.

```bash
ffmpeg -nostdin -v error \
  -i /home/tracelab/carepack-dataset/raw/lip_balm/lip_balm_01.mkv \
  -f null -
```

U20CAM의 MJPEG 원본에서는 `non monotonically increasing dts` 시간값 경고가 일부
나올 수 있습니다. 영상이 끝까지 읽히고 프레임 추출이 가능하면 현재 데이터 제작
과정에는 사용할 수 있습니다.

## 7. 학습 후보 프레임 추출

45초 영상에서 초당 2장을 추출하면 약 90장이 만들어집니다.

```bash
mkdir -p /home/tracelab/carepack-dataset/frames/lip_balm/lip_balm_01

ffmpeg -nostdin \
  -i /home/tracelab/carepack-dataset/raw/lip_balm/lip_balm_01.mkv \
  -vf fps=2 \
  -q:v 2 \
  /home/tracelab/carepack-dataset/frames/lip_balm/lip_balm_01/%06d.jpg
```

연속된 사진은 모습이 거의 같으므로 학습 전 흐릿한 프레임과 중복 프레임을
제외합니다. 원본 영상은 삭제하지 않습니다.

## 8. SAM2 Tiny 모델 준비

SAM2는 기존 `RobotUnified_v2` 가상환경의 PyTorch와 Ultralytics를 사용합니다.
모델 파일이 아직 없다면 한 번만 실행합니다.

```bash
mkdir -p /home/tracelab/chan/models
cd /home/tracelab/chan/models

/home/tracelab/RobotUnified_v2/.venv/bin/python -c \
  "from ultralytics import SAM; SAM('sam2_t.pt')"
```

다운로드 후 `/home/tracelab/chan/models/sam2_t.pt`가 있어야 합니다.

## 9. SAM2 포인트 마스킹

먼저 마스킹할 사진을 정합니다. `--point X Y`에는 사진 왼쪽 위를 `(0, 0)`으로 한
물체 내부 좌표를 넣습니다.

```bash
cd /home/tracelab/chan

/home/tracelab/RobotUnified_v2/.venv/bin/python sam2_mask.py \
  /home/tracelab/carepack-dataset/sam_test/lip_balm_frame.jpg \
  --point 560 470
```

배경이 함께 선택되면 배경 좌표를 음성 점으로 추가합니다.

```bash
/home/tracelab/RobotUnified_v2/.venv/bin/python sam2_mask.py \
  photo.jpg \
  --point 560 470 \
  --negative-point 900 500
```

물체를 둘러싼 박스를 사용할 수도 있습니다.

```bash
/home/tracelab/RobotUnified_v2/.venv/bin/python sam2_mask.py \
  photo.jpg \
  --box 310 330 810 605
```

CPU에서는 1280x720 사진 한 장에 약 10~20초가 걸릴 수 있습니다.

## 10. SAM2 결과 확인

기본 결과 폴더는 다음과 같습니다.

```text
/home/tracelab/carepack-dataset/sam_masks/<사진이름>_sam2/
├── overlay.jpg
├── mask_combined.png
├── mask_00.png
└── result.json
```

색상 마스크 결과 확인:

```bash
python3 /home/tracelab/chan/media_viewer.py \
  /home/tracelab/carepack-dataset/sam_masks/lip_balm_frame_sam2/overlay.jpg
```

흑백 마스크 확인:

```bash
python3 /home/tracelab/chan/media_viewer.py \
  /home/tracelab/carepack-dataset/sam_masks/lip_balm_frame_sam2/mask_combined.png
```

## 11. 처리 방향

라즈베리파이 CPU에서 45초 영상을 30fps 전체 프레임으로 SAM2 처리하면 시간이 너무
오래 걸립니다. 다음 순서를 권장합니다.

1. 원본 영상을 그대로 보관합니다.
2. 초당 1~2장만 후보 프레임으로 추출합니다.
3. 흐릿하거나 중복된 프레임을 제거합니다.
4. YOLO가 만든 물체 박스 또는 사람이 지정한 점을 SAM2에 전달합니다.
5. SAM2 마스크를 사람이 검수합니다.
6. 확정된 마스크를 YOLO11-seg 학습 형식으로 변환합니다.

SAM2는 마스크 생성과 라벨링 보조에 사용하고, 로봇의 실시간 인식은 학습한
YOLO11n-seg 모델로 처리하는 구성이 적합합니다.

## 12. 자주 발생하는 문제

### 카메라를 열 수 없음

다른 프로그램이 `/dev/video0`을 사용 중인지 확인합니다.

```bash
fuser /dev/video0
pkill ffplay
```

필요한 프로그램만 종료하고 다시 실행합니다.

### 영상 창이 나타나지 않음

라즈베리파이 데스크톱에 `tracelab` 사용자가 로그인되어 있어야 합니다. 데스크톱
로그인 없이 SSH만 연결된 상태라면 맥으로 파일을 복사해서 확인합니다.

### SAM2 모델 파일이 없음

8절의 모델 준비 명령을 다시 실행하고 다음 경로를 확인합니다.

```bash
ls -lh /home/tracelab/chan/models/sam2_t.pt
```

### 프로그램 종료

- OpenCV 뷰어: `q` 또는 `ESC`
- `ffplay`: `q`, 안 되면 터미널에서 `Ctrl+C`
- `ffmpeg`: 지정 시간이 끝나면 자동 종료, 중간 종료는 `Ctrl+C`
