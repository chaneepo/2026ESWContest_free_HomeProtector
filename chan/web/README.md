# 라즈봇 전용 컨트롤러 UI

[프로젝트 홈](../../README.md) · [상위 안내](../README.md)

방향 버튼·키보드·회전각 입력·모드 선택·센서 표시와 공통 안전 클라이언트를 제공합니다.

## 파일과 하위 폴더

| 파일·폴더 | 내용 |
|---|---|
| [app.js](app.js) | Pi 전용 화면 연결·입력 처리 |
| [control-client.d.mts](control-client.d.mts) | 공통 클라이언트의 TypeScript 타입 |
| [control-client.mjs](control-client.mjs) | Pi·React가 공유하는 운전 권한 관리 |
| [index.html](index.html) | 전용 컨트롤러 화면 |
| [styles.css](styles.css) | 전용 컨트롤러 스타일 |

## 사용 방법

저장소 루트에서:

```bash
cd chan
python3 server.py --host 127.0.0.1 --port 8090
```

브라우저에서 `http://127.0.0.1:8090`을 엽니다. 위 명령은 데모 모드입니다.

## 알아둘 점

HTML 파일을 `file://`로 직접 열지 마세요. API가 필요합니다. `control-client.mjs`는 통합 React 리모컨도 공유합니다. 서버와 UI는 안전 프로토콜 2를 함께 사용해야 합니다.
