# Motor control

[프로젝트 홈](../README.md) · [기존 SO-ARM101 상세 설명서](README_KO.md) · [테스트 안내](tests/README.md)

기존 팔·모터 프로그램을 보관하는 폴더입니다. **이번 문서 정리에서는 털기 동작, 팔 제어 코드, 설정·교정값을 변경하지 않았습니다.**

## 프로그램 구성

| 프로그램·파일 | Documentation | 역할 |
|---|---|---|
| [carepack_so101_profiled_studio.py](carepack_so101_profiled_studio.py) | [Profiled Studio 안내](README_KO.md) | SO-ARM101 raw PULSE 점검·수동 이동·고정 자세 시퀀스·리더암 추종 |
| [run_profiled_studio.cmd](run_profiled_studio.cmd) | [실행 준비](#실행-준비) | Windows의 기존 `lerobot` 환경을 활성화하는 실행 도구 |
| [carepack_so101_profiled_config.json](carepack_so101_profiled_config.json) | [기존 설정 안내](README_KO.md) | 팔 프로그램 설정 원본 |
| [carepack_so101_wrist_homing_backup.json](carepack_so101_wrist_homing_backup.json) | [기존 영점 안내](README_KO.md) | 손목 영점 관련 백업 원본 |
| [motor_control.py](motor_control.py) | [ESP32 모터·털기 도구](#esp32-모터털기-도구) | Tkinter 화면에서 이동·털기 각도·횟수·간격 전송 |
| [esp32_motor_controller_with_interval.ino](esp32_motor_controller_with_interval.ino) | [ESP32 모터·털기 도구](#esp32-모터털기-도구) | ESP32의 이동·털기·복귀 시퀀스 |
| [tests/](tests/) | [테스트 README](tests/README.md) | 기존 팔 로직의 fake-bus 테스트 |
| [s101](s101) | — | 현재 `#s101` 내용만 있는 메모 파일; 실행 진입점 아님 |

## 실행 준비

### SO-ARM101 Profiled Studio

Windows의 기존 `lerobot` Conda 환경과 Tkinter, 해당 LeRobot 모터 라이브러리를 사용합니다. 루트 웹앱의 Python 의존성 설치만으로 이 환경까지 구성되지는 않습니다.

`motor` 폴더에서 `run_profiled_studio.cmd`를 실행하거나, 기존 환경을 활성화한 터미널에서:

```bat
conda activate lerobot
python carepack_so101_profiled_studio.py
```

환경·포트·교정·시퀀스 세부 설명은 기존 [README_KO.md](README_KO.md)를 우선합니다. 문서에 있는 COM 포트·개인 PC 경로·교정값을 다른 장치에 그대로 적용하지 마세요.

### ESP32 모터·털기 도구

`motor_control.py`는 Python의 Tkinter와 `pyserial`을 사용합니다. 기존 ESP32 펌웨어·모터 드라이버·전원 구성을 확인한 환경에서 실행합니다.

```bash
python motor_control.py
```

코드상 PC–ESP32 연결은 115200 baud, ESP32–모터 UART는 38400 baud이며 RX/TX 정의는 16/17입니다. 이는 **현재 소스 정의**이며, 실제 배선 확인을 대신하지 않습니다.

기존 기능은 주 이동 → 끝점 털기 → 복귀, 별도 JOG 이동입니다. 연결 전에는 제어 명령을 전송하지 않도록 UI에서 안내합니다. 이 설명을 확인하기 위해 이번에 실제 장치를 실행하거나 펌웨어를 업로드하지 않았습니다.

## 다른 모듈과의 관계

- [웹 팔 서비스](../services/README.md)는 현재 시뮬레이션이며 이 프로그램을 자동 호출하지 않습니다.
- [자율 초안](../autonomy/README.md)은 별도의 가상 동작 모듈입니다.
- 기존 고정 자세 시퀀스나 리더암 추종은 카메라 인식·적재 센서까지 연결한 통합 자율 작업 완료를 의미하지 않습니다.
- [라즈봇 서버의 STOP](../chan/SAFETY_REVIEW.md)은 이 폴더의 독립 팔·ESP32 프로그램을 모두 정지시키는 통합 비상정지가 아닙니다.

## 원본 보존과 주의사항

`README_KO.md`의 기존 상세 내용과 코드·JSON·실행 스크립트·테스트는 그대로 보존합니다. 새 장치에 기존 교정값을 덮어쓰지 마세요.

특히 기존 상세 문서의 `1:1 빠른 추종`은 프로그램 속도·스텝·선행거리 제한이 없다고 명시되어 있습니다. 전체 PULSE 범위가 기계적으로 안전한 범위를 뜻하지 않습니다. 실제 제어 시 장치별 작업 공간·전원 차단 수단을 확인해야 합니다.

이 README 추가는 하드웨어 안전성 검증이나 기존 알고리즘 수정이 아닙니다.
