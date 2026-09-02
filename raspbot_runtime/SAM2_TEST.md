# SAM2 마스킹 시험

라즈베리파이에는 SAM2 Tiny 모델을 사용합니다. CUDA GPU가 없으므로 한 장 처리에
수 초에서 수십 초가 걸릴 수 있으며 실시간 처리는 목표로 하지 않습니다.

```bash
cd /home/tracelab/chan

/home/tracelab/RobotUnified_v2/.venv/bin/python sam2_mask.py \
  /home/tracelab/carepack-dataset/sam_test/lip_balm_frame.jpg \
  --point 560 470
```

물체 내부에 있는 점의 사진 좌표를 `--point X Y`로 지정합니다. 배경까지 함께
선택되면 제외할 위치를 `--negative-point X Y`로 추가할 수 있습니다.

```bash
/home/tracelab/RobotUnified_v2/.venv/bin/python sam2_mask.py \
  photo.jpg \
  --point 560 470 \
  --negative-point 900 500
```

물체를 둘러싼 박스를 이용할 수도 있습니다.

```bash
/home/tracelab/RobotUnified_v2/.venv/bin/python sam2_mask.py \
  photo.jpg \
  --box 310 330 810 605
```

결과는 `/home/tracelab/carepack-dataset/sam_masks` 아래에 저장됩니다.

- `overlay.jpg`: 원본 위에 색상 마스크를 표시한 결과
- `mask_combined.png`: 모든 물체를 합친 흑백 마스크
- `mask_00.png`: 개별 물체의 흑백 마스크
- `result.json`: 점수, 경계 상자와 처리 시간
