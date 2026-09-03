# Python 설치 목록 / Python requirements

[프로젝트 홈](../README.md) · [한국어 설치 안내](../docs/setup/README.ko.md) · [English setup](../docs/setup/README.en.md)

- `requirements.txt`: 통합 실행 환경 의존성
- `requirements-dev.txt`: 실행 환경 전체와 개발·테스트 도구

저장소 루트에서 가상환경을 활성화한 후 실행합니다. macOS/Linux와 Windows PowerShell에서 동일합니다.

```bash
python -m pip install -r requirements/requirements-dev.txt
```

실행 패키지만 설치하려면:

```bash
python -m pip install -r requirements/requirements.txt
```

개발용 파일의 `-r requirements.txt`는 해당 파일이 있는 이 폴더를 기준으로 실행용 목록을 포함합니다. 패키지 버전은 이동 전과 같습니다. `vision/requirements.txt`와 `raspbot_runtime/requirements.txt`는 각 장치·모듈의 별도 환경용이므로 그대로 유지합니다. 자동 설치 스크립트도 새 경로를 사용합니다.

## English

Activate the virtual environment and run the commands above from the repository root. The development list includes runtime dependencies through its relative `-r requirements.txt` entry. Dependency versions are unchanged. Module-specific lists under `vision/` and `raspbot_runtime/` remain in place. Both platform setup scripts use the new paths.
