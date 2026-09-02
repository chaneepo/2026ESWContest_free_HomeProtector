# 공통 UI와 리모컨

[프로젝트 홈](../README.md) · [상위 안내](../README.md)

통합 제어센터 프레임과 공통 UI, 실제 라즈봇 리모컨을 제공합니다.

## 파일과 하위 폴더

| 파일·폴더 | 내용 |
|---|---|
| [ControlCenter.tsx](ControlCenter.tsx) | 통합 화면·상단 비상 정지 연결 |
| [RaspbotRemote.tsx](RaspbotRemote.tsx) | 실제 라즈봇용 React 리모컨 |
| [ui.tsx](ui.tsx) | 공통 표시 컴포넌트·라벨 |

## 사용 방법

저장소 루트에서 `npm run dev`로 실행합니다. [웹 진입점](../app/README.md)과 [페이지](../views/README.md)에서 사용합니다.

## 알아둘 점

작업·팔 화면은 시뮬레이션이지만 `RaspbotRemote`는 실기 제어가 가능합니다. 상단 비상 정지는 라즈봇에도 STOP을 요청하며 물리 정지 확인을 대신하지 않습니다.
