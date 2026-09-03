# 웹 기능별 화면

[프로젝트 홈](../../README.md) · [상위 안내](../../README.md)

대시보드·자동 작업·수동 제어·비전·물품 관리·작업 이력 페이지를 구성합니다.

## 파일과 하위 폴더

| 파일·폴더 | 내용 |
|---|---|
| [AutomaticPage.tsx](AutomaticPage.tsx) | 자동 작업 시뮬레이션 |
| [DashboardPage.tsx](DashboardPage.tsx) | 시스템 요약 대시보드 |
| [HistoryPage.tsx](HistoryPage.tsx) | 작업·이벤트 이력 |
| [ItemsPage.tsx](ItemsPage.tsx) | 물품·목적지 편집 |
| [ManualPage.tsx](ManualPage.tsx) | 가상 팔 수동 제어 |
| [VisionPage.tsx](VisionPage.tsx) | 카메라 서버 상태·영상 표시 |

## 사용 방법

루트 `npm --prefix frontend run dev` 실행 후 왼쪽 메뉴에서 선택합니다. [ControlCenter](../components/README.md)가 화면을 전환합니다.

## 알아둘 점

자동 작업과 팔 수동 화면은 시뮬레이션입니다. `VisionPage`는 별도 카메라 서버의 실제 스트림을 표시할 수 있고, 실제 라즈봇 제어는 별도 리모컨입니다.
