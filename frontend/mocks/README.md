# 웹 시뮬레이션·예시 데이터

[프로젝트 홈](../../README.md) · [상위 안내](../../README.md)

화면 초기 데이터와 작업 단계별 시뮬레이션 엔진을 제공합니다.

## 파일과 하위 폴더

| 파일·폴더 | 내용 |
|---|---|
| [mockData.ts](mockData.ts) | 화면 예시 데이터 |
| [simulationEngine.ts](simulationEngine.ts) | 웹 작업 단계·실패 재현 |

## 사용 방법

저장소 루트에서 `npm --prefix frontend run dev` 후 자동 작업 화면에서 사용합니다. [상태 관리](../store/README.md)가 엔진을 호출합니다.

## 알아둘 점

화면용 가상 좌표·상태·성공 결과를 생성합니다. 웹 시뮬레이터와 Python [autonomy](../../autonomy/README.md)는 각각 독립적으로 실행합니다.
