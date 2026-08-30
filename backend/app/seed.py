from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.database import SessionLocal
from backend.app.enums import RoutineType
from backend.app.models import Item, Location, Routine, RoutineItem


@dataclass
class SeedResult:
    locations_created: int = 0
    items_created: int = 0
    routines_created: int = 0
    routine_items_created: int = 0


LOCATION_DATA = (
    ("BAG", "가방"),
    ("ENTRANCE", "현관"),
    ("BEDROOM", "안방"),
    ("KITCHEN", "주방"),
    ("CAREGIVER_BOX", "보호자 확인함"),
)

ITEM_DATA = (
    ("TAG-001", "약통", "의약품", "BEDROOM"),
    ("TAG-002", "물병", "생활용품", "KITCHEN"),
    ("TAG-003", "차키", "소지품", "ENTRANCE"),
    ("TAG-004", "마스크", "위생용품", "ENTRANCE"),
    ("TAG-005", "핫팩", "생활용품", "BEDROOM"),
)

ROUTINE_DATA = (
    (
        "OUTING_PREP",
        "외출 가방 준비",
        RoutineType.OUTING_PREP,
        "대회 시뮬레이션용 외출 준비 루틴",
    ),
    (
        "RETURN_HOME",
        "귀가 후 물품 정리",
        RoutineType.RETURN_HOME,
        "대회 시뮬레이션용 귀가 정리 루틴",
    ),
)


def seed_development_data(session: Session) -> SeedResult:
    result = SeedResult()

    locations = {
        location.code: location for location in session.scalars(select(Location)).all()
    }
    for code, name in LOCATION_DATA:
        if code not in locations:
            location = Location(code=code, name=name)
            session.add(location)
            session.flush()
            locations[code] = location
            result.locations_created += 1

    items = {item.tag_id: item for item in session.scalars(select(Item)).all()}
    for tag_id, name, category, location_code in ITEM_DATA:
        if tag_id not in items:
            item = Item(
                tag_id=tag_id,
                name=name,
                category=category,
                home_location_id=locations[location_code].id,
            )
            session.add(item)
            session.flush()
            items[tag_id] = item
            result.items_created += 1

    routines = {
        routine.code: routine for routine in session.scalars(select(Routine)).all()
    }
    for code, name, routine_type, description in ROUTINE_DATA:
        if code not in routines:
            routine = Routine(
                code=code,
                name=name,
                routine_type=routine_type,
                description=description,
            )
            session.add(routine)
            session.flush()
            routines[code] = routine
            result.routines_created += 1

    routine_plan = {
        "OUTING_PREP": (
            ("TAG-001", "BAG"),
            ("TAG-003", "BAG"),
            ("TAG-004", "BAG"),
        ),
        "RETURN_HOME": tuple(
            (tag_id, location_code) for tag_id, _, _, location_code in ITEM_DATA
        ),
    }

    existing_pairs = {
        (routine_id, item_id)
        for routine_id, item_id in session.execute(
            select(RoutineItem.routine_id, RoutineItem.item_id)
        )
    }
    for routine_code, configured_items in routine_plan.items():
        routine = routines[routine_code]
        for sequence, (tag_id, target_code) in enumerate(configured_items, start=1):
            item = items[tag_id]
            pair = (routine.id, item.id)
            if pair in existing_pairs:
                continue
            session.add(
                RoutineItem(
                    routine_id=routine.id,
                    item_id=item.id,
                    target_location_id=locations[target_code].id,
                    sequence=sequence,
                    is_required=True,
                )
            )
            existing_pairs.add(pair)
            result.routine_items_created += 1

    session.commit()
    return result


def main() -> None:
    with SessionLocal() as session:
        result = seed_development_data(session)
    print(
        "CARE-PACK development seed complete: "
        f"locations={result.locations_created}, "
        f"items={result.items_created}, "
        f"routines={result.routines_created}, "
        f"routine_items={result.routine_items_created}"
    )


if __name__ == "__main__":
    main()
