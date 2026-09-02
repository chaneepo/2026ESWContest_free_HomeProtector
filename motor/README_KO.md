# CARE-PACK SO-ARM101 Profiled PULSE Studio v21

SO-ARM101의 STS3215 모터 ID 1~6을 raw PULSE로 점검하고, 수동 이동·고정 자세 시퀀스·카메라 없는 리더암 텔레오퍼레이션을 실행하는 Windows GUI입니다.

## v21 핵심 변경

- 기존 v20 기능 유지
- `1:1 빠른 추종`에서는 리더 목표값을 팔로워에 직접 전송
- `max_step_pulse`와 `max_command_lead_pulse`는 `안전 추종`에서만 적용
- 직접 추종의 `Goal_Velocity`는 `0`으로 설정하여 STS3215 위치모드 최대속도 사용
- 직접 추종에서도 사용자 지정 허용범위·통신 오류·저전압·과열·긴급정지는 유지
- 1~6번 최초 프로그램 허용범위를 모두 `0~4095`로 변경
- 기존 실측범위 `825~2950`, `833~3230` 같은 고정 제한 제거
- 사용자가 저장한 최소·최대값을 유일한 프로그램 허용범위로 사용
- 연결 전에도 사용자 허용범위 저장 가능
- 범위 저장 시 현재위치·EEPROM MIN/MAX·집게 교정값과 비교하지 않음
- 현재 위치가 사용자 범위 밖이어도 토크 ON 허용
- 리더암 시작 위치가 사용자 범위 밖이어도 즉시 경계로 튀지 않고 현재 위치에서 시작
- 텔레오퍼레이션에서 EEPROM 범위에 맞춘 자동 축소 및 정체 안전정지 제거
- 통신 오류·저전압·과열 긴급정지는 유지
- `1:1 빠른 추종` 모드: 배율 1.0, 제어주기 25Hz, 프로그램 속도·스텝·선행거리 제한 없음
- 필요하면 `안전 추종`을 선택해 제한된 저속 설정으로 복귀
- `허용범위 설정` 탭에서 1~6번 최소·최대 PULSE 편집·저장·복원
- 입력 형식은 STS3215 raw 위치값인 0~4095와 `최소 < 최대`만 검사
- 사용자 범위는 수동 이동·시퀀스·리더암 조작에 공통 적용
- 허용범위 편집은 프로그램 JSON만 변경하며 모터 EEPROM은 변경하지 않음
- `리더암 조작` 탭 추가, 기본 포트는 팔로워 COM3 / 리더 COM4
- 리더와 팔로워의 시작 자세를 각각 기준으로 저장하는 상대 위치 제어
- 리더암 토크는 항상 OFF, 팔로워만 위치제어
- 축별 사용 여부와 방향 반전 선택
- 1:1 모드 이동 배율 1.0, 안전 모드는 0.2~1.0 조절
- 팔로워 목표는 사용자가 저장한 프로그램 범위만 사용
- 안전 추종에서 축별 최대 명령 스텝과 현재 위치 대비 선행거리 제한 적용
- 저전압·과열·통신 오류 시 팔로워 토크 OFF
- 0/4095 경계를 지나는 리더 위치를 연속값으로 처리해 잘못된 한 바퀴 명령 방지
- 화면을 `수동 조작·교정`, `자동 동작·기록`, `허용범위 설정`, `리더암 조작` 탭으로 분리
- 수동 화면에 세로·가로 스크롤 적용
- 팔꿈치 증가 방향의 긴 이동을 최대 400 PULSE 구간 목표로 자동 분할
- 팔꿈치 속도·가속도를 별도로 제한해 긴 이동 진동 완화
- 손목 회전축 속도를 다른 팔축보다 1.5배로 보정하되 최대 450으로 제한
- 1~6번 모터의 EEPROM MIN·MAX·MODE를 명령어 없이 확인하는 읽기 전용 버튼 추가
- 여러 고정 자세 단계 추가·순서 변경·저장·불러오기·순차 실행
- 모든 이동 결과를 `carepack_motion_log.csv`에 자동 기록
- 손목 영점·집게 교정·2·3축 튜닝·통신 복구 기능 유지

## 프로그램 허용범위

v21은 기존 측정값을 고정 제한으로 사용하지 않습니다.

| 축 | v21 기본 범위 |
|---|---:|
| 1~6번 전체 | 0~4095 |

`허용범위 설정` 탭에서 네가 원하는 값으로 바꾸면 그 값만 적용됩니다.

## v20 설정 파일 복사

v20과 v21 폴더가 같은 `새 폴더` 안에 있으면 v21 최초 실행 시 손목·집게·튜닝·사용자 허용범위 파일을 자동 복사합니다. 팔로워를 다시 교정할 필요는 없습니다.

자동 복사가 되지 않을 때만 v20 프로그램을 종료한 뒤 기존 설정 파일을 v21 폴더로 복사하세요.

```bat
if exist "C:\Users\wngk7\Desktop\새 폴더\carepack_so101_profiled_studio_v20\carepack_so101_wrist_homing_backup.json" copy /Y "C:\Users\wngk7\Desktop\새 폴더\carepack_so101_profiled_studio_v20\carepack_so101_wrist_homing_backup.json" "C:\Users\wngk7\Desktop\새 폴더\carepack_so101_profiled_studio_v21\carepack_so101_wrist_homing_backup.json"
```

```bat
if exist "C:\Users\wngk7\Desktop\새 폴더\carepack_so101_profiled_studio_v20\carepack_so101_gripper_calibration.json" copy /Y "C:\Users\wngk7\Desktop\새 폴더\carepack_so101_profiled_studio_v20\carepack_so101_gripper_calibration.json" "C:\Users\wngk7\Desktop\새 폴더\carepack_so101_profiled_studio_v21\carepack_so101_gripper_calibration.json"
```

```bat
if exist "C:\Users\wngk7\Desktop\새 폴더\carepack_so101_profiled_studio_v20\carepack_so101_loaded_axis_tuning_backup.json" copy /Y "C:\Users\wngk7\Desktop\새 폴더\carepack_so101_profiled_studio_v20\carepack_so101_loaded_axis_tuning_backup.json" "C:\Users\wngk7\Desktop\새 폴더\carepack_so101_profiled_studio_v21\carepack_so101_loaded_axis_tuning_backup.json"

```

```bat
if exist "C:\Users\wngk7\Desktop\새 폴더\carepack_so101_profiled_studio_v20\carepack_so101_range_overrides.json" copy /Y "C:\Users\wngk7\Desktop\새 폴더\carepack_so101_profiled_studio_v20\carepack_so101_range_overrides.json" "C:\Users\wngk7\Desktop\새 폴더\carepack_so101_profiled_studio_v21\carepack_so101_range_overrides.json"
```

## 실행 방법

압축을 `C:\Users\wngk7\Desktop\새 폴더`에 풀고 `run_profiled_studio.cmd`를 더블클릭합니다. 명령어로 실행하려면:

```bat
conda activate lerobot
cd /d "C:\Users\wngk7\Desktop\새 폴더\carepack_so101_profiled_studio_v21"
python carepack_so101_profiled_studio.py
```

## 최초 안전 확인

1. v20과 일반 LeRobot 텔레오퍼레이션 등 다른 모터 제어 프로그램을 모두 종료합니다.
2. v21을 실행합니다.
3. `내부 MIN·MAX·MODE 확인`을 누릅니다.
4. 모든 축 MODE가 0인지 확인합니다.
5. 모터 내부 MIN·MAX는 참고만 하며 프로그램 범위를 자동 변경하지 않습니다.
6. 손목 영점 상태가 `완료`인지 확인합니다. 완료 상태라면 영점 버튼을 다시 누르지 않습니다.
7. `gentle`과 한 축만 선택한 상태에서 중앙 부근 ±20 PULSE부터 시험합니다.

## 수동 이동

1. `현재값 → 목표값`을 눌러 현재 자세를 복사하고 축 선택을 초기화합니다.
2. 움직일 축의 목표값을 입력합니다. 해당 축만 자동 선택됩니다.
3. `프로파일 이동`을 누릅니다.
4. 2축 이상 또는 300 PULSE 이상 이동은 확인창의 시작값과 목표값을 다시 확인합니다.

팔꿈치가 증가하는 방향으로 400 PULSE를 넘게 수동 이동하면 v21이 중간 목표를 자동 생성합니다. 이 설정은 리더암 직접 추종에는 적용되지 않습니다.

## 허용범위 변경

1. `허용범위 설정` 탭을 엽니다. 팔로워 연결 전에도 가능합니다.
2. `허용범위 설정` 탭에서 축별 새 최소·최대 PULSE를 입력합니다.
3. `내 허용범위 저장`을 누릅니다.
4. 현재위치·EEPROM·집게 교정값과 관계없이 저장됩니다.
5. 전체범위로 돌아가려면 `전체 0~4095로 복원`을 누릅니다.

저장 파일은 `carepack_so101_range_overrides.json`입니다. 모터 EEPROM은 변경하지 않습니다.

## 리더암 텔레오퍼레이션

`lerobot-calibrate`로 팔로워를 다시 교정하지 않습니다. v20에서 복사한 손목 영점과 집게 교정값을 그대로 사용합니다.

1. 팔로워 USB(COM3)와 리더 USB(COM4)를 모두 연결합니다.
2. 수동 탭에서 팔로워 COM3을 연결하고 `내부 MIN·MAX·MODE 확인`을 실행합니다.
3. 팔로워 토크를 켭니다.
4. `리더암 조작` 탭에서 COM4를 입력하고 `리더 연결`을 누릅니다.
5. 추종 모드 `1:1 빠른 추종`, 이동 배율 1.0을 확인하고 사용할 축 하나만 선택합니다. 이 모드에는 프로그램 속도·스텝·선행거리 제한이 없습니다.
6. 두 팔을 안전한 중앙 자세에 놓고 `기준 자세 저장 + 리더 조작 시작`을 누릅니다.
7. 리더축을 조금 움직여 팔로워 방향을 확인합니다. 반대라면 즉시 중지하고 해당 축 `방향 반전`을 선택합니다.
8. 정상인 축을 하나씩 추가합니다.

`리더 조작 중지 + 현재 자세 유지`는 팔로워 토크를 유지합니다. 진동·이상음·예상 밖 움직임에는 `긴급 정지 + 팔로워 토크 OFF`를 사용합니다.

## 자동 동작과 기록

`자동 동작·기록` 탭에서 수동 탭의 목표 6축을 단계로 추가할 수 있습니다. 단계 이름과 완료 후 대기시간을 정하고 순서를 편집한 뒤 JSON으로 저장하거나 순차 실행합니다.

카메라·무게센서 확인은 아직 포함하지 않았으므로 물품과 가방 위치를 고정한 시험에서만 사용합니다. 이동 시작·목표·최종값, 오차, 이동시간, 전압·온도·전류, 성공·미도달·고장은 `carepack_motion_log.csv`에 저장됩니다.

## 안전 주의

- 진동·이상음·발열·케이블 당김이 생기면 즉시 `긴급 정지 + 6축 토크 OFF`를 누릅니다.
- 모터 내부 제한 진단 버튼은 읽기만 하며 EEPROM 값을 변경하지 않습니다.
- 바닥축 EEPROM은 이미 확인한 `742~3439`, MODE 0 상태를 유지합니다.
- 팔꿈치 진동을 해결하려고 토크나 P게인을 임의로 올리지 않습니다.
- 소프트웨어 긴급정지는 물리적 전원 차단 스위치를 대신하지 않습니다.
