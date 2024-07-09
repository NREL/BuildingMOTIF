# import neccessary libraries
import re
from typing import List

from buildingmotif.label_parsing.parser import Parser
from buildingmotif.label_parsing.tokens import (
    Constant,
    Delimiter,
    Identifier,
    Null,
    Token,
    TokenOrConstructor,
    TokenResult,
    ensure_token,
)
from buildingmotif.namespaces import BRICK


class string(Parser):
    """Constructs a parser that matches a string."""

    def __init__(self, s: str, type_name: TokenOrConstructor):
        self.s = s
        self.type_name = type_name

    def __call__(self, target: str) -> List[TokenResult]:
        if target.startswith(self.s):
            return [
                TokenResult(self.s, ensure_token(self.type_name, self.s), len(self.s))
            ]
        return [
            TokenResult(
                None, Null(), 0, f"Expected {self.s}, got {target[:len(self.s)]}"
            )
        ]


class rest(Parser):
    """Constructs a parser that matches the rest of the string."""

    def __init__(self, type_name: TokenOrConstructor):
        self.type_name = type_name

    def __call__(self, target: str) -> List[TokenResult]:
        return [TokenResult(target, ensure_token(self.type_name, target), len(target))]


class substring_n(Parser):
    """Constructs a parser that matches a substring of length n."""

    def __init__(self, length: int, type_name: TokenOrConstructor):
        self.length = length
        self.type_name = type_name

    def __call__(self, target: str) -> List[TokenResult]:
        if len(target) >= self.length:
            value = target[: self.length]
            return [
                TokenResult(value, ensure_token(self.type_name, value), self.length)
            ]
        return [
            TokenResult(
                None,
                Null(),
                0,
                f"Expected {self.length} characters, got {target[:self.length]}",
            )
        ]


class regex(Parser):
    """Constructs a parser that matches a regular expression."""

    def __init__(self, r: str, type_name: TokenOrConstructor):
        self.r = r
        self.type_name = type_name

    def __call__(self, target: str) -> List[TokenResult]:
        match = re.match(self.r, target)
        if match:
            value = match.group()
            return [TokenResult(value, ensure_token(self.type_name, value), len(value))]
        return [
            TokenResult(
                None, Null(), 0, f"Expected {self.r}, got {target[:len(self.r)]}"
            )
        ]


class choice(Parser):
    """Constructs a choice combinator of parsers."""

    def __init__(self, *parsers):
        self.parsers = parsers

    def __call__(self, target: str) -> List[TokenResult]:
        errors = []
        for p in self.parsers:
            result = p(target)
            if result and not any(r.error for r in result):
                return result
            if result:
                errors.append(result[0].error)
        return [TokenResult(None, Null(), 0, " | ".join(errors))]


class constant(Parser):
    """Matches a constant token."""

    def __init__(self, type_name: Token):
        self.type_name = type_name

    def __call__(self, target: str) -> List[TokenResult]:
        return [TokenResult(None, self.type_name, 0)]


class abbreviations(Parser):
    """Constructs a choice combinator of string matching based on a dictionary."""

    def __init__(self, patterns):
        patterns = patterns
        parsers = [string(s, Constant(t)) for s, t in patterns.items()]
        self.choice = choice(*parsers)

    def __call__(self, target):
        return self.choice(target.upper())


class sequence(Parser):
    """Applies parsers in sequence. All parsers must match consecutively."""

    def __init__(self, *parsers):
        self.parsers = parsers

    def __call__(self, target: str) -> List[TokenResult]:
        results = []
        total_length = 0
        for p in self.parsers:
            result = p(target)
            if not result:
                raise Exception("Expected result")
            results.extend(result)
            # if there are any errors, return the results
            if any(r.error for r in result):
                return results
            # TODO: how to handle error?
            consumed_length = sum([r.length for r in result])
            target = target[consumed_length:]
            total_length += sum([r.length for r in result])
        return results


class many(Parser):
    """Applies the given sequence parser repeatedly until it stops matching."""

    def __init__(self, seq_parser):
        self.seq_parser = seq_parser

    def __call__(self, target):
        results = []
        while True:
            part = self.seq_parser(target)
            if not part or part[0].value is None:
                break
            results.extend(part)
            # add up the length of all the tokens
            total_length = sum([r.length for r in part])
            target = target[total_length:]
        return results


class maybe(Parser):
    """Applies the given parser, but does not fail if it does not match."""

    def __init__(self, parser: Parser):
        self.parser = parser

    def __call__(self, target):
        result = self.parser(target)
        # if the result is not empty and there are no errors, return the result, otherwise return a null token
        if result and not any(r.error for r in result):
            return result
        return [TokenResult(None, Null(), 0)]


class until(Parser):
    """
    Constructs a parser that matches everything until the given parser matches.
    STarts with a string length of 1 and increments it until the parser matches.
    """

    def __init__(self, parser, type_name: TokenOrConstructor):
        self.parser = parser
        self.type_name = type_name

    def __call__(self, target):
        length = 1
        while length <= len(target):
            result = self.parser(target[length:])
            if result and not any(r.error for r in result):
                return [
                    TokenResult(
                        target[:length],
                        ensure_token(self.type_name, target[:length]),
                        length,
                    )
                ]
            length += 1
        return [
            TokenResult(
                None, Null(), 0, f"Expected {self.type_name}, got {target[:length]}"
            )
        ]


class extend_if_match(Parser):
    """Adds the type to the token result."""

    def __init__(self, parser, type_name: Token):
        self.parser = parser
        self.type_name = type_name

    def __call__(self, target):
        result = self.parser(target)
        if result and not any(r.error for r in result):
            result.extend([TokenResult(None, self.type_name, 0)])
            return result
        return result


def as_identifier(parser):
    """
    If the parser matches, add a new Identifier token after
    every Constant token in the result. The Identifier token
    has the same string value as the Constant token.
    """

    def as_identifier_parser(target):
        result = parser(target)
        if result and not any(r.error for r in result):
            new_result = []
            for r in result:
                new_result.append(r)
                if isinstance(r.token, Constant):
                    # length of the new token must be given as 0 so that the substring
                    # is not double counted
                    new_result.append(TokenResult(r.value, Identifier(r.value), 0))
            return new_result
        return result

    return as_identifier_parser


COMMON_EQUIP_ABBREVIATIONS_BRICK = {
    "AHU": BRICK.Air_Handling_Unit,
    "FCU": BRICK.Fan_Coil_Unit,
    "VAV": BRICK.Variable_Air_Volume_Box,
    "CRAC": BRICK.Computer_Room_Air_Conditioner,
    "HX": BRICK.Heat_Exchanger,
    "PMP": BRICK.Pump,
    "RVAV": BRICK.Variable_Air_Volume_Box_With_Reheat,
    "HP": BRICK.Heat_Pump,
    "RTU": BRICK.Rooftop_Unit,
    "DMP": BRICK.Damper,
    "STS": BRICK.Status,
    "VLV": BRICK.Valve,
    "CHVLV": BRICK.Chilled_Water_Valve,
    "HWVLV": BRICK.Hot_Water_Valve,
    "VFD": BRICK.Variable_Frequency_Drive,
    "CT": BRICK.Cooling_Tower,
    "MAU": BRICK.Makeup_Air_Unit,
    "R": BRICK.Room,
    "A": BRICK.Air_Handling_Unit,
}


COMMON_POINT_ABBREVIATIONS = {
    "ART": BRICK.Room_Temperature_Sensor,
    "TSP": BRICK.Air_Temperature_Setpoint,
    "HSP": BRICK.Air_Temperature_Heating_Setpoint,
    "CSP": BRICK.Air_Temperature_Cooling_Setpoint,
    "SP": BRICK.Setpoint,
    "CHWST": BRICK.Leaving_Chilled_Water_Temperature_Sensor,
    "CHWRT": BRICK.Entering_Chilled_Water_Temperature_Sensor,
    "HWST": BRICK.Leaving_Hot_Water_Temperature_Sensor,
    "HWRT": BRICK.Entering_Hot_Water_Temperature_Sensor,
    "CO": BRICK.CO_Sensor,
    "CO2": BRICK.CO2_Sensor,
    "T": BRICK.Temperature_Sensor,
    "FS": BRICK.Flow_Sensor,
    "PS": BRICK.Pressure_Sensor,
    "DPS": BRICK.Differential_Pressure_Sensor,
}


COMMON_ABBREVIATIONS = abbreviations(
    {**COMMON_EQUIP_ABBREVIATIONS_BRICK, **COMMON_POINT_ABBREVIATIONS}
)

equip_abbreviations = abbreviations(COMMON_EQUIP_ABBREVIATIONS_BRICK)
point_abbreviations = abbreviations(COMMON_POINT_ABBREVIATIONS)
delimiters = regex(r"[._&:/\- ]", Delimiter)
identifier = regex(r"[a-zA-Z0-9]+", Identifier)
named_equip = sequence(equip_abbreviations, maybe(delimiters), identifier)
named_point = sequence(point_abbreviations, maybe(delimiters), identifier)
building_constant = constant(Constant(BRICK.Building))
up_to_delimiter = regex(r"[^_._:/\-]+", Identifier)

# ith mapped points to brick class embeddings
COMMON_GENERATED_ABBREVIATIONS = {
    "DEWPTTMP": BRICK.Dewpoint_Setpoint,
    "KTONHR": BRICK.Chilled_Water_Meter,
    "CHWVLV": BRICK.Chilled_Water_Valve,
    "ENTTMP": BRICK.Enthalpy_Sensor,
    "CHVLV": BRICK.Chilled_Water_Valve,
    "HWVLV": BRICK.Hot_Water_Valve,
    "CHWST": BRICK.Leaving_Chilled_Water_Temperature_Sensor,
    "CHWRT": BRICK.Chilled_Water_Temperature_Sensor,
    "HHW-R": BRICK.Hot_Water_Radiator,
    "HHW-S": BRICK.Hot_Water_System,
    "SPEED": BRICK.Fan_Speed_Command,
    "THERM": BRICK.Natural_Gas_Usage_Sensor,
    "SCHWP": BRICK.Chilled_Water_System_Enable_Command,
    "TCHWP": BRICK.Chilled_Water_Pump,
    "PRESS": BRICK.Pressure_Setpoint,
    "ZNTMP": BRICK.Zone_Air_Temperature_Setpoint,
    "LWTMP": BRICK.Leaving_Water_Temperature_Setpoint,
    "CRAC": BRICK.Computer_Room_Air_Conditioner,
    "RVAV": BRICK.Variable_Air_Volume_Box_With_Reheat,
    "HWST": BRICK.Leaving_Hot_Water_Temperature_Sensor,
    "HWRT": BRICK.Entering_Hot_Water_Temperature_Sensor,
    "CHWR": BRICK.Chilled_Water_System_Enable_Command,
    "CHWS": BRICK.Chilled_Water_System_Enable_Command,
    "CHWP": BRICK.Chilled_Water_Pump,
    "HHWP": BRICK.Hot_Water_Pump,
    "DMPR": BRICK.Damper_Command,
    "FFIL": BRICK.Final_Filter,
    "PFIL": BRICK.Pre_Filter_Status,
    "SCHW": BRICK.Chilled_Water_System,
    "ENTH": BRICK.Enthalpy_Setpoint,
    "AHU": BRICK.Air_Handling_Unit,
    "FCU": BRICK.Duct_Fan_Coil_Unit,
    "VAV": BRICK.Variable_Air_Volume_Box,
    "PMP": BRICK.Pump,
    "RTU": BRICK.Rooftop_Unit,
    "DMP": BRICK.Damper,
    "VFD": BRICK.Variable_Frequency_Drive,
    "MAU": BRICK.Makeup_Air_Unit,
    "ART": BRICK.Room_Temperature_Sensor,
    "TSP": BRICK.Air_Temperature_Setpoint,
    "HSP": BRICK.Air_Temperature_Heating_Setpoint,
    "CSP": BRICK.Air_Temperature_Cooling_Setpoint,
    "CO2": BRICK.CO2_Sensor,
    "STS": BRICK.Status,
    "VLV": BRICK.Valve,
    "DPS": BRICK.Differential_Pressure_Sensor,
    "BLR": BRICK.Boiler_Command,
    "CDW": BRICK.Condenser_Water_Temperature_Sensor,
    "CWP": BRICK.Condenser_Water_Pump,
    "DHW": BRICK.Domestic_Hot_Water_System_Enable_Command,
    "FEV": BRICK.Exhaust_Air_Temperature_Sensor,
    "GET": BRICK.Exhaust_Air_Temperature_Sensor,
    "GEV": BRICK.Gas_Pressure_Regulator_Valve,
    "LEF": BRICK.Exhaust_Air_Temperature_Sensor,
    "HHW": BRICK.Hot_Water_Temperature_Setpoint,
    "HPA": BRICK.Packaged_Air_Source_Heat_Pump,
    "HRU": BRICK.Heat_Recovery_Condensing_Unit,
    "HTX": BRICK.Radiator,
    "HUM": BRICK.Humidifier_Fault_Status,
    "LAB": BRICK.Enclosed_Office,
    "OAU": BRICK.Dedicated_Outdoor_Air_System_Unit,
    "PEM": BRICK.Electrical_Meter,
    "PWP": BRICK.Water_Pump,
    "SAV": BRICK.Return_Heating_Valve,
    "CLG": BRICK.Cooling_Command,
    "FLW": BRICK.Mixed_Air_Flow_Sensor,
    "HTG": BRICK.Heating_Command,
    "LSP": BRICK.Static_Pressure_Setpoint,
    "MUA": BRICK.Makeup_Air_Unit,
    "RHC": BRICK.Reheat_Valve,
    "TON": BRICK.Chilled_Water_Meter,
    "CHW": BRICK.Chilled_Water_System_Enable_Command,
    "HWP": BRICK.Hot_Water_Pump,
    "RAF": BRICK.Return_Fan,
    "SAF": BRICK.Supply_Fan,
    "FIL": BRICK.Intake_Air_Filter,
    "MIX": BRICK.Mixing_Valve,
    "RHT": BRICK.Reheat_Command,
    "ALM": BRICK.Alarm_Sensitivity_Parameter,
    "DEG": BRICK.Warm_Cool_Adjust_Sensor,
    "TMP": BRICK.Temperature_Setpoint,
    "PLT": BRICK.PVT_Panel,
    "ACC": BRICK.Air_Cooled_Chiller,
    "ACU": BRICK.Air_Cooling_Unit,
    "ACW": BRICK.Wall_Air_Conditioner,
    "ATS": BRICK.Automatic_Transfer_Switch,
    "BAT": BRICK.Battery,
    "BFP": BRICK.Backflow_Preventer_Valve,
    "BSB": BRICK.Electric_Baseboard_Radiator,
    "CMD": BRICK.CO2_Sensor,
    "CMI": BRICK.CO2_Sensor,
    "CMP": BRICK.Compressor,
    "COL": BRICK.Cooling_Coil,
    "CTR": BRICK.Cooling_Tower,
    "DCT": BRICK.Disconnect_Switch,
    "DEA": BRICK.Storage_Tank,
    "DPP": BRICK.Damper_Command,
    "EHC": BRICK.Fume_Hood,
    "EHF": BRICK.Fume_Hood,
    "EMS": BRICK.Energy_Storage_System,
    "EVP": BRICK.Dry_Cooler,
    "EXT": BRICK.Thermal_Expansion_Tank,
    "FMT": BRICK.Flow_Sensor,
    "FSD": BRICK.Fire_Safety_System,
    "GDS": BRICK.Gas_Sensor,
    "GTP": BRICK.Grease_Interceptor,
    "HCU": BRICK.Heat_Pump_Condensing_Unit,
    "HVU": BRICK.HVAC_Equipment,
    "HWC": BRICK.Hot_Water_Radiator,
    "ICE": BRICK.Chilled_Water_Loop,
    "KTL": BRICK.Steam_Radiator,
    "LCP": BRICK.Luminance_Command,
    "LGD": BRICK.Dimmer,
    "LOT": BRICK.Parking_Structure,
    "MCC": BRICK.Motor_Control_Center,
    "OZG": BRICK.Ozone_Level_Sensor,
    "PLB": BRICK.Plumbing_Room,
    "PTD": BRICK.Water_Pressure_Sensor,
    "PVT": BRICK.PVT_Panel,
    "REL": BRICK.Relay_Command,
    "RFM": BRICK.Refrigerant_Metering_Device,
    "RFR": BRICK.Chiller,
    "RRS": BRICK.Heat_Recovery_Condensing_Unit,
    "SDS": BRICK.Fire_Sensor,
    "SHS": BRICK.Humidifier_Fault_Status,
    "SWB": BRICK.Switch_Room,
    "THS": BRICK.Outside_Air_Humidity_Sensor,
    "TKW": BRICK.Hot_Water_Thermal_Energy_Storage_Tank,
    "TMR": BRICK.On_Timer_Sensor,
    "TMU": BRICK.Terminal_Unit,
    "TST": BRICK.Thermostat_Status,
    "TUS": BRICK.Steam_System,
    "UHH": BRICK.Thermal_Energy_Usage_Sensor,
    "UST": BRICK.Chilled_Water_Thermal_Energy_Storage_Tank,
    "VCP": BRICK.Pump_VFD,
    "WCC": BRICK.Condenser_Water_Temperature_Sensor,
    "WIN": BRICK.Blind,
    "HX": BRICK.Heat_Exchanger,
    "HP": BRICK.Heat_Pump,
    "CT": BRICK.Cooling_Tower,
    "SP": BRICK.Setpoint,
    "CO": BRICK.CO2_Alarm,
    "FS": BRICK.Flow_Sensor,
    "PS": BRICK.Air_Pressure_Sensor,
    "AC": BRICK.Wall_Air_Conditioner,
    "CH": BRICK.Centrifugal_Chiller,
    "DW": BRICK.Water_System,
    "EF": BRICK.Fan_VFD,
    "RF": BRICK.Return_Fan,
    "SF": BRICK.Supply_Fan,
    "UH": BRICK.Heat_Pump_Condensing_Unit,
    "CC": BRICK.Cooling_Coil,
    "DP": BRICK.Differential_Pressure_Setpoint,
    "EA": BRICK.Intake_Air_Filter,
    "HC": BRICK.Heating_Coil,
    "LT": BRICK.Low_Temperature_Alarm,
    "MA": BRICK.Mixed_Air_Filter,
    "VP": BRICK.Velocity_Pressure_Setpoint,
    "RA": BRICK.Return_Air_Filter,
    "SA": BRICK.Supply_Air_Plenum,
    "RH": BRICK.Relative_Humidity_Sensor,
    "AL": BRICK.Alarm_Sensitivity_Parameter,
    "R": BRICK.Prayer_Room,
    "A": BRICK.Alarm,
    "T": BRICK.Temperature_Parameter,
    "C": BRICK.Command,
    "H": BRICK.High_Humidity_Alarm,
    "P": BRICK.Pressure_Setpoint,
    "S": BRICK.Status,
}
