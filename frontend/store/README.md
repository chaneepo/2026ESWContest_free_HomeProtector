# 웹 전역 상태

[프로젝트 홈](../../README.md) · [상위 안내](../../README.md)

현재 페이지·작업·이벤트·물품·가상 팔 상태를 React Context로 공유합니다.

## 파일과 하위 폴더

| 파일·폴더 | 내용 |
|---|---|
| [SystemProvider.tsx](SystemProvider.tsx) | React Context·작업 진행·이벤트 상태 |

## 사용 방법

[SystemProvider.tsx](SystemProvider.tsx)의 `SystemProvider` 안에서 `useSystem()`으로 접근합니다.

## 알아둘 점

현재 상태는 브라우저 메모리 중심이므로 새로고침하면 초기화됩니다. 이 모듈의 시뮬레이션 정지와 실제 라즈봇 STOP 연결은 [ControlCenter](../components/README.md)에서 구분해 처리합니다.
