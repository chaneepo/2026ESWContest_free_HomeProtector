# 사진·영상·카메라 확인

라즈베리파이 데스크톱 터미널에서 실행합니다.

```bash
cd /home/tracelab/chan
python3 media_viewer.py
```

기본 실행은 `/home/tracelab/carepack-dataset` 아래의 사진과 영상을 최신순으로
표시합니다. 번호를 입력하면 해당 파일을 엽니다.

특정 영상 또는 사진을 바로 열 수도 있습니다.

```bash
python3 media_viewer.py \
  /home/tracelab/carepack-dataset/raw/lipstick/lipstick_01.mkv
```

실시간 U20CAM 화면은 다음과 같이 엽니다.

```bash
python3 media_viewer.py --camera 0
```

실시간 화면에서 `s`를 누르면 원본 프레임이
`/home/tracelab/carepack-dataset/snapshots`에 저장됩니다.

## 조작키

- 공통: `q` 또는 `ESC`로 닫기
- 영상: `SPACE` 일시정지, `a` 5초 뒤로, `d` 5초 앞으로, `r` 처음부터
- 실시간 카메라: `s` 사진 저장

라즈베리파이 데스크톱에 같은 사용자로 로그인되어 있다면 일반 SSH 터미널에서도
현재 그래픽 세션을 자동으로 찾아 라즈베리파이 모니터에 창을 표시합니다.
