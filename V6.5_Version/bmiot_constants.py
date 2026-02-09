"""
BMIoT Configuration Constants and Reference Data
Based on: BD-Algorithm - BMIoT Platform Document (Dec 27, 2025)
Date: January 28, 2026

This module contains all constants, dropdown options, validation ranges,
and reference data from the BD-Algorithm PDF specification.
"""

# ============================================================================
# MODBUS FUNCTION CODES
# ============================================================================

FUNCTION_CODES = {
    1: "Read Coil Status",
    2: "Read Input Status", 
    3: "Read Holding Registers",
    4: "Read Input Registers",
    5: "Force Single Coil",
    6: "Preset Single Register",
    15: "Force Multiple Coils",
    16: "Preset Multiple Registers"
}

# Function codes categorized by read/write
READ_FUNCTION_CODES = [1, 2, 3, 4]
WRITE_FUNCTION_CODES = [5, 6, 15, 16]

# Coil values
COIL_OFF = 0x0000
COIL_ON = 0xFF00

# ============================================================================
# DATA FORMAT CODES (FMT)
# ============================================================================

DATA_FORMATS = {
    1: "FP32bit_BA",      # Float 32-bit Big Endian (AB order)
    2: "FP32bit_AB",      # Float 32-bit Little Endian (BA order)
    3: "UINT16bit",       # Unsigned 16-bit integer (MOST COMMON)
    4: "INT32bit_BA",     # Signed 32-bit Big Endian
    5: "INT32bit_AB",     # Signed 32-bit Little Endian
    6: "UINT32bit_BA",    # Unsigned 32-bit Big Endian
    7: "UINT32bit_AB",    # Unsigned 32-bit Little Endian
    8: "INT16bit"         # Signed 16-bit integer
}

# Format names for display (user-friendly)
DATA_FORMAT_DISPLAY = {
    1: "Float 32-bit (Big Endian)",
    2: "Float 32-bit (Little Endian)",
    3: "Unsigned 16-bit",
    4: "Signed 32-bit (Big Endian)",
    5: "Signed 32-bit (Little Endian)",
    6: "Unsigned 32-bit (Big Endian)",
    7: "Unsigned 32-bit (Little Endian)",
    8: "Signed 16-bit"
}

# Register length by format code
FORMAT_LENGTH = {
    1: 2,  # Float 32-bit = 2 registers
    2: 2,  # Float 32-bit = 2 registers
    3: 1,  # UINT16 = 1 register
    4: 2,  # INT32 = 2 registers
    5: 2,  # INT32 = 2 registers
    6: 2,  # UINT32 = 2 registers
    7: 2,  # UINT32 = 2 registers
    8: 1   # INT16 = 1 register
}

# ============================================================================
# DATA TYPE VALIDATION RANGES
# ============================================================================

DATA_TYPE_RANGES = {
    # Format Code: (min_value, max_value, description)
    1: (-3.4e38, 3.4e38, "Float 32-bit"),
    2: (-3.4e38, 3.4e38, "Float 32-bit"),
    3: (0, 65535, "Unsigned 16-bit"),
    4: (-2147483648, 2147483647, "Signed 32-bit"),
    5: (-2147483648, 2147483647, "Signed 32-bit"),
    6: (0, 4294967295, "Unsigned 32-bit"),
    7: (0, 4294967295, "Unsigned 32-bit"),
    8: (-32768, 32767, "Signed 16-bit")
}

# Data type names for Python type checking
DATA_TYPE_PYTHON = {
    1: float,
    2: float,
    3: int,
    4: int,
    5: int,
    6: int,
    7: int,
    8: int
}

# ============================================================================
# COMMUNICATION SETTINGS
# ============================================================================

BAUD_RATES = [9600, 19200, 38400, 57600, 115200]

DATA_FORMAT_OPTIONS = [
    "8N1",  # 8 data bits, No parity, 1 stop bit (MOST COMMON)
    "8E1",  # 8 data bits, Even parity, 1 stop bit
    "8O1",  # 8 data bits, Odd parity, 1 stop bit
    "7E1",  # 7 data bits, Even parity, 1 stop bit
    "7O1"   # 7 data bits, Odd parity, 1 stop bit
]

# ============================================================================
# ACCESS TYPES
# ============================================================================

ACCESS_TYPES = {
    'R': 'Read Only',
    'W': 'Write Only',
    'RW': 'Read/Write (Write + Verification)'
}

# ============================================================================
# PROFILE CONFIGURATIONS
# ============================================================================

PROFILE_TYPES = {
    0: "Multiple Slave, Different Types, Non-Uniform, Slave-by-Slave",
    1: "Multiple Slave, Same Type, Uniform, Slave-by-Slave",
    2: "Multiple Slave, Different Types, Non-Uniform, Single Send"
}

PROFILE_DESCRIPTIONS = {
    0: "Different parameters per slave, each slave sends separately",
    1: "Same parameter structure for all slaves, each slave sends separately",
    2: "Different parameters across slaves, all parameters sent in one message"
}

# ============================================================================
# FIRMWARE LIMITS
# ============================================================================

MAX_SLAVES = 50              # B3_szmax
MAX_PARAMETERS = 300         # B5_szmax
MAX_PACKETS = 150            # B4_szmax
MAX_REGISTERS_PER_PACKET = 70  # Packet split threshold
MAX_REGISTERS_TOTAL = 65535  # Modbus addressing limit

# Modbus standard limits
MIN_SLAVE_ID = 1
MAX_SLAVE_ID = 247
MIN_ADDRESS = 0
MAX_ADDRESS = 65535

# ============================================================================
# JSON BLOCK STRUCTURES
# ============================================================================

# Block B1 fields
B1_FIELDS = {
    'NOS': 'uint8_t',    # Number of Slaves
    'NOP': 'uint16_t',   # Number of Parameters
    'NPT': 'uint16_t',   # Number of Packets
    'NOR': 'uint16_t'    # Number of Registers
}

# Block B2 fields
B2_FIELDS = {
    'BR': 'uint32_t',    # Baud Rate
    'DF': 'char[4]'      # Data Format
}

# Block B3 fields
B3_FIELDS = {
    'SI': 'uint8_t[]',   # Slave IDs (array)
    'SP': 'uint16_t[]'   # Starting Packet (array)
}

# Block B4 fields
B4_FIELDS = {
    'SA': 'uint16_t[]',  # Starting Address (array)
    'NRT': 'uint16_t[]', # Number of Registers (array)
    'FC': 'uint8_t[]',   # Function Code (array)
    'SID': 'uint8_t[]'   # Slave ID (array)
}

# Block B5 fields
B5_FIELDS = {
    'ID': 'uint16_t[]',  # Parameter ID (array)
    'PN': 'uint16_t[]',  # Packet Number (array)
    'STA': 'uint16_t[]', # Start Address (array)
    'LN': 'uint8_t[]',   # Length (array)
    'FMT': 'uint8_t[]',  # Format (array)
    'MLT': 'float[]'     # Multiplier (array)
}

# Block B6 fields
B6_FIELDS = {
    'WP': 'uint16_t[]',  # Write Parameter indices (array)
    'RP': 'uint16_t[]'   # Read Parameter indices (array)
}

# Block P1 fields
P1_FIELDS = {
    'NLB': 'uint16_t',   # Number of Lua Buffer variables
    'NLBIN': 'uint16_t', # Number of Lua Buffer input variables
    'NMD': 'uint16_t'    # Number of Main data (cloud parameters)
}

# Block P2 fields
P2_FIELDS = {
    'LBI': 'uint16_t[]',  # Lua Buffer ID (array)
    'MPI': 'uint16_t[]',  # Modbus Parameter ID (array)
    'RPCI': 'uint8_t[]'   # RPC Command ID (array)
}

# Block P3 fields
P3_FIELDS = {
    'MDI': 'uint16_t[]',  # Main Data ID (array) - must be sequential [1,2,3,...]
    'MPI': 'uint16_t[]',  # Modbus Parameter ID (array)
    'LBI': 'uint16_t[]'   # Lua Buffer ID (array)
}

# JKY fields
JKY_FIELDS = {
    'JKA': 'array[3]'  # Json Key Array: [Equipment_Type, [Keys], [Equipment_Names]]
}

# JKC fields
JKC_FIELDS = {
    'JKH': 'char[15]',   # Json Header
    'EKS': 'char[15]'    # Equipment Key String (typically "Dkey" or "DKEY")
}

# NTC fields
NTC_FIELDS = {
    'IP': 'char[20]',    # IP Address
    'PT': 'char[8]',     # Port
    'CI': 'char[20]',    # Client ID
    'SN': 'uint8_t[]',   # Slave Numbers (array)
    'MI': 'char[20][]',  # Machine IDs (array)
    'MT': 'char[20][]',  # Machine Types (array)
    'DI': 'char[20]'     # Device ID
}

# MST fields
MST_FIELDS = {
    'PRF': 'uint8_t'     # Profile (0, 1, or 2)
}

# ============================================================================
# VALIDATION RULES
# ============================================================================

VALIDATION_RULES = {
    'slave_id': (MIN_SLAVE_ID, MAX_SLAVE_ID),
    'address': (MIN_ADDRESS, MAX_ADDRESS),
    'function_code': list(FUNCTION_CODES.keys()),
    'format_code': list(DATA_FORMATS.keys()),
    'profile': [0, 1, 2],
    'baud_rate': BAUD_RATES,
    'data_format': DATA_FORMAT_OPTIONS,
    'max_slaves': MAX_SLAVES,
    'max_parameters': MAX_PARAMETERS,
    'max_packets': MAX_PACKETS,
    'max_registers_per_packet': MAX_REGISTERS_PER_PACKET
}

# ============================================================================
# ERROR MESSAGES
# ============================================================================

ERROR_MESSAGES = {
    'slave_id_range': f"Slave ID must be between {MIN_SLAVE_ID} and {MAX_SLAVE_ID}",
    'address_range': f"Address must be between {MIN_ADDRESS} and {MAX_ADDRESS}",
    'invalid_fc': f"Function code must be one of: {list(FUNCTION_CODES.keys())}",
    'invalid_fmt': f"Format code must be one of: {list(DATA_FORMATS.keys())}",
    'invalid_profile': "Profile must be 0, 1, or 2",
    'max_slaves_exceeded': f"Number of slaves exceeds firmware limit of {MAX_SLAVES}",
    'max_parameters_exceeded': f"Number of parameters exceeds firmware limit of {MAX_PARAMETERS}",
    'max_packets_exceeded': f"Number of packets exceeds firmware limit of {MAX_PACKETS}",
    'max_registers_exceeded': f"Registers per packet exceeds limit of {MAX_REGISTERS_PER_PACKET}",
    'invalid_baud_rate': f"Baud rate must be one of: {BAUD_RATES}",
    'invalid_data_format': f"Data format must be one of: {DATA_FORMAT_OPTIONS}",
    'p1_nmd_mismatch': "P1.NMD must equal total JKY elements (Keys × Equipment_Names)",
    'p2_size_mismatch': "Size(P2.LBI) must equal Size(P2.MPI) + Size(P2.RPCI) = P1.NLBIN",
    'p3_mdi_not_sequential': "P3.MDI must be sequential [1, 2, 3, ...]",
    'value_out_of_range': "Value out of range for data type"
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def validate_value_range(value, format_code):
    """
    Validate if a value is within the valid range for its data type.
    
    Args:
        value: The value to validate
        format_code: The format code (1-8)
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if format_code not in DATA_TYPE_RANGES:
        return False, f"Invalid format code: {format_code}"
    
    min_val, max_val, type_name = DATA_TYPE_RANGES[format_code]
    
    # Check type
    expected_type = DATA_TYPE_PYTHON[format_code]
    if not isinstance(value, expected_type):
        return False, f"Value must be {expected_type.__name__} for {type_name}"
    
    # Check range
    if value < min_val or value > max_val:
        return False, f"Value {value} out of range [{min_val}, {max_val}] for {type_name}"
    
    return True, ""

def get_register_length(format_code):
    """
    Get the number of registers required for a data format.
    
    Args:
        format_code: The format code (1-8)
    
    Returns:
        int: Number of registers (1 or 2)
    """
    return FORMAT_LENGTH.get(format_code, 1)

def get_format_name(format_code):
    """
    Get the display name for a format code.
    
    Args:
        format_code: The format code (1-8)
    
    Returns:
        str: Format display name
    """
    return DATA_FORMAT_DISPLAY.get(format_code, f"Unknown ({format_code})")

def get_function_code_name(fc):
    """
    Get the name for a function code.
    
    Args:
        fc: The function code (1-16)
    
    Returns:
        str: Function code name
    """
    return FUNCTION_CODES.get(fc, f"Unknown ({fc})")

def is_read_function_code(fc):
    """
    Check if a function code is a read operation.
    
    Args:
        fc: The function code
    
    Returns:
        bool: True if read operation
    """
    return fc in READ_FUNCTION_CODES

def is_write_function_code(fc):
    """
    Check if a function code is a write operation.
    
    Args:
        fc: The function code
    
    Returns:
        bool: True if write operation
    """
    return fc in WRITE_FUNCTION_CODES

def validate_slave_id(slave_id):
    """
    Validate slave ID is in valid range.
    
    Args:
        slave_id: The slave ID to validate
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if not isinstance(slave_id, int):
        return False, "Slave ID must be an integer"
    
    if slave_id < MIN_SLAVE_ID or slave_id > MAX_SLAVE_ID:
        return False, ERROR_MESSAGES['slave_id_range']
    
    return True, ""

def validate_address(address):
    """
    Validate Modbus address is in valid range.
    
    Args:
        address: The address to validate
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if not isinstance(address, int):
        return False, "Address must be an integer"
    
    if address < MIN_ADDRESS or address > MAX_ADDRESS:
        return False, ERROR_MESSAGES['address_range']
    
    return True, ""

def validate_function_code(fc):
    """
    Validate function code is valid.
    
    Args:
        fc: The function code to validate
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if not isinstance(fc, int):
        return False, "Function code must be an integer"
    
    if fc not in FUNCTION_CODES:
        return False, ERROR_MESSAGES['invalid_fc']
    
    return True, ""

def validate_format_code(fmt):
    """
    Validate format code is valid.
    
    Args:
        fmt: The format code to validate
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if not isinstance(fmt, int):
        return False, "Format code must be an integer"
    
    if fmt not in DATA_FORMATS:
        return False, ERROR_MESSAGES['invalid_fmt']
    
    return True, ""

def validate_profile(profile):
    """
    Validate profile is valid.
    
    Args:
        profile: The profile to validate
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if not isinstance(profile, int):
        return False, "Profile must be an integer"
    
    if profile not in PROFILE_TYPES:
        return False, ERROR_MESSAGES['invalid_profile']
    
    return True, ""

# ============================================================================
# DROPDOWN OPTIONS FOR UI
# ============================================================================

# For tkinter Combobox values
DROPDOWN_OPTIONS = {
    'function_code': [f"{fc} - {name}" for fc, name in FUNCTION_CODES.items()],
    'data_format_code': [f"{code} - {name}" for code, name in DATA_FORMAT_DISPLAY.items()],
    'data_format_comm': DATA_FORMAT_OPTIONS,
    'baud_rate': [str(br) for br in BAUD_RATES],
    'access_type': [f"{code} - {name}" for code, name in ACCESS_TYPES.items()],
    'profile': [f"{p} - {desc}" for p, desc in PROFILE_DESCRIPTIONS.items()]
}

# For parsing dropdown selections back to values
def parse_dropdown_selection(dropdown_value, dropdown_type):
    """
    Parse a dropdown selection string back to its numeric value.
    
    Args:
        dropdown_value: The string from dropdown (e.g., "3 - Unsigned 16-bit")
        dropdown_type: Type of dropdown ('function_code', 'data_format_code', etc.)
    
    Returns:
        The numeric value or original string
    """
    if ' - ' in dropdown_value:
        try:
            return int(dropdown_value.split(' - ')[0])
        except ValueError:
            return dropdown_value
    return dropdown_value

# ============================================================================
# EXPORT ALL
# ============================================================================

__all__ = [
    # Function codes
    'FUNCTION_CODES', 'READ_FUNCTION_CODES', 'WRITE_FUNCTION_CODES',
    'COIL_OFF', 'COIL_ON',
    
    # Data formats
    'DATA_FORMATS', 'DATA_FORMAT_DISPLAY', 'FORMAT_LENGTH',
    'DATA_TYPE_RANGES', 'DATA_TYPE_PYTHON',
    
    # Communication
    'BAUD_RATES', 'DATA_FORMAT_OPTIONS',
    
    # Access types
    'ACCESS_TYPES',
    
    # Profiles
    'PROFILE_TYPES', 'PROFILE_DESCRIPTIONS',
    
    # Limits
    'MAX_SLAVES', 'MAX_PARAMETERS', 'MAX_PACKETS', 'MAX_REGISTERS_PER_PACKET',
    'MIN_SLAVE_ID', 'MAX_SLAVE_ID', 'MIN_ADDRESS', 'MAX_ADDRESS',
    
    # JSON structures
    'B1_FIELDS', 'B2_FIELDS', 'B3_FIELDS', 'B4_FIELDS', 'B5_FIELDS', 'B6_FIELDS',
    'P1_FIELDS', 'P2_FIELDS', 'P3_FIELDS', 'JKY_FIELDS', 'JKC_FIELDS', 'NTC_FIELDS', 'MST_FIELDS',
    
    # Validation
    'VALIDATION_RULES', 'ERROR_MESSAGES',
    
    # Helper functions
    'validate_value_range', 'get_register_length', 'get_format_name', 'get_function_code_name',
    'is_read_function_code', 'is_write_function_code',
    'validate_slave_id', 'validate_address', 'validate_function_code', 'validate_format_code',
    'validate_profile',
    
    # Dropdown options
    'DROPDOWN_OPTIONS', 'parse_dropdown_selection'
]
