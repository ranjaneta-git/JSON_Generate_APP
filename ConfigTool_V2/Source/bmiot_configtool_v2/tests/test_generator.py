"""Tests for the BMIoT ConfigTool generation engine.

Verifies the generator produces correct JSON output against known configs:
  - HeatPump_HP (2 slaves, 17 params, 5 packets, NLB=4, NMD=15)
  - Example7 (single VFD, 7 params, empty B6, NLB=1, NMD=7)
"""

import json
import os
import sys
import unittest
from pathlib import Path

# Ensure package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from bmiot_configtool_v2.engine.generator import generate
from bmiot_configtool_v2.engine.models import (
    CloudGroup,
    Device,
    NetworkConfig,
    NvsSlot,
    Project,
    Register,
    Slave,
)
from bmiot_configtool_v2.engine.validator import validate_output, validate_project


# ---------------------------------------------------------------------------
# Helper: build the HeatPump_HP project model
# ---------------------------------------------------------------------------

def build_heatpump_project() -> Project:
    """Build the exact Project that should produce HeatPump_HP JSON output.

    HeatPump_HP Modbus_Config:
      B1: NOS=2, NOP=17, NPT=5, NOR=27
      B2: BR=9600, DF="8N1"
      B3: SI=[1,2], SP=[1,5]
      B4: SA=[0,82,0,8,1], NRT=[9,12,1,1,4], FC=[3,3,6,6,1], SID=[1,1,1,1,2]
      B5: 17 params, all FMT=3, MLT=1
      B6: WP=[12,13], RP=[1,3]

    HeatPump_HP ParamMap_Config:
      P1: NLB=4, NLBIN=4, NMD=15
      P2: LBI=[1,2,3,4], MPI=[12,13,1,2], RPCI=[]
      P3: MDI=[1..15], MPI=[1,2,3,4,5,6,7,8,9,10,11,14,15,16,17], LBI=[]
      JKY.JKA: 5 entries, JKC: JKH=properties, EKS=DKEY
    """
    # --- Slave 1 (modbus addr 1): 13 registers ---
    # Read FC3: addresses 0,2,8, 82,83,84,85,86,87,92,93
    # Write FC6: addresses 0,8
    s1_regs = [
        # FC3 read holdings
        Register(name="HP_Run",     address=0,  fc=3, fmt=3, mlt=1, slave_id=1),
        Register(name="Circ_Run",   address=2,  fc=3, fmt=3, mlt=1, slave_id=1),
        Register(name="Setpoint_R", address=8,  fc=3, fmt=3, mlt=1, slave_id=1),
        Register(name="Fault1",     address=82, fc=3, fmt=3, mlt=1, slave_id=1),
        Register(name="Fault2",     address=83, fc=3, fmt=3, mlt=1, slave_id=1),
        Register(name="Fault3",     address=84, fc=3, fmt=3, mlt=1, slave_id=1),
        Register(name="Fault4",     address=85, fc=3, fmt=3, mlt=1, slave_id=1),
        Register(name="Fault5",     address=86, fc=3, fmt=3, mlt=1, slave_id=1),
        Register(name="Tank_T",     address=87, fc=3, fmt=3, mlt=1, slave_id=1),
        Register(name="Supply_T",   address=92, fc=3, fmt=3, mlt=1, slave_id=1),
        Register(name="Return_T",   address=93, fc=3, fmt=3, mlt=1, slave_id=1),
        # FC6 write registers
        Register(name="W_HP_Run",     address=0, fc=6, fmt=3, mlt=1, slave_id=1),
        Register(name="W_Setpoint",   address=8, fc=6, fmt=3, mlt=1, slave_id=1),
    ]

    # Mark read regs 1 and 2 (HP_Run, Circ_Run) as needing LBI
    s1_regs[0].needs_lbi_slot = True  # HP_Run (will be param 1)
    s1_regs[1].needs_lbi_slot = True  # Circ_Run (will be param 2)

    slave1 = Slave(modbus_id=1, registers=s1_regs)

    # --- Slave 2 (modbus addr 2): 4 registers ---
    # Read FC1: coils at addresses 1,2,3,4
    s2_regs = [
        Register(name="RO_PU1", address=1, fc=1, fmt=3, mlt=1, slave_id=2),
        Register(name="RO_PU2", address=2, fc=1, fmt=3, mlt=1, slave_id=2),
        Register(name="RO_PU3", address=3, fc=1, fmt=3, mlt=1, slave_id=2),
        Register(name="RO_PU4", address=4, fc=1, fmt=3, mlt=1, slave_id=2),
    ]
    slave2 = Slave(modbus_id=2, registers=s2_regs)

    device = Device(name="HeatPump", slaves=[slave1, slave2])

    # --- Cloud groups (JKA entries) ---
    # After generation, param IDs will be:
    #   S1 FC3: addr 0→1, 2→2, 8→3, 82→4, 83→5, 84→6, 85→7, 86→8, 87→9, 92→10, 93→11
    #   S1 FC6: addr 0→12, 8→13
    #   S2 FC1: addr 1→14, 2→15, 3→16, 4→17
    #
    # JKA consumption (for each name → for each key → one param):
    #   HP_Status:  [St] × [HP_Run, Circ_Run]     → params 1, 2
    #   HP_Setpoint:[DegC] × [Setpoint]            → param 3
    #   HP_Fault:   [St] × [Fault1..5]             → params 4,5,6,7,8
    #   HP_Temp:    [DegC] × [Tank_T,Supply_T,Return_T] → params 9,10,11
    #   RO_Plant:   [St] × [RO_PU1..4]            → params 14,15,16,17
    #
    # We assign Register references in consumption order.
    # Note: we reference the SAME Register objects from the slaves.
    cloud_groups = [
        CloudGroup(
            cluster_name="HP_Status",
            keys=["St"],
            equipment_names=["HP_Run", "Circ_Run"],
            source_type="modbus",
            registers=[s1_regs[0], s1_regs[1]],  # params 1, 2
        ),
        CloudGroup(
            cluster_name="HP_Setpoint",
            keys=["DegC"],
            equipment_names=["Setpoint"],
            source_type="modbus",
            registers=[s1_regs[2]],  # param 3
        ),
        CloudGroup(
            cluster_name="HP_Fault",
            keys=["St"],
            equipment_names=["Fault1", "Fault2", "Fault3", "Fault4", "Fault5"],
            source_type="modbus",
            registers=[s1_regs[3], s1_regs[4], s1_regs[5], s1_regs[6], s1_regs[7]],
        ),
        CloudGroup(
            cluster_name="HP_Temp",
            keys=["DegC"],
            equipment_names=["Tank_T", "Supply_T", "Return_T"],
            source_type="modbus",
            registers=[s1_regs[8], s1_regs[9], s1_regs[10]],
        ),
        CloudGroup(
            cluster_name="RO_Plant",
            keys=["St"],
            equipment_names=["RO_PU1", "RO_PU2", "RO_PU3", "RO_PU4"],
            source_type="modbus",
            registers=[s2_regs[0], s2_regs[1], s2_regs[2], s2_regs[3]],
        ),
    ]

    network = NetworkConfig(
        ip="18.191.222.62",
        port="1234",
        client_id="Lucas",
        slave_numbers=[1],
        machine_ids=["GWAY01"],
        machine_types=["GWAY"],
        device_id="GW01",
    )

    return Project(
        name="HeatPump_HP",
        baud_rate=9600,
        data_format="8N1",
        devices=[device],
        cloud_groups=cloud_groups,
        nvs_slots=[],
        network=network,
        profile=0,
    )


# ---------------------------------------------------------------------------
# Helper: build the Example7 project model (single VFD, read-only)
# ---------------------------------------------------------------------------

def build_example7_project() -> Project:
    """Build the project for Example7 (7 params, 1 slave, read-only, empty B6).

    Modbus_Config:
      B1: NOS=1, NOP=7, NPT=1, NOR=7
      B3: SI=[1], SP=[1]
      B4: SA=[0], NRT=[7], FC=[3], SID=[1]
      B5: 7 params, all FC3, FMT=3, MLT=1
      B6: WP=[], RP=[]

    ParamMap_Config:
      P1: NLB=1, NLBIN=1, NMD=7
      P2: LBI=[1], MPI=[1], RPCI=[]
      P3: MDI=[1..7], MPI=[1,2,3,4,5,6,7], LBI=[]
      JKA: [["VFD", ["STAT","ALARM","FREQ","VOLT","CURR","PWR","RNHR"], ["CW PMP VFD1"]]]
    """
    regs = [
        Register(name="STAT",  address=0, fc=3, fmt=3, mlt=1, slave_id=1),
        Register(name="ALARM", address=1, fc=3, fmt=3, mlt=1, slave_id=1),
        Register(name="FREQ",  address=2, fc=3, fmt=3, mlt=1, slave_id=1),
        Register(name="VOLT",  address=3, fc=3, fmt=3, mlt=1, slave_id=1),
        Register(name="CURR",  address=4, fc=3, fmt=3, mlt=1, slave_id=1),
        Register(name="PWR",   address=5, fc=3, fmt=3, mlt=1, slave_id=1),
        Register(name="RNHR",  address=6, fc=3, fmt=3, mlt=1, slave_id=1),
    ]

    # Only param 1 (STAT) needs an LBI slot
    regs[0].needs_lbi_slot = True

    slave = Slave(modbus_id=1, registers=regs)
    device = Device(name="VFD", slaves=[slave])

    cloud_groups = [
        CloudGroup(
            cluster_name="VFD",
            keys=["STAT", "ALARM", "FREQ", "VOLT", "CURR", "PWR", "RNHR"],
            equipment_names=["CW PMP VFD1"],
            source_type="modbus",
            registers=regs,  # all 7 regs in order → 7 keys × 1 name = 7 slots
        ),
    ]

    network = NetworkConfig(
        ip="18.191.222.62",
        port="1234",
        client_id="Lucas",
        slave_numbers=[1],
        machine_ids=["VFD01"],
        machine_types=["VFD"],
        device_id="GW01",
    )

    return Project(
        name="Example7",
        baud_rate=9600,
        data_format="8N1",
        devices=[device],
        cloud_groups=cloud_groups,
        nvs_slots=[],
        network=network,
        profile=0,
    )


# ===========================================================================
# Test Classes
# ===========================================================================


class TestHeatPumpGeneration(unittest.TestCase):
    """Test generator output against known HeatPump_HP JSON."""

    @classmethod
    def setUpClass(cls):
        cls.project = build_heatpump_project()
        cls.modbus, cls.parammap = generate(cls.project)

    # --- Modbus B1 ---
    def test_b1(self):
        b1 = self.modbus["B1"]
        self.assertEqual(b1["NOS"], 2)
        self.assertEqual(b1["NOP"], 17)
        self.assertEqual(b1["NPT"], 5)
        self.assertEqual(b1["NOR"], 27)

    # --- Modbus B2 ---
    def test_b2(self):
        b2 = self.modbus["B2"]
        self.assertEqual(b2["BR"], 9600)
        self.assertEqual(b2["DF"], "8N1")

    # --- Modbus B3 ---
    def test_b3(self):
        b3 = self.modbus["B3"]
        self.assertEqual(b3["SI"], [1, 2])
        self.assertEqual(b3["SP"], [1, 5])

    # --- Modbus B4 ---
    def test_b4(self):
        b4 = self.modbus["B4"]
        self.assertEqual(b4["SA"], [0, 82, 0, 8, 1])
        self.assertEqual(b4["NRT"], [9, 12, 1, 1, 4])
        self.assertEqual(b4["FC"], [3, 3, 6, 6, 1])
        self.assertEqual(b4["SID"], [1, 1, 1, 1, 2])

    # --- Modbus B5 ---
    def test_b5_id(self):
        self.assertEqual(self.modbus["B5"]["ID"], list(range(1, 18)))

    def test_b5_pn(self):
        self.assertEqual(
            self.modbus["B5"]["PN"],
            [1, 1, 1, 2, 2, 2, 2, 2, 2, 2, 2, 3, 4, 5, 5, 5, 5],
        )

    def test_b5_sta(self):
        self.assertEqual(
            self.modbus["B5"]["STA"],
            [0, 2, 8, 82, 83, 84, 85, 86, 87, 92, 93, 0, 8, 1, 2, 3, 4],
        )

    def test_b5_ln(self):
        self.assertEqual(self.modbus["B5"]["LN"], [1] * 17)

    def test_b5_fmt(self):
        self.assertEqual(self.modbus["B5"]["FMT"], [3] * 17)

    def test_b5_mlt(self):
        self.assertEqual(self.modbus["B5"]["MLT"], [1] * 17)

    # --- Modbus B6 ---
    def test_b6(self):
        b6 = self.modbus["B6"]
        self.assertEqual(b6["WP"], [12, 13])
        self.assertEqual(b6["RP"], [1, 3])

    # --- ParamMap P1 ---
    def test_p1(self):
        p1 = self.parammap["P1"]
        self.assertEqual(p1["NLB"], 4)
        self.assertEqual(p1["NLBIN"], 4)
        self.assertEqual(p1["NMD"], 15)

    # --- ParamMap P2 ---
    def test_p2(self):
        p2 = self.parammap["P2"]
        self.assertEqual(p2["LBI"], [1, 2, 3, 4])
        self.assertEqual(p2["MPI"], [12, 13, 1, 2])
        self.assertEqual(p2["RPCI"], [])

    # --- ParamMap P3 ---
    def test_p3(self):
        p3 = self.parammap["P3"]
        self.assertEqual(p3["MDI"], list(range(1, 16)))
        self.assertEqual(
            p3["MPI"],
            [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 14, 15, 16, 17],
        )
        self.assertEqual(p3["LBI"], [])

    # --- ParamMap JKY ---
    def test_jka(self):
        jka = self.parammap["JKY"]["JKA"]
        self.assertEqual(len(jka), 5)
        self.assertEqual(jka[0], ["HP_Status", ["St"], ["HP_Run", "Circ_Run"]])
        self.assertEqual(jka[1], ["HP_Setpoint", ["DegC"], ["Setpoint"]])
        self.assertEqual(jka[2], ["HP_Fault", ["St"], ["Fault1", "Fault2", "Fault3", "Fault4", "Fault5"]])
        self.assertEqual(jka[3], ["HP_Temp", ["DegC"], ["Tank_T", "Supply_T", "Return_T"]])
        self.assertEqual(jka[4], ["RO_Plant", ["St"], ["RO_PU1", "RO_PU2", "RO_PU3", "RO_PU4"]])

    # --- ParamMap JKC ---
    def test_jkc(self):
        jkc = self.parammap["JKC"]
        self.assertEqual(jkc["JKH"], "properties")
        self.assertEqual(jkc["EKS"], "DKEY")

    # --- ParamMap NTC ---
    def test_ntc(self):
        ntc = self.parammap["NTC"]
        self.assertEqual(ntc["IP"], "18.191.222.62")
        self.assertEqual(ntc["PT"], "1234")
        self.assertEqual(ntc["CI"], "Lucas")
        self.assertEqual(ntc["SN"], [1])
        self.assertEqual(ntc["MI"], ["GWAY01"])
        self.assertEqual(ntc["MT"], ["GWAY"])
        self.assertEqual(ntc["DI"], "GW01")

    # --- ParamMap MST ---
    def test_mst(self):
        self.assertEqual(self.parammap["MST"]["PRF"], 0)

    # --- Validation ---
    def test_pre_validation_passes(self):
        result = validate_project(self.project)
        self.assertTrue(result.ok, f"Pre-validation errors: {result.errors}")

    def test_post_validation_passes(self):
        result = validate_output(self.modbus, self.parammap)
        self.assertTrue(result.ok, f"Post-validation errors: {result.errors}")


class TestExample7Generation(unittest.TestCase):
    """Test generator output against known Example7 JSON (read-only VFD)."""

    @classmethod
    def setUpClass(cls):
        cls.project = build_example7_project()
        cls.modbus, cls.parammap = generate(cls.project)

    def test_b1(self):
        b1 = self.modbus["B1"]
        self.assertEqual(b1["NOS"], 1)
        self.assertEqual(b1["NOP"], 7)
        self.assertEqual(b1["NPT"], 1)
        self.assertEqual(b1["NOR"], 7)

    def test_b3(self):
        self.assertEqual(self.modbus["B3"]["SI"], [1])
        self.assertEqual(self.modbus["B3"]["SP"], [1])

    def test_b4(self):
        b4 = self.modbus["B4"]
        self.assertEqual(b4["SA"], [0])
        self.assertEqual(b4["NRT"], [7])
        self.assertEqual(b4["FC"], [3])
        self.assertEqual(b4["SID"], [1])

    def test_b5(self):
        b5 = self.modbus["B5"]
        self.assertEqual(b5["ID"], [1, 2, 3, 4, 5, 6, 7])
        self.assertEqual(b5["PN"], [1, 1, 1, 1, 1, 1, 1])
        self.assertEqual(b5["STA"], [0, 1, 2, 3, 4, 5, 6])

    def test_b6_empty(self):
        self.assertEqual(self.modbus["B6"]["WP"], [])
        self.assertEqual(self.modbus["B6"]["RP"], [])

    def test_p1(self):
        p1 = self.parammap["P1"]
        self.assertEqual(p1["NLB"], 1)
        self.assertEqual(p1["NLBIN"], 1)
        self.assertEqual(p1["NMD"], 7)

    def test_p2(self):
        p2 = self.parammap["P2"]
        self.assertEqual(p2["LBI"], [1])
        self.assertEqual(p2["MPI"], [1])
        self.assertEqual(p2["RPCI"], [])

    def test_p3(self):
        p3 = self.parammap["P3"]
        self.assertEqual(p3["MDI"], [1, 2, 3, 4, 5, 6, 7])
        self.assertEqual(p3["MPI"], [1, 2, 3, 4, 5, 6, 7])
        self.assertEqual(p3["LBI"], [])

    def test_jka(self):
        jka = self.parammap["JKY"]["JKA"]
        self.assertEqual(len(jka), 1)
        self.assertEqual(
            jka[0],
            ["VFD", ["STAT", "ALARM", "FREQ", "VOLT", "CURR", "PWR", "RNHR"], ["CW PMP VFD1"]],
        )

    def test_validations_pass(self):
        self.assertTrue(validate_project(self.project).ok)
        self.assertTrue(validate_output(self.modbus, self.parammap).ok)


class TestValidatorCatchesErrors(unittest.TestCase):
    """Test that validation rules trigger on known-bad input."""

    def test_v1_no_registers(self):
        p = Project(name="empty")
        result = validate_project(p)
        self.assertFalse(result.ok)
        self.assertTrue(any("V1" in e for e in result.errors))

    def test_v2_slave_id_out_of_range(self):
        reg = Register(name="x", address=0, fc=3, fmt=3, slave_id=300)
        slave = Slave(modbus_id=300, registers=[reg])
        device = Device(name="d", slaves=[slave])
        p = Project(name="t", devices=[device])
        result = validate_project(p)
        self.assertTrue(any("V2" in e for e in result.errors))

    def test_v3_duplicate_register(self):
        r1 = Register(name="a", address=0, fc=3, fmt=3, slave_id=1)
        r2 = Register(name="b", address=0, fc=3, fmt=3, slave_id=1)
        slave = Slave(modbus_id=1, registers=[r1, r2])
        device = Device(name="d", slaves=[slave])
        p = Project(name="t", devices=[device])
        result = validate_project(p)
        self.assertTrue(any("V3" in e for e in result.errors))

    def test_v4_invalid_fmt(self):
        reg = Register(name="x", address=0, fc=3, fmt=99, slave_id=1)
        slave = Slave(modbus_id=1, registers=[reg])
        device = Device(name="d", slaves=[slave])
        p = Project(name="t", devices=[device])
        result = validate_project(p)
        self.assertTrue(any("V4" in e for e in result.errors))

    def test_v6_invalid_baud(self):
        reg = Register(name="x", address=0, fc=3, fmt=3, slave_id=1)
        slave = Slave(modbus_id=1, registers=[reg])
        device = Device(name="d", slaves=[slave])
        p = Project(name="t", baud_rate=1234, devices=[device])
        result = validate_project(p)
        self.assertTrue(any("V6" in e for e in result.errors))

    def test_v11_nvs_key_too_long(self):
        reg = Register(name="x", address=0, fc=3, fmt=3, slave_id=1)
        slave = Slave(modbus_id=1, registers=[reg])
        device = Device(name="d", slaves=[slave])
        nvs = NvsSlot(key_name="a" * 20)
        p = Project(name="t", devices=[device], nvs_slots=[nvs])
        result = validate_project(p)
        self.assertTrue(any("V11" in e for e in result.errors))

    def test_v14_modbus_after_nvs_cloud_group(self):
        reg = Register(name="x", address=0, fc=3, fmt=3, slave_id=1)
        slave = Slave(modbus_id=1, registers=[reg])
        device = Device(name="d", slaves=[slave])
        nvs = NvsSlot(key_name="k1")
        cg_nvs = CloudGroup(
            cluster_name="NVS_Group", keys=["k"], equipment_names=["e"],
            source_type="nvs", nvs_slots=[nvs],
        )
        cg_mb = CloudGroup(
            cluster_name="MB_Group", keys=["k"], equipment_names=["e"],
            source_type="modbus", registers=[reg],
        )
        p = Project(
            name="t", devices=[device], nvs_slots=[nvs],
            cloud_groups=[cg_nvs, cg_mb],  # NVS before Modbus = error
        )
        result = validate_project(p)
        self.assertTrue(any("V14" in e for e in result.errors))

    def test_w9_nmd_jka_mismatch(self):
        """W9: NMD != JKA total slots should be caught."""
        # Manually create a bad output dict
        modbus = {
            "B1": {"NOS": 1, "NOP": 2, "NPT": 1, "NOR": 2},
            "B2": {"BR": 9600, "DF": "8N1"},
            "B3": {"SI": [1], "SP": [1]},
            "B4": {"SA": [0], "NRT": [2], "FC": [3], "SID": [1]},
            "B5": {"ID": [1, 2], "PN": [1, 1], "STA": [0, 1], "LN": [1, 1], "FMT": [3, 3], "MLT": [1, 1]},
            "B6": {"WP": [], "RP": []},
        }
        parammap = {
            "P1": {"NLB": 0, "NLBIN": 0, "NMD": 2},
            "P2": {"LBI": [], "MPI": [], "RPCI": []},
            "P3": {"MDI": [1, 2], "MPI": [1, 2], "LBI": []},
            "JKY": {"JKA": [["G", ["k"], ["n"]]]},  # 1×1 = 1 slot but NMD=2
            "JKC": {"JKH": "properties", "EKS": "DKEY"},
            "NTC": {"IP": "", "PT": "", "CI": "", "SN": [], "MI": [], "MT": [], "DI": ""},
            "MST": {"PRF": 0},
        }
        result = validate_output(modbus, parammap)
        self.assertTrue(any("W9" in e for e in result.errors))


class TestImportRoundTrip(unittest.TestCase):
    """Test import from real JSON files and re-generation produces matching output."""

    WORKSPACE = Path(__file__).resolve().parent.parent.parent

    def _load_json(self, rel_path: str) -> dict:
        fpath = self.WORKSPACE / rel_path
        if not fpath.exists():
            self.skipTest(f"Test file not found: {fpath}")
        with open(fpath, "r", encoding="utf-8-sig") as f:
            return json.load(f)

    def test_heatpump_import_roundtrip_b1(self):
        """Import HeatPump JSON, re-generate, verify B1 counts match."""
        from bmiot_configtool_v2.engine.importer import import_from_dicts

        modbus_orig = self._load_json("HeatPump_HP/Modbus_Config.json")
        parammap_orig = self._load_json("HeatPump_HP/ParamMap_Config.json")

        project = import_from_dicts(modbus_orig, parammap_orig, "HP_Import")
        modbus_new, parammap_new = generate(project)

        # B1 counts should match
        self.assertEqual(modbus_new["B1"]["NOS"], modbus_orig["B1"]["NOS"])
        self.assertEqual(modbus_new["B1"]["NOP"], modbus_orig["B1"]["NOP"])
        self.assertEqual(modbus_new["B1"]["NPT"], modbus_orig["B1"]["NPT"])
        self.assertEqual(modbus_new["B1"]["NOR"], modbus_orig["B1"]["NOR"])

        # Post-validation should pass
        result = validate_output(modbus_new, parammap_new)
        self.assertTrue(result.ok, f"Post-validation errors: {result.errors}")


if __name__ == "__main__":
    unittest.main()
