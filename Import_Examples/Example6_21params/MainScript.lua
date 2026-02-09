-- Devices 
-- Usr Inp
CHLR_COMP1 = 1 IC_PMP = 2 EC_PMP = 3 AHU_SAC1 = 4
AHU_SAC2 = 5 AHU_SAC3 = 6 SN_TNKTP = 7  SN_AMSW1 = 8  SN_AMSW2 = 9 

--End Usr Inp

-- Device structure
Write = 1 Stat = 2 Keys = 3
Set1 = 4 Set2 = 5 ALARM = 6 Freq = 7 Stat2 = 8

-- VFD Action Command
--VFD_RUN_OFF = 4 VFD_RUN_ON = 1 NO_FAULT = 0 VFD_ON_REV = 2
--SET1_CMD = 2  SET2_CMD = 4

-- Types of values
NO_DATA = -1 OFF = 0 ON = 1 -- RPC buffer values
PKT_SUCC = 1 PKT_VRFAIL = 3 PKT_FAIL = 4 -- Modbus write status

--Device tables & LBI inputs
-- Usr Inp --

CMP = {}
CMP[Write] = {[CHLR_COMP1] = 1}
CMP[Stat] = {[CHLR_COMP1] = 2}
CMP[Keys] = {[CHLR_COMP1] = "COMP 1"}

NPMP = {}
NPMP[Write] = {[IC_PMP] = 3, [EC_PMP] = 5}
NPMP[Stat] = {[IC_PMP] = 4, [EC_PMP] = 6}
NPMP[Keys] = {[IC_PMP] = "IC PUMP", [EC_PMP] = "EC PUMP"}

AHU = {}
AHU[Write] = {[AHU_SAC1] = 7, [AHU_SAC2] = 9, [AHU_SAC3] = 11 }
AHU[Stat] = {[AHU_SAC1] = 8, [AHU_SAC2] = 10, [AHU_SAC3] = 12}
AHU[Keys] = {[AHU_SAC1] = "SAC1", [AHU_SAC2] = "SAC2",  [AHU_SAC3] = "SAC3"}

SEN = {}
SEN[Stat] = {[SN_TNKTP] = 13, [SN_AMSW1] = 14, [SN_AMSW2] = 15}
SEN[Keys] = {[SN_TNKTP] = "TNK Temp", [SN_AMSW1] = "AM Switch1", [SN_AMSW2] = "AM Switch2"}

LBI = {[1] = 16, [2] = 17, [3] = 18, [4] = 19}

FB_TYM = 5000 -- FB Delay time
-- End Usr Inp --

-- CntrlDev4
STATE_NEW = 1
Curr_MS = 0
A_Flag = 0

-- Command Seq Var
Cmd_Cnt = 0
Seq_Set = 0
Seq_Ms = 0
Seq_Flg = 0

--Once, DoEvery func bar
ONC = {0}
DOEV = {0, 0}

--User Variables
ST_PT = 0 -- Setpoint
Tank_Temp = 0
Chlr_Trig = -1
Dlt_PT = 0
Chlr_Md = 0 -- 0 - No Mode, 1 - Normal Mode, 2 - Pre-cool Mode
Chlr_Cmd = 0

-- Initializations of equipment
do
    delay(5000)

    NVS_Read("STP", LBI[1])
    NVS_Read("DLT", LBI[2])
    NVS_Read("CMD", LBI[3])
    NVS_Read("TRG", LBI[4])


   -- delay(15000)
end

-- Main while loop
while true do
    print("Script version: From computer-1")

    Act_Com()

    ST_PT = Buff_Read(LBI[1])
    Dlt_PT = Buff_Read(LBI[2])
    Chlr_Md = Buff_Read(LBI[3])
    Chlr_Cmd = Buff_Read(LBI[4])
    Tank_Temp = Read_Val(SEN, SN_TNKTP, Stat)

    if DoEvery(2, 2000) then
        Disp_Dev(CMP, Stat, "COMP")
        Disp_Dev(NPMP, Stat, "PUMP")
        Disp_Dev(AHU, Stat, "AC")
        Disp_Dev(SEN, Stat, "VAL")
        print("Set Point: "..ST_PT..", Dlt_PT: "..Dlt_PT)
        print("Read Sen: "..Tank_Temp..", CH_Mode: "..Chlr_Md)
        print("CH_Cmd: "..(Chlr_Cmd or "nil"))

    end

    AHU_Mode_Logic()

    if DoEvery(1, 15000) then
        Comp_Logic()
    end

    if Script_Restart() then break end

    Grb_collect()

    delay(1000)
end