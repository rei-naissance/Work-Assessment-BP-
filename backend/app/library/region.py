"""Region-specific modules based on ZIP code prefix → state → region."""

from app.library.loader import get_region_modules_data

# Comprehensive ZIP prefix → region mapping
# Northeast: CT, ME, MA, NH, NJ, NY, PA, RI, VT
# Southeast: AL, FL, GA, KY, MD, MS, NC, SC, TN, VA, WV, DE, DC
# Midwest: IA, IL, IN, KS, MI, MN, MO, ND, NE, OH, SD, WI
# Southwest: AZ, AR, LA, NM, OK, TX
# West: AK, CA, CO, HI, ID, MT, NV, OR, UT, WA, WY

def _build_zip_map() -> dict[str, str]:
    m: dict[str, str] = {}

    def _add(start: int, end: int, region: str):
        for i in range(start, end + 1):
            m[f"{i:03d}"] = region

    # Northeast
    _add(10, 69, "northeast")    # MA, RI, NH, ME, VT, CT
    _add(70, 89, "northeast")    # NJ
    _add(100, 149, "northeast")  # NY
    _add(150, 196, "northeast")  # PA

    # Southeast
    _add(197, 199, "southeast")  # DE
    _add(200, 205, "southeast")  # DC
    _add(206, 219, "southeast")  # MD
    _add(220, 246, "southeast")  # VA
    _add(247, 268, "southeast")  # WV
    _add(270, 289, "southeast")  # NC
    _add(290, 299, "southeast")  # SC
    _add(300, 319, "southeast")  # GA
    _add(320, 349, "southeast")  # FL
    _add(350, 369, "southeast")  # AL
    _add(370, 385, "southeast")  # TN
    _add(386, 397, "southeast")  # MS
    _add(400, 427, "southeast")  # KY

    # Midwest
    _add(430, 459, "midwest")    # OH
    _add(460, 479, "midwest")    # IN
    _add(480, 499, "midwest")    # MI
    _add(500, 528, "midwest")    # IA
    _add(530, 549, "midwest")    # WI
    _add(550, 567, "midwest")    # MN
    _add(570, 577, "midwest")    # SD
    _add(580, 588, "midwest")    # ND
    _add(590, 599, "midwest")    # MT (sometimes grouped West — keeping Midwest for plains)
    _add(600, 629, "midwest")    # IL
    _add(630, 658, "midwest")    # MO
    _add(660, 679, "midwest")    # KS
    _add(680, 693, "midwest")    # NE

    # Southwest
    _add(700, 714, "southwest")  # LA
    _add(716, 729, "southwest")  # AR
    _add(730, 749, "southwest")  # OK
    _add(750, 799, "southwest")  # TX
    _add(850, 865, "southwest")  # AZ
    _add(870, 884, "southwest")  # NM

    # West
    _add(800, 816, "west")       # CO
    _add(820, 831, "west")       # WY
    _add(832, 838, "west")       # ID
    _add(840, 847, "west")       # UT
    _add(889, 898, "west")       # NV
    _add(590, 599, "west")       # MT (override — more West than Midwest)
    _add(900, 966, "west")       # CA, HI
    _add(967, 968, "west")       # HI
    _add(970, 979, "west")       # OR
    _add(980, 994, "west")       # WA
    _add(995, 999, "west")       # AK

    return m


ZIP_PREFIX_TO_REGION = _build_zip_map()

MODULES = get_region_modules_data()


def get_region(zip_code: str) -> str:
    prefix = zip_code[:3] if len(zip_code) >= 3 else ""
    return ZIP_PREFIX_TO_REGION.get(prefix, "")


def get_region_modules(zip_code: str) -> dict:
    region = get_region(zip_code)
    if not region:
        return {}
    return {k: v for k, v in MODULES.items() if v.get("region") == region}
