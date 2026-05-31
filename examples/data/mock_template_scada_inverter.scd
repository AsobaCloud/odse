<?xml version="1.0" encoding="UTF-8"?>
<SCL xmlns="http://www.iec.ch/61850/2003/SCL" version="2007" revision="B" release="4">
  <Header id="Template_SCADA_Inverter" version="1.0" revision="1">
    <Text>Template SCADA Inverter Configuration</Text>
  </Header>
  
  <Substation name="SolarPlant_A" desc="Solar Power Plant A">
    <VoltageLevel name="LV" desc="Low Voltage 400V" nomFreq="50.0" numPhases="3">
      <Voltage unit="V" multiplier="m">400</Voltage>
      <Bay name="InverterBay_01" desc="Inverter Bay 1">
        <ConductingEquipment type="CTR" name="CT_Inv01" desc="Current Transformer Inverter 1"/>
        <ConductingEquipment type="VTR" name="VT_Inv01" desc="Voltage Transformer Inverter 1"/>
        
        <LNode iedName="TEMPLATE_INV_01" lnClass="MMXU" lnInst="1" lnType="MMXU1"/>
        <LNode iedName="TEMPLATE_INV_01" lnClass="MMTR" lnInst="1" lnType="MMTR1"/>
      </Bay>
      
      <Bay name="InverterBay_02" desc="Inverter Bay 2">
        <ConductingEquipment type="CTR" name="CT_Inv02" desc="Current Transformer Inverter 2"/>
        <ConductingEquipment type="VTR" name="VT_Inv02" desc="Voltage Transformer Inverter 2"/>
        
        <LNode iedName="TEMPLATE_INV_02" lnClass="MMXU" lnInst="1" lnType="MMXU1"/>
        <LNode iedName="TEMPLATE_INV_02" lnClass="MMTR" lnInst="1" lnType="MMTR1"/>
      </Bay>
    </VoltageLevel>
    
    <VoltageLevel name="MV" desc="Medium Voltage 11kV" nomFreq="50.0" numPhases="3">
      <Voltage unit="V" multiplier="k">11</Voltage>
      <Bay name="FeederBay_01" desc="Main Feeder Bay">
        <ConductingEquipment type="CBR" name="CB_Feeder01" desc="Circuit Breaker Feeder 1"/>
        <LNode iedName="TEMPLATE_FEEDER_01" lnClass="MMXU" lnInst="1" lnType="MMXU1"/>
      </Bay>
    </VoltageLevel>
  </Substation>
  
  <IED name="TEMPLATE_INV_01" type="Inverter" manufacturer="Template" desc="Template Inverter IED 1">
    <Services>
      <DynAssociation/>
      <GetDirectory/>
      <GetDataObjectDefinition/>
      <GetDataSetValue/>
      <SetDataSetValue/>
      <ConfDataSet/>
      <ConfReportControl/>
    </Services>
    <AccessPoint name="S1">
      <Server>
        <Authentication/>
        <LDevice inst="LD0">
          <LN0 lnClass="LLN0" inst="1" lnType="LLN0"/>
          
          <!-- Measurement Unit for Electrical Parameters -->
          <LN lnClass="MMXU" inst="1" lnType="MMXU1" desc="Measurement Unit">
            <DOI name="W">
              <DAI name="mag">
                <Val>125.5</Val>
              </DAI>
            </DOI>
            <DOI name="A">
              <DAI name="mag">
                <Val>180.2</Val>
              </DAI>
            </DOI>
            <DOI name="V">
              <DAI name="mag">
                <Val>400.0</Val>
              </DAI>
            </DOI>
          </LN>
          
          <!-- Metering Unit for Energy -->
          <LN lnClass="MMTR" inst="1" lnType="MMTR1" desc="Metering Unit">
            <DOI name="TotWh">
              <DAI name="mag">
                <Val>15250.75</Val>
              </DAI>
            </DOI>
          </LN>
        </LDevice>
      </Server>
    </AccessPoint>
  </IED>
  
  <IED name="TEMPLATE_INV_02" type="Inverter" manufacturer="Template" desc="Template Inverter IED 2">
    <Services>
      <DynAssociation/>
      <GetDirectory/>
      <GetDataObjectDefinition/>
      <GetDataSetValue/>
      <SetDataSetValue/>
      <ConfDataSet/>
      <ConfReportControl/>
    </Services>
    <AccessPoint name="S1">
      <Server>
        <Authentication/>
        <LDevice inst="LD0">
          <LN0 lnClass="LLN0" inst="1" lnType="LLN0"/>
          
          <LN lnClass="MMXU" inst="1" lnType="MMXU1" desc="Measurement Unit">
            <DOI name="W">
              <DAI name="mag">
                <Val>98.3</Val>
              </DAI>
            </DOI>
            <DOI name="A">
              <DAI name="mag">
                <Val>142.1</Val>
              </DAI>
            </DOI>
            <DOI name="V">
              <DAI name="mag">
                <Val>398.5</Val>
              </DAI>
            </DOI>
          </LN>
          
          <LN lnClass="MMTR" inst="1" lnType="MMTR1" desc="Metering Unit">
            <DOI name="TotWh">
              <DAI name="mag">
                <Val>12100.25</Val>
              </DAI>
            </DOI>
          </LN>
        </LDevice>
      </Server>
    </AccessPoint>
  </IED>
  
  <IED name="TEMPLATE_FEEDER_01" type="Feeder" manufacturer="Template" desc="Template Feeder IED 1">
    <Services>
      <DynAssociation/>
      <GetDirectory/>
      <GetDataObjectDefinition/>
      <GetDataSetValue/>
      <SetDataSetValue/>
      <ConfDataSet/>
      <ConfReportControl/>
    </Services>
    <AccessPoint name="S1">
      <Server>
        <Authentication/>
        <LDevice inst="LD0">
          <LN0 lnClass="LLN0" inst="1" lnType="LLN0"/>
          
          <LN lnClass="MMXU" inst="1" lnType="MMXU1" desc="Measurement Unit">
            <DOI name="W">
              <DAI name="mag">
                <Val>223.8</Val>
              </DAI>
            </DOI>
            <DOI name="A">
              <DAI name="mag">
                <Val>322.3</Val>
              </DAI>
            </DOI>
            <DOI name="V">
              <DAI name="mag">
                <Val>11000.0</Val>
              </DAI>
            </DOI>
          </LN>
        </LDevice>
      </Server>
    </AccessPoint>
  </IED>
  
  <DataTypeTemplates>
    <LNodeType id="LLN0" desc="Logical Node Zero">
      <DO name="Mod" type="ENC_Mod"/>
      <DO name="Beh" type="ENS_Beh"/>
    </LNodeType>
    
    <LNodeType id="MMXU1" desc="Measurement Unit">
      <DO name="W" type="MV_W"/>
      <DO name="A" type="MV_A"/>
      <DO name="V" type="MV_V"/>
    </LNodeType>
    
    <LNodeType id="MMTR1" desc="Metering Unit">
      <DO name="TotWh" type="MV_TotWh"/>
    </LNodeType>
    
    <DOType id="ENC_Mod" cdc="ENC">
      <DA name="ctlVal" type="Enumerated"/>
      <DA name="stVal" type="Enumerated"/>
    </DOType>
    
    <DOType id="ENS_Beh" cdc="ENS">
      <DA name="stVal" type="Enumerated"/>
    </DOType>
    
    <DOType id="MV_W" cdc="MV">
      <DA name="mag" type="AnalogueValue"/>
    </DOType>
    
    <DOType id="MV_A" cdc="MV">
      <DA name="mag" type="AnalogueValue"/>
    </DOType>
    
    <DOType id="MV_V" cdc="MV">
      <DA name="mag" type="AnalogueValue"/>
    </DOType>
    
    <DOType id="MV_TotWh" cdc="MV">
      <DA name="mag" type="AnalogueValue"/>
    </DOType>
    
    <DAType id="Enumerated">
      <BDA name="val" type="INT8"/>
    </DAType>
    
    <DAType id="AnalogueValue">
      <BDA name="f" type="FLOAT32"/>
      <BDA name="i" type="INT32"/>
    </DAType>
    
    <EnumType id="BehaviourModeKind">
      <EnumVal ord="1">on</EnumVal>
      <EnumVal ord="2">blocked</EnumVal>
      <EnumVal ord="3">test</EnumVal>
      <EnumVal ord="4">test/blocked</EnumVal>
      <EnumVal ord="5">off</EnumVal>
    </EnumType>
  </DataTypeTemplates>
</SCL>
