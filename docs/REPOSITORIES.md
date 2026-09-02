# CARE-PACK 저장소 구성

2026-09-03에 기존 통합 저장소를 보존하면서 기능별 공개 저장소 6개를 만들었습니다. OpenArm처럼 메인 README의 Repositories 표에서 독립 저장소와 문서로 이동합니다. Git submodule이나 폴더 링크가 아닙니다.

## 역할과 코드 위치

| 독립 저장소 | 이 통합 저장소의 코드 위치 | 역할 |
|---|---|---|
| [carepack_web](https://github.com/chaneepo/carepack_web) | `app/`, `components/`, `views/`, `lib/` 등 | 웹 UI와 장치 프록시 |
| [carepack_raspbot](https://github.com/chaneepo/carepack_raspbot) | `raspbot_runtime/` | Pi 라즈봇 제어 서버·전용 UI |
| [carepack_arm](https://github.com/chaneepo/carepack_arm) | `motor/` | SO-ARM101·ESP32 도구 |
| [carepack_vision](https://github.com/chaneepo/carepack_vision) | `vision/` | 학습·라벨링·추론·웹 스트림 |
| [carepack_autonomy](https://github.com/chaneepo/carepack_autonomy) | `autonomy/` | 하드웨어 없는 자율 작업 시뮬레이터 |
| [carepack_backend](https://github.com/chaneepo/carepack_backend) | `backend/` | DB·서비스·상태 확인 API |

2026-09-03 이 통합 저장소에서는 `chan/`을 `raspbot_runtime/`으로 이름 변경했습니다. **독립 `carepack_raspbot` 저장소의 `chan/`과 Pi의 `/home/tracelab/chan`은 이번 변경 대상이 아닙니다.**

각 저장소는 자체 `.git`, `main` 브랜치와 루트 README를 갖습니다. 필요한 저장소만 독립적으로 clone할 수 있습니다. 모듈 이름을 Python 패키지 또는 운영 경로로 사용하는 경우를 위해 `backend/`, `autonomy/`, `chan/` 등의 내부 디렉터리는 유지했습니다.

## 보존 범위와 원본 이력

- 기준 통합 커밋: `c4f6c62999bfcf10cefd16c97f24c56144d6f76f`.
- 새 저장소는 해당 공개 소스를 선별한 독립 스냅샷입니다. 이전 커밋 이력은 기존 통합 저장소에 남아 있습니다.
- 각 저장소의 `SOURCE.json`에 원본과 포함 경로를 기록했습니다.
- 원래 통합 소스·로컬 `.env.local`·현재 실행 중인 웹과 카메라는 유지합니다.
- 웹의 라즈봇 공통 클라이언트는 `lib/raspbot/`에 독립 사본을 두었습니다. 기존 로컬에서 확인된 `fetch` 호출 바인딩 수정은 새 웹·라즈봇 사본 모두에 반영했습니다.
- 카메라 전용 `vision_stream.py`를 비전 저장소에 추가했습니다. 로봇 제어기를 시작하지 않습니다.
- 원래 Sites 배포 ID와 로그인 연결은 새 웹 저장소에 복사하지 않았습니다.
- 비밀 환경설정·SSH 인증 정보·원본 촬영 데이터·가상환경·빌드 결과는 복사하지 않았습니다. 기존 공개 가중치 `best.pt`와 코드의 설정 예시는 유지합니다.

## 앞으로 수정할 곳

새 기능과 버그 수정은 기능별 저장소에서 진행합니다. 기존 통합본이 필요한 경우 검토한 변경만 별도로 반영하세요. **한쪽에 커밋해도 다른 저장소나 실행 중인 Pi에 자동 반영되지 않습니다.**

독립 웹 저장소의 `lib/raspbot/control-client.*`와 독립 라즈봇 저장소의 `chan/web/control-client.*`(이 통합본에서는 `raspbot_runtime/web/control-client.*`)는 같은 제어 프로토콜을 사용합니다. 프로토콜을 바꾸면 양쪽 테스트를 실행하고 함께 반영합니다.

장치 주소는 웹의 무시된 `.env.local`에만 설정합니다. 코드를 GitHub에 올리는 것과 실제 장치에 배포·모터 운전을 시작하는 것은 별개입니다. 분리 작업은 장치를 재시작하거나 모터를 조작하지 않습니다.

## 분리 검증

- 자율 작업 모의 테스트: 9개 통과.
- 라즈봇 서버·안전 모의 테스트: 31개 통과.
- 로봇팔 fake-bus 로직 테스트: 43개 통과.
- 브라우저 제어 클라이언트: 웹과 라즈봇에서 각각 8개 통과.
- 웹 독립 의존성 설치·TypeScript 검사·배포용 빌드 통과.
- Python 문법·JSON 형식·문서 경로 검사 통과.
- 실제 모터 운전, CUDA 재학습, 테스트 DB 삭제·재생성은 실행하지 않았습니다.

라이선스는 임의로 새로 지정하지 않았습니다. 자체 코드의 라이선스 지정과 외부 라이브러리·모델의 조건 확인은 별도로 진행합니다.
