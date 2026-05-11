"""Firmware constants and lookup tables for BMIoT gateway configuration."""

# --- Packet Limits ---
MAX_NRT = 60  # Maximum registers per transaction (firmware buffer size)

# --- Firmware Hard Limits (MBConfig_BlockAlloc) ---
MAX_NOS = 50    # Max number of slaves
MAX_NPT = 150   # Max number of packets
MAX_NOP = 300   # Max number of parameters
MAX_NOR = 1500  # Max total register slots

# --- Valid Function Codes ---
READ_FCS = frozenset({1, 2, 3, 4})
WRITE_FCS = frozenset({5, 6})
ALL_FCS = READ_FCS | WRITE_FCS

# FC descriptions for UI
FC_NAMES = {
    1: "Read Coils",
    2: "Read Discrete Inputs",
    3: "Read Holding Registers",
    4: "Read Input Registers",
    5: "Write Single Coil",
    6: "Write Single Register",
}

# --- FMT Codes and LN Mapping ---
# FMT → (description, LN)
FMT_TABLE = {
    1: ("Float32 (BA, low word first)", 2),
    2: ("Float32 (AB, high word first)", 2),
    3: ("Unsigned 16-bit", 1),
    4: ("Signed 32-bit (BA)", 2),
    5: ("Signed 32-bit (AB)", 2),
    6: ("Unsigned 32-bit (BA)", 2),
    7: ("Unsigned 32-bit (AB)", 2),
    8: ("Signed 16-bit", 1),
}

VALID_FMTS = frozenset(FMT_TABLE.keys())

def fmt_to_ln(fmt: int) -> int:
    """Return register length (1 for 16-bit, 2 for 32-bit) for a given FMT code."""
    return FMT_TABLE[fmt][1]

# --- Serial Settings ---
VALID_BAUD_RATES = frozenset({9600, 19200, 38400, 57600, 115200})
VALID_DATA_FORMATS = frozenset({"8N1", "8E1", "8O1", "8N2"})

# --- Link A FC Mapping ---
# Write FC → complementary Read FC for verify (same address)
LINK_A_FC_MAP = {
    5: 1,   # Write Coil → Read Coils
    6: 3,   # Write Register → Read Holdings
}

# --- NVS ---
MAX_NVS_KEY_LEN = 15

# --- Slave Address Range ---
MIN_SLAVE_ID = 1
MAX_SLAVE_ID = 247
