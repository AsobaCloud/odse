"""
SCL (Substation Configuration Language) Parser

Parses IEC 61850 SCL files (.scd, .cid) to extract asset hierarchy
and measurement mappings for ODS-E integration.

Design Strategy:
- Asset Discovery: Parse Substation → VoltageLevel → Bay → IED hierarchy
- Measurement Mapping: Map MMTR (metering) and MMXU (measurements) to ODS-E fields
- High-performance XML traversal using lxml
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass


@dataclass
class SCLAsset:
    """Represents an asset extracted from SCL hierarchy."""
    asset_id: str
    asset_type: str
    substation: str
    voltage_level: str
    bay: str
    ied_name: str
    description: Optional[str] = None
    measurements: Optional[Dict[str, Any]] = None


@dataclass
class SCLMeasurement:
    """Represents a measurement mapping from SCL to ODS-E."""
    ied_name: str
    ln_class: str
    measurement_type: str  # e.g., "TotWh", "W", "V", "A"
    ods_e_field: str  # e.g., "kWh", "kW", "voltage_ac", "current_ac"
    xpath: str


class SCLParser:
    """
    Parser for IEC 61850 SCL files.
    
    Extracts asset hierarchy and measurement mappings from .scd/.cid files.
    """
    
    def __init__(self, scd_path: Union[str, Path]):
        """
        Initialize the SCL parser.
        
        Args:
            scd_path: Path to the .scd or .cid file
        """
        self.scd_path = Path(scd_path)
        self._tree = None
        self._ns = {"scl": "http://www.iec.ch/61850/2003/SCL"}
        
    def _load_xml(self):
        """Load and parse the XML file using lxml."""
        try:
            from lxml import etree
        except ImportError:
            raise ImportError(
                "lxml is required for SCL parsing. "
                "Install with: pip install lxml"
            )
        
        if not self.scd_path.exists():
            raise FileNotFoundError(f"SCL file not found: {self.scd_path}")
        
        self._tree = etree.parse(str(self.scd_path))
        
    def extract_assets(self) -> List[SCLAsset]:
        """
        Extract asset hierarchy from SCL file.
        
        Returns:
            List of SCLAsset objects representing the plant hierarchy
        """
        if self._tree is None:
            self._load_xml()
        
        assets = []
        
        # Find all Substation elements
        substations = self._tree.xpath("//scl:Substation", namespaces=self._ns)
        
        for substation in substations:
            substation_name = substation.get("name", "Unknown")
            substation_desc = substation.get("desc", "")
            
            # Find all VoltageLevel elements within this substation
            voltage_levels = substation.xpath("./scl:VoltageLevel", namespaces=self._ns)
            
            for voltage_level in voltage_levels:
                vl_name = voltage_level.get("name", "Unknown")
                vl_desc = voltage_level.get("desc", "")
                
                # Find all Bay elements within this voltage level
                bays = voltage_level.xpath("./scl:Bay", namespaces=self._ns)
                
                for bay in bays:
                    bay_name = bay.get("name", "Unknown")
                    bay_desc = bay.get("desc", "")
                    
                    # Find all LNode elements to get IED references
                    lnodes = bay.xpath("./scl:LNode", namespaces=self._ns)
                    
                    for lnode in lnodes:
                        ied_name = lnode.get("iedName")
                        ln_class = lnode.get("lnClass")
                        
                        if ied_name:
                            # Determine asset type based on logical node class
                            asset_type = self._derive_asset_type(ln_class, bay_name)
                            
                            # Generate asset_id following ODS-E convention
                            asset_id = self._generate_asset_id(
                                substation_name, vl_name, bay_name, ied_name
                            )
                            
                            asset = SCLAsset(
                                asset_id=asset_id,
                                asset_type=asset_type,
                                substation=substation_name,
                                voltage_level=vl_name,
                                bay=bay_name,
                                ied_name=ied_name,
                                description=f"{substation_desc} > {vl_desc} > {bay_desc}".strip(" > ")
                            )
                            assets.append(asset)
        
        return assets
    
    def extract_measurements(self, ied_name: Optional[str] = None) -> List[SCLMeasurement]:
        """
        Extract measurement mappings from SCL file.
        
        Args:
            ied_name: Optional IED name to filter measurements. If None, extracts all.
            
        Returns:
            List of SCLMeasurement objects mapping SCL measurements to ODS-E fields
        """
        if self._tree is None:
            self._load_xml()
        
        measurements = []
        
        # Find all IED elements
        ieds = self._tree.xpath("//scl:IED", namespaces=self._ns)
        
        for ied in ieds:
            current_ied_name = ied.get("name")
            
            # Filter by ied_name if specified
            if ied_name and current_ied_name != ied_name:
                continue
            
            # Find all LN (Logical Node) elements within this IED
            lns = ied.xpath(".//scl:LN", namespaces=self._ns)
            
            for ln in lns:
                ln_class = ln.get("lnClass")
                
                # Process MMTR (Metering) logical nodes
                if ln_class == "MMTR":
                    mmtr_measurements = self._extract_mmtr_measurements(
                        current_ied_name, ln
                    )
                    measurements.extend(mmtr_measurements)
                
                # Process MMXU (Measurements) logical nodes
                elif ln_class == "MMXU":
                    mmxu_measurements = self._extract_mmxu_measurements(
                        current_ied_name, ln
                    )
                    measurements.extend(mmxu_measurements)
        
        return measurements
    
    def _extract_mmtr_measurements(
        self, ied_name: str, ln: Any
    ) -> List[SCLMeasurement]:
        """Extract metering measurements from MMTR logical node."""
        measurements = []
        
        # Look for TotWh (Total Active Energy)
        tot_wh_doi = ln.xpath("./scl:DOI[@name='TotWh']", namespaces=self._ns)
        
        if tot_wh_doi:
            xpath = f".//IED[@name='{ied_name}']//LN[@lnClass='MMTR']//DOI[@name='TotWh']"
            measurements.append(
                SCLMeasurement(
                    ied_name=ied_name,
                    ln_class="MMTR",
                    measurement_type="TotWh",
                    ods_e_field="kWh",
                    xpath=xpath
                )
            )
        
        return measurements
    
    def _extract_mmxu_measurements(
        self, ied_name: str, ln: Any
    ) -> List[SCLMeasurement]:
        """Extract electrical measurements from MMXU logical node."""
        measurements = []
        
        # Mapping of SCL measurement names to ODS-E fields
        measurement_map = {
            "W": "kW",        # Active Power
            "V": "voltage_ac", # Voltage
            "A": "current_ac", # Current
            "Hz": "frequency", # Frequency
            "PF": "PF",       # Power Factor
            "VA": "kVA",      # Apparent Power
            "VAr": "kVAr",   # Reactive Power
        }
        
        for scl_name, ods_e_field in measurement_map.items():
            doi = ln.xpath(f"./scl:DOI[@name='{scl_name}']", namespaces=self._ns)
            
            if doi:
                xpath = f".//IED[@name='{ied_name}']//LN[@lnClass='MMXU']//DOI[@name='{scl_name}']"
                measurements.append(
                    SCLMeasurement(
                        ied_name=ied_name,
                        ln_class="MMXU",
                        measurement_type=scl_name,
                        ods_e_field=ods_e_field,
                        xpath=xpath
                    )
                )
        
        return measurements
    
    def _derive_asset_type(self, ln_class: Optional[str], bay_name: str) -> str:
        """Derive asset type from logical node class and bay name."""
        if ln_class == "MMTR":
            return "meter"
        if ln_class == "MMXU":
            return "inverter"
        
        # Fallback: infer from bay name
        bay_lower = bay_name.lower()
        if "inv" in bay_lower or "inverter" in bay_lower:
            return "inverter"
        if "meter" in bay_lower:
            return "meter"
        if "feeder" in bay_lower:
            return "feeder"
        if "transformer" in bay_lower or "tx" in bay_lower:
            return "transformer"
        
        return "unknown"
    
    def _generate_asset_id(
        self, substation: str, voltage_level: str, bay: str, ied_name: str
    ) -> str:
        """
        Generate ODS-E compliant asset_id from SCL hierarchy.
        
        Format: {substation}:{voltage_level}:{bay}:{ied_name}
        """
        # Normalize names to be URL-safe
        def normalize(name: str) -> str:
            return name.replace(" ", "-").replace("_", "-").lower()
        
        return f"{normalize(substation)}:{normalize(voltage_level)}:{normalize(bay)}:{normalize(ied_name)}"
    
    def to_odse_metadata(self) -> Dict[str, Any]:
        """
        Convert SCL hierarchy to ODS-E asset-metadata.json format.
        
        Returns:
            Dictionary in ODS-E asset metadata format
        """
        assets = self.extract_assets()
        
        metadata = {
            "version": "1.0",
            "source": "SCL",
            "source_file": str(self.scd_path),
            "assets": []
        }
        
        for asset in assets:
            asset_dict = {
                "asset_id": asset.asset_id,
                "asset_type": asset.asset_type,
                "description": asset.description,
                "location": {
                    "substation": asset.substation,
                    "voltage_level": asset.voltage_level,
                    "bay": asset.bay
                },
                "oem_reference": {
                    "ied_name": asset.ied_name,
                    "protocol": "IEC-61850"
                }
            }
            metadata["assets"].append(asset_dict)
        
        return metadata


class SCLMetadataExtractor:
    """
    High-level interface for extracting metadata from SCL files.
    
    Provides convenience methods for common SCL parsing workflows.
    """
    
    def __init__(self, scd_path: Union[str, Path]):
        """
        Initialize the metadata extractor.
        
        Args:
            scd_path: Path to the .scd or .cid file
        """
        self.parser = SCLParser(scd_path)
    
    def extract_all(self) -> Dict[str, Any]:
        """
        Extract all metadata from SCL file.
        
        Returns:
            Complete metadata dictionary including assets and measurements
        """
        metadata = self.parser.to_odse_metadata()
        
        # Add measurement mappings
        measurements = self.parser.extract_measurements()
        metadata["measurement_mappings"] = [
            {
                "ied_name": m.ied_name,
                "ln_class": m.ln_class,
                "scl_measurement": m.measurement_type,
                "ods_e_field": m.ods_e_field,
                "xpath": m.xpath
            }
            for m in measurements
        ]
        
        return metadata
    
    def save_metadata(self, output_path: Union[str, Path]):
        """
        Extract and save metadata to JSON file.
        
        Args:
            output_path: Path to save the metadata JSON file
        """
        import json
        
        metadata = self.extract_all()
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
