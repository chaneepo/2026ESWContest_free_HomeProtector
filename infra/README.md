# Docker 인프라 설정 / Docker infrastructure

[프로젝트 홈](../README.md) · [한국어 설치 안내](../docs/setup/README.ko.md) · [English setup](../docs/setup/README.en.md)

`compose.yaml`은 기존 PostgreSQL DB 설정입니다. **모든 명령은 저장소 루트에서 실행합니다.** 루트의 `.env`를 준비한 후:

```bash
docker compose --project-directory . -f infra/compose.yaml up -d db
docker compose --project-directory . -f infra/compose.yaml ps
docker compose --project-directory . -f infra/compose.yaml stop db
```

macOS/Linux 터미널과 Windows PowerShell에서 같은 명령을 사용합니다. `--project-directory .`는 프로젝트 기준 경로를 기존 저장소 루트로 유지해 `.env`와 기본 프로젝트 이름, `postgres_data` 볼륨 이름이 파일 이동 때문에 달라지지 않게 합니다. `infra/` 안에서 실행하거나 `-f`만 사용하는 방식은 피하세요. 기존에 `-p` 또는 `COMPOSE_PROJECT_NAME`을 사용했다면 동일한 이름을 계속 사용해야 합니다. 저장소 폴더 이름 자체를 변경한 경우에는 기존 Compose 프로젝트 이름을 별도로 지정해야 합니다.

이 정리는 DB 데이터나 컨테이너를 이전·초기화하지 않습니다. `down -v`는 DB 볼륨까지 삭제하므로 단순 정리·재시작에 사용하지 마세요.

## English

Run every command above from the repository root after preparing its `.env`. The commands work on macOS/Linux and Windows PowerShell. `--project-directory .` preserves the root used for environment loading and the default Compose project/volume names. Do not run from `infra/` or omit this option. If you previously used `-p` or `COMPOSE_PROJECT_NAME`, keep that same project name. Renaming the repository directory also requires explicitly retaining the previous project name.

This reorganization does not migrate or reset database data. Do not use `down -v` for routine cleanup or restarts: it deletes the database volume.
