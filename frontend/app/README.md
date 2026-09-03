# 웹 애플리케이션 진입점

[프로젝트 홈](../../README.md) · [상위 안내](../../README.md)

페이지, 공통 레이아웃, 스타일과 서버 측 장치 API 경로를 관리합니다.

## 파일과 하위 폴더

| 파일·폴더 | 내용 |
|---|---|
| [api/](api/README.md) | 웹 API |
| [globals.css](globals.css) | 전역 스타일 |
| [layout.tsx](layout.tsx) | 공통 HTML 레이아웃·메타데이터 |
| [page.tsx](page.tsx) | 통합 제어센터 진입 |

## 사용 방법

저장소 루트에서 `npm --prefix frontend ci` 후 `npm --prefix frontend run dev`로 실행합니다. 이 폴더 안에서 별도 설치하거나 실행하지 않습니다.

## 알아둘 점

`page.tsx`가 통합 제어센터를 불러옵니다. API 프록시와 작업 시뮬레이션의 역할은 다르며, 라즈봇 리모컨은 실제 기기에 명령을 보낼 수 있습니다.
