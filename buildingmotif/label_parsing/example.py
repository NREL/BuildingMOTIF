from pathlib import Path

from buildingmotif.ingresses import CSVIngress
from buildingmotif.label_parsing.combinators import (
    COMMON_EQUIP_ABBREVIATIONS_BRICK,
    abbreviations,
    constant,
    many,
    maybe,
    regex,
    sequence,
    string,
)
from buildingmotif.label_parsing.parser import (
    analyze_failures,
    parse,
    parse_list,
    results_to_tokens,
)
from buildingmotif.label_parsing.tokens import Constant, Delimiter, Identifier
from buildingmotif.namespaces import BRICK

# define abbreviation dictionaries. Use a provided one for Equipment
equip_abbreviations = abbreviations(COMMON_EQUIP_ABBREVIATIONS_BRICK)
# define our own for Points (specific to this building)
point_abbreviations = abbreviations(
    {
        "ChwVlvPos": BRICK.Position_Sensor,
        "HwVlvPos": BRICK.Position_Sensor,
        "RoomTmp": BRICK.Air_Temperature_Sensor,
        "Room_RH": BRICK.Relative_Humidity_Sensor,
        "UnoccHtgSpt": BRICK.Unoccupied_Air_Temperature_Heating_Setpoint,
        "OccHtgSpt": BRICK.Occupied_Air_Temperature_Heating_Setpoint,
        "UnoccClgSpt": BRICK.Unoccupied_Air_Temperature_Cooling_Setpoint,
        "OccClgSpt": BRICK.Occupied_Air_Temperature_Cooling_Setpoint,
        "SaTmp": BRICK.Supply_Air_Temperature_Sensor,
        "OccCmd": BRICK.Occupancy_Command,
        "EffOcc": BRICK.Occupancy_Status,
    }
)


# encode the naming convention in a function
def custom_parser(target):
    return sequence(
        string(":", Delimiter),
        # regex until the underscore
        constant(Constant(BRICK.Building)),
        regex(r"[^_]+", Identifier),
        string("_", Delimiter),
        # number for AHU name
        constant(Constant(BRICK.Air_Handling_Unit)),
        regex(r"[0-9a-zA-Z]+", Identifier),
        string(":", Delimiter),
        # equipment types
        equip_abbreviations,
        # equipment ident
        regex(r"[0-9a-zA-Z]+", Identifier),
        string("_", Delimiter),
        maybe(
            sequence(regex(r"[A-Z]+[0-9]+", Identifier), string("_", Delimiter)),
        ),
        # point types
        point_abbreviations,
    )(target)


# loading point labels from a CSV but this could be from BACnet
source = CSVIngress(
    data="""label
:BuildingName_02:FCU503_ChwVlvPos
:BuildingName_01:FCU336_OccHtgSptFnl
:BuildingName_02:FCU510_EffOcc
:BuildingName_02:FCU507_UnoccHtgSpt
:BuildingName_02:FCU415_UnoccHtgSpt
:BuildingName_01:FCU203_OccClgSpt
:BuildingName_02:FCU521_UO11_HwVlvOut
:BuildingName_01:FCU365_UnoccHtgSptFnl
:BuildingName_02:FCU529_UnoccHtgSpt
:BuildingName_01:FCU243_EffOcc
:BuildingName_01:FCU362_ChwVlvPos
:BuildingName_01:FCU180B_UnoccClgSptFnl
:BuildingName_02:FCU539_UO12_ChwVlvOut
:BuildingName_02:FCU428_BO4_HighSpdFanOut
:BuildingName_02:FCU416_RoomTmp
:BuildingName_02:FCU415_UI17_Fan_Status
:BuildingName_01:FCU391_HwVlvPos
:BuildingName_02:FCU559_UnoccHtgSpt
:BuildingName_01:FCU262_UI22_SaTmp
:BuildingName_02:FCU448_UO11_HwVlvOut
:BuildingName_01:FCU369_OccClgSptFnl
:BuildingName_01:FCU255_UI22_SaTmp
:BuildingName_02:FCU543_UI22_SaTmp
:BuildingName_01:FCU376_UI22_SaTmp
:BuildingName_01:FCU241_EffSysMode
:BuildingName_01:FCU343_ChwVlvPos
:BuildingName_01:FCU313_BO4_HighSpdFanOut
:BuildingName_02:FCU549_EffOcc
:BuildingName_01:FCU242_UI17_Fan_Status
:BuildingName_01:FCU392_UnoccHtgSptFnl
:BuildingName_01:FCU323_OccHtgSptFnl
:BuildingName_01:FCU311_OccHtgSpt
:BuildingName_01:FCU216_EffOcc
:BuildingName_01:FCU331_SysMode
:BuildingName_02:FCU558_FanMode
:BuildingName_01:FCU227_BO4_HighSpdFanOut
:BuildingName_01:FCU285_OccClgSpt
:BuildingName_01:FCU391_FanMode
:BuildingName_01:FCU367_EffOcc
:BuildingName_02:FCU439_HwVlvPos
:BuildingName_02:FCU438_HwVlvPos
:BuildingName_01:FCU235_HwVlvPos
:BuildingName_02:FCU439_RoomTmp
:BuildingName_01:FCU205_UI17_Fan_Status
:BuildingName_01:FCU239_OccHtgSpt
:BuildingName_02:FCU538_EffOcc
:BuildingName_02:FCU479_UnoccHtgSpt
:BuildingName_01:FCU292_SysMode
:BuildingName_02:FCU555_UO12_ChwVlvOut
:BuildingName_02:FCU489_UnoccClgSpt
:BuildingName_01:FCU331_UO12_ChwVlvOut
:BuildingName_01:FCU301_ChwVlvPos
:BuildingName_02:FCU448_ChwVlvPos
:BuildingName_02:FCU460_OccHtgSpt
:BuildingName_01:FCU319_UnoccClgSptFnl
:BuildingName_02:FCU401_OccClgSpt
:BuildingName_01:FCU311_UnoccClgSpt
:BuildingName_01:FCU261_UnoccHtgSptFnl
:BuildingName_01:FCU273_UnoccClgSpt
:BuildingName_02:FCU531_BO4_HighSpdFanOut
:BuildingName_02:FCU416_FanMode
:BuildingName_01:FCU223_OccCmd
:BuildingName_01:FCU342_UnoccHtgSpt
:BuildingName_02:FCU485_UO11_HwVlvOut
:BuildingName_01:FCU201_OccHtgSpt
:BuildingName_02:FCU438_UO11_HwVlvOut
:BuildingName_02:FCU539_Room_RH
:BuildingName_02:FCU452_EffSysMode
:BuildingName_01:FCU205_UnoccHtgSptFnl
:BuildingName_01:FCU210_UnoccHtgSptFnl
:BuildingName_02:FCU444_HwVlvPos
:BuildingName_01:FCU240_OccCmd
:BuildingName_01:FCU215_OccCmd
:BuildingName_01:FCU373_UO11_HwVlvOut
:BuildingName_01:FCU273_UI22_SaTmp
:BuildingName_01:FCU352_OccHtgSptFnl
:BuildingName_01:FCU307_OccHtgSptFnl
:BuildingName_02:FCU430_RoomTmp
:BuildingName_01:FCU277_OccHtgSptFnl
:BuildingName_01:FCU364_UO11_HwVlvOut
:BuildingName_01:FCU213_UI17_Fan_Status
:BuildingName_01:FCU276_OccCmd
:BuildingName_02:FCU505_BO4_HighSpdFanOut
:BuildingName_01:FCU292_UnoccClgSpt
:BuildingName_02:FCU507_OccHtgSpt
:BuildingName_02:FCU563_BO4_HighSpdFanOut
:BuildingName_02:FCU481_UI17_Fan_Status
:BuildingName_02:FCU444_UO12_ChwVlvOut
:BuildingName_02:FCU555_UI17_Fan_Status
:BuildingName_01:FCU289_UnoccClgSptFnl
:BuildingName_01:FCU285_OccClgSptFnl
:BuildingName_01:FCU254_UI17_Fan_Status
:BuildingName_01:FCU255_UnoccHtgSpt
:BuildingName_01:FCU282_UnoccHtgSptFnl
:BuildingName_02:FCU503_OccClgSpt
:BuildingName_02:FCU525_UnoccHtgSpt
:BuildingName_01:FCU283_OccClgSpt
:BuildingName_02:FCU465_FanMode
:BuildingName_02:FCU530_ChwVlvPos
:BuildingName_02:FCU486_UI17_Fan_Status
:BuildingName_01:FCU225_UnoccHtgSpt
:BuildingName_01:FDU123_UnoccHtgSpt"""
)

# hook our source of BMS labels to our naming convention parser
"""
ing = NamingConventionIngress(source, custom_parser)
for record in ing.records[:3]:
    # the 'fields' of the record are just the token format needed for semantic graph synthesis
    print(record.fields)

# quick error reporting on what labels did not work
ing.dump_failed_labels()
"""
