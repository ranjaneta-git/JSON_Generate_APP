"""
Transform Wrapper - Convenience Functions
==========================================

Simple wrapper functions for bidirectional transformation.
Provides easy-to-use function interfaces for the GUI application.

Author: Firmware-aware Application Developer
Version: 1.0
Date: February 6, 2026
"""

import json
from reverse_engine import ReverseTransformationEngine
from forward_engine import ForwardTransformationEngine


def forward_transform(register_config_path: str, 
                      output_modbus_path: str, 
                      output_paramap_path: str,
                      baudrate: int = 38400,
                      data_format: str = "8N1",
                      profile: int = 0):
    """
    Forward transformation: Register Entry JSON → Modbus + Paramap JSON
    
    Args:
        register_config_path: Path to input Register_Config.json
        output_modbus_path: Path to output Modbus_Config.json
        output_paramap_path: Path to output ParamMap_Config.json
        baudrate: Modbus baudrate (default: 38400)
        data_format: Data format string (default: "8N1")
        profile: Profile type 0, 1, or 2 (default: 0)
    
    Returns:
        Dictionary with status and file paths
    """
    try:
        # Load register configuration
        with open(register_config_path, 'r') as f:
            register_config = json.load(f)
        
        # Create engine and transform
        engine = ForwardTransformationEngine()
        result = engine.transform(
            register_config.get('registers', []),
            baudrate=baudrate,
            data_format=data_format,
            profile=profile
        )
        
        # Save outputs
        with open(output_modbus_path, 'w') as f:
            json.dump(result['modbus_config'], f, indent=2)
        
        with open(output_paramap_path, 'w') as f:
            json.dump(result['paramap_config'], f, indent=2)
        
        return {
            'status': 'success',
            'modbus_path': output_modbus_path,
            'paramap_path': output_paramap_path
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }


def reverse_transform(modbus_config_path: str, 
                      paramap_config_path: str,
                      output_register_path: str):
    """
    Reverse transformation: Modbus + Paramap JSON → Register Entry JSON
    
    Args:
        modbus_config_path: Path to input Modbus_Config.json
        paramap_config_path: Path to input ParamMap_Config.json
        output_register_path: Path to output Register_Config.json
    
    Returns:
        Dictionary with status and file path
    """
    try:
        # Load input JSONs
        with open(modbus_config_path, 'r') as f:
            modbus_config = json.load(f)
        
        with open(paramap_config_path, 'r') as f:
            paramap_config = json.load(f)
        
        # Create engine and transform
        engine = ReverseTransformationEngine()
        result = engine.transform(modbus_config, paramap_config)
        
        # Save output
        with open(output_register_path, 'w') as f:
            json.dump(result, f, indent=2)
        
        return {
            'status': 'success',
            'register_path': output_register_path,
            'registers': result.get('registers', [])
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }
