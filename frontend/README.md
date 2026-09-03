# CARE-PACK 웹 / Frontend

[프로젝트 홈](../README.md) · [한국어 전체 설정](../docs/setup/README.ko.md) · [English setup](../docs/setup/README.en.md)

통합 웹 UI와 장치 API 프록시를 관리합니다. 웹 소스, Node.js 패키지 목록, TypeScript·Vite·Next.js·ESLint 설정은 모두 이 폴더에 있습니다.

리모컨은 기존 `../raspbot_runtime/web/control-client.mjs`와 타입 선언을 공유합니다. 이 통합 저장소 전체를 clone해서 빌드해야 하며 `frontend/`만 복사하면 해당 의존성이 빠집니다. 이 파일은 브라우저용 클라이언트이고 Pi 서버를 실행하지 않습니다.

## 설치와 실행

아래는 **저장소 루트**에서 실행하는 명령이며 macOS/Linux·Windows PowerShell 모두 동일합니다. Node.js 22.13 이상이 필요합니다.

```bash
npm --prefix frontend ci
npm --prefix frontend run dev
npm --prefix frontend run build
```

이미 `frontend/` 안에 있다면 `npm ci`, `npm run dev`, `npm run build`를 사용하세요. 배포 빌드를 실행하려면 `npm --prefix frontend run start`를 사용합니다.

Python도 함께 설치하는 기존 `scripts/setup.sh`, `scripts/setup.ps1`과 실행 도구 `scripts/dev.sh`, `scripts/dev.ps1`은 저장소 루트에 유지되며 새 웹 경로를 사용합니다. Python 가상환경은 루트 `.venv/`, DB 환경설정은 루트 `.env`입니다.

## 환경설정과 배포

장치 연결이 필요할 때만 이 폴더의 `.env.example`을 `.env.local`로 복사한 뒤 직접 확인한 주소를 설정하세요. 서버 재시작이 필요합니다. 장치 주소가 없으면 웹 시뮬레이션은 사용할 수 있으며 실기 연결은 비활성 상태입니다.

기존 작업 폴더를 업데이트했다면 기존 루트 `.env.local`, `.openai/`, `node_modules/`를 내용 변경 없이 `frontend/` 아래로 옮겨 사용하세요. 목적지 파일이 이미 있다면 덮어쓰지 말고 먼저 확인하세요. 패키지는 이동 대신 위 설치 명령으로 새로 설치해도 됩니다. 이번 로컬 작업 환경에서는 이동을 완료했습니다.

Sites 개인 연결 설정은 `frontend/.openai/hosting.json`이며 계속 Git에서 제외됩니다. 새 clone에는 없어도 실행·빌드할 수 있습니다. 빌드 결과는 `frontend/dist/`에 생성됩니다. 호스팅 서비스의 빌드 기준 디렉터리는 `frontend`로 지정하고, 패키징 도구도 `frontend/`를 프로젝트 경로로 사용해야 합니다. 이번 폴더 정리에서는 호스팅 서비스 재배포나 원격 설정 변경을 수행하지 않았습니다.

## 폴더

- `app/`: 진입점·레이아웃·장치 API
- `components/`, `views/`: UI 구성 요소와 화면
- `lib/`, `services/`, `store/`, `mocks/`, `types/`: 프록시·서비스·상태·목업·타입
- `public/`: 정적 파일
- `scripts/`: 웹 빌드 설정 도우미와 테스트

## 검사

저장소 루트에서 배포 설정의 선택적 로딩을 검사합니다.

```bash
node --test frontend/scripts/load-hosting-config.test.mjs
```

타입 검사는 `frontend/` 안에서 `npx tsc --noEmit --incremental false`로 실행합니다. 실제 로봇이나 DB를 실행하는 검사가 아닙니다.

## English

All web source and package/build configuration now live in `frontend/`. Run the prefix commands above from the repository root, or run ordinary npm commands inside `frontend/`. Shared setup/dev scripts still live in root `scripts/`; Python `.venv` and the database `.env` remain at the repository root.

Web endpoints belong in `frontend/.env.local` (copy this folder's `.env.example` only when needed). Existing local web settings and dependencies move into this folder without changing their contents. Do not overwrite existing destination settings. Personal Sites metadata remains ignored at `frontend/.openai/hosting.json` and is optional for a fresh clone.

Build output is `frontend/dist/`. Clone the whole repository: the remote UI still imports the shared browser client and types from `../raspbot_runtime/web/`. Use `frontend` as the hosting build root and the project path passed to packaging tools. This reorganization does not redeploy the hosted site or modify its remote settings. Database and hardware services are unchanged.
