        
---comment Read the Values blocks of the selected Devices
---@param cluster table Device Table
---@param cluster_blk integer cluster block
---@param Stname string Device Naming
function Disp_Dev(cluster, cluster_blk, Stname)
    local str = Stname.." : "
    local keys = {}
    for k in pairs(cluster[cluster_blk]) do
        table.insert(keys, k)
    end
    table.sort(keys)

    for _,k in ipairs(keys) do
        str = str..Buff_Read(cluster[cluster_blk][k])..","
    end
    print(str)
end

---comment ARS Response generate
---@param writeSt integer Write Status, 0/1/2 = Inprogress/Sucess/Fail
---@param fbSt integer Feedback Status
---@
function ARS_Resp(writeSt, fbSt)
    local d_flg = 0
    if((writeSt == 0) and (fbSt == 0)) then d_flg = 0
    elseif((writeSt == 1) and (fbSt == 0)) then d_flg = 1 
    elseif((writeSt == 2) and (fbSt == 0)) then d_flg = 2
    elseif((writeSt == 2) and (fbSt == 1)) then d_flg = 3
    elseif((writeSt == 2) and (fbSt == 2)) then d_flg = 4
    elseif((writeSt == 1) and (fbSt == 1)) then d_flg = 5
    elseif((writeSt == 1) and (fbSt == 2)) then d_flg = 6
    end 
    return(d_flg)
end

---comment Control Func for any device with Trig & spontaneous FB Structure with return the action & ARS stat
---@param cluster any Device table
---@param clusterNum integer Selected Device
---@param clusterTP integer Selected cluster Trig param
---@param clusterFB integer Selected cluster FB param
---@param val integer Write Val
---@param exp_rslt integer Expected result
---@param seq_tym integer Time Value
---@return integer 0 - Inprogress, 1 - Sucess FB, 2 - Fail FB
---@return integer ARS stat
function CntrlDev4(cluster, clusterNum, clusterTP, clusterFB, val, exp_rslt, seq_tym)  
    local d_flg, e, d = 0, 0, 0
    local sc, fa, fb, rd = "Succ ","Fail ","FB","Read"
    if STATE_NEW == 1 then
        A_Flag = CntrlDev_NoFB2(cluster, clusterNum, clusterTP, val)
        Curr_MS = millis()
        STATE_NEW = 0
        
    elseif millis() - Curr_MS < seq_tym then
        e, d = Buff_Read_Wait(cluster[clusterFB][clusterNum])
        print("Check:"..e..", "..d)
        if((e == 4) or (e == 1)) then
            if(e == 1) then
                print(sc..rd)
                if(d == exp_rslt) then d_flg = 1; print(sc..fb) 
                else d_flg = 2; print(fa..fb) 
                end
            else d_flg = 2; print(fa..rd); print(fa..fb) 
            end
            STATE_NEW = 1; print("LBI:"..cluster[clusterFB][clusterNum]..", e:"..e..", d:"..d)
        end

    elseif millis() - Curr_MS >= seq_tym then
        d_flg = 2; print(fa..rd); print(fa..fb)
        STATE_NEW = 1; print("Timeout, LBI:"..cluster[clusterFB][clusterNum]..", e:"..e..", d:"..d)
    end

    return d_flg, A_Flag
end

---comment Reading the device parameters
---@param cluster any Device table
---@param clusterNum integer Selected Device
---@param clusterFB integer Selected cluster FB param
---@return any Read value 
function Read_Val(cluster, clusterNum, clusterFB)
    return(Buff_Read(cluster[clusterFB][clusterNum]))
end

---comment Command Sequence of Device Functions with next Cmd_ID & delay
---@param Cmd_ID integer Cmd ID
---@param Nxt_CmdID integer Nxt_CmdID
---@param Seq_Dly integer Seq Delay
---@param func any DevFunction
---@param ... unknown parameters
function Cmd_Seq4(Cmd_ID, Nxt_CmdID, Seq_Dly, func, ...)
    local rs, fs = 0, 0
    if(Cmd_Cnt == Cmd_ID) then
        if(Seq_Ms == 0) then Seq_Ms = millis() end
        if(Seq_Flg == 0) then
            rs, fs = func(...)
        end
        if(rs ~= 0) then Seq_Flg = 1 end
        if((millis() - Seq_Ms >= Seq_Dly) and (Seq_Flg == 1)) then
            Cmd_Cnt = Nxt_CmdID
            Seq_Ms = 0  -- Reset the timer
            Seq_Flg = 0
        end
    end
    return rs, fs
end

---comment Device Command execution on a condition & delay
---@param Cmd_ID integer Cmd ID
---@param cmd_Cond any Condition parameter
---@param Cond_rslt any Expected result
---@param Tr_CmdID any Nxt_CmdID if True
---@param Fal_CmdID any Nxt_CmdID if False
---@param Seq_Dly integer Seq Delay
---@param func any Function
---@param ... unknown all parameters of the function
function Cmd_CondSeq4(Cmd_ID, cmd_Cond, Cond_rslt, Tr_CmdID, Fal_CmdID, Seq_Dly, func, ...)
    if(Cmd_Cnt == Cmd_ID) then
        if(cmd_Cond == Cond_rslt) then 
            print("CMID:"..Cmd_ID..", Succ, Mov-CMID:"..Tr_CmdID)
            Cmd_Seq4(Cmd_ID, Tr_CmdID, Seq_Dly, func, ...)
        else 
            Cmd_Cnt = Fal_CmdID
            print("CMID:"..Cmd_ID..", fail, Mov-CMID:"..Fal_CmdID)
        end
    end
end

---comment Command Sequence start, Setting Cmd_Cnt to 1
---@param Seq_No integer Seq No
function Cmd_Start(Seq_No)
    if(Cmd_Cnt == 0) then 
        Seq_Set = Seq_No
        Cmd_Cnt = 1
        print("Start Trig - " .. Seq_Set) 
    end
end

---comment Ending the Sequence
---@param Cmd_ID integer Cmd ID
function Cmd_End(Cmd_ID)
    if(Cmd_Cnt == Cmd_ID) then
        print("End Trig - " .. Seq_Set)
        Seq_Set = 0
        Cmd_Cnt = 0
    end
end

---@param Seq_Set integer Seq Set
---@param Md integer Mode id
function CHLR_Start(Seq_Set, Md)
    if(Md == 0) then
        print("CHLR Start Trig - " .. Seq_Set) 
        Chlr_Trig = Seq_Set
        if(Seq_Set == ON) then 
            Chlr_Md = 1 -- setting the mode
            Chlr_Cmd = 1 --Chlr_Cmd when Seq_Set is ON
        else Chlr_Md = 0 
             Chlr_Cmd = 0
        end
        ValWrt_Pt(Chlr_Md, "CMD", LBI[3])
        ValWrt_Pt( Chlr_Cmd, "TRG", LBI[4])
        Cmd_Start(1)
    elseif(Md == 1) then
        --Assign_GVar("Chlr_Md", 1)
        --CntrlDev_NoFB2(NPMP, IC_PMP, Write, ON)
        return 1,1
    elseif(Md == 2) then
        --Assign_GVar("Chlr_Md", 0)
        return 1,1
    end
end

---comment  AHU  Mode Logic
function AHU_Mode_Logic()
-------------------ON LOGIC---------------------
    if (Chlr_Trig == ON) then
        print("AC ON")

        Cmd_Seq4(1, 2, 15000, CntrlDev4, NPMP, IC_PMP,  Write,  Stat, ON, ON, FB_TYM)
        Cmd_Seq4(2, 3, 15000, CntrlDev4, NPMP, EC_PMP, Write, Stat, ON, ON, FB_TYM)
        Cmd_Seq4(3, 4, 10000, CntrlDev4, AHU, AHU_SAC1,  Write, Stat, ON, ON, FB_TYM)
        Cmd_Seq4(4, 5, 10000, CntrlDev4, AHU, AHU_SAC2, Write, Stat, ON, ON, FB_TYM)
        Cmd_Seq4(5, 6, 90000, CntrlDev4, AHU, AHU_SAC3, Write, Stat, ON, ON, FB_TYM)

        local IC_PMP_Sts, EC_PMP_Sts = Read_Val(NPMP, IC_PMP, Stat), Read_Val(NPMP, EC_PMP, Stat) 
        --print("IC_PMP St: " .. IC_PMP_Sts..", EC_PMP Status: " .. EC_PMP_Sts)

        -- Ensure both pumps are on before starting the chiller
        --Cmd_CondSeq4(6, (IC_PMP_Sts == ON and EC_PMP_Sts == ON), true, 7, 7, 5000, Cmd_Seq4, 6, 7, 5000, CntrlDev4, CMP, CHLR_COMP1, Write, Stat, ON, ON, FB_TYM)
        if(Cmd_Cnt == 6) then ARS_Stat(5) end
        if IC_PMP_Sts == ON and EC_PMP_Sts == ON then
            Cmd_Seq4(6, 7, 5000, CntrlDev4, CMP, CHLR_COMP1, Write, Stat, ON, ON, FB_TYM)
            Cmd_End(7)
        else
            print("Error: Both IC_PMP and EC_PMP must be ON before starting CHLR_COMP1")
            Cmd_End(6)
        end

-------------------OFF LOGIC-------------------------   
    elseif (Chlr_Trig == OFF) then 
        print("AC OFF")
        Cmd_Seq4(1, 2, 15000, CntrlDev4, CMP, CHLR_COMP1, Write, Stat, OFF, OFF, FB_TYM)
        Cmd_Seq4(2, 3, 15000, CntrlDev4, AHU, AHU_SAC1, Write, Stat, OFF, OFF, FB_TYM)
        Cmd_Seq4(3, 4, 15000, CntrlDev4, AHU, AHU_SAC2, Write, Stat, OFF, OFF, FB_TYM)
        Cmd_Seq4(4, 5, 15000, CntrlDev4, AHU, AHU_SAC3, Write, Stat, OFF, OFF, FB_TYM)
        Cmd_Seq4(5, 6, 15000, CntrlDev4, NPMP, IC_PMP, Write, Stat, OFF, OFF, FB_TYM)
        Cmd_Seq4(6, 7, 15000, CntrlDev4, NPMP, EC_PMP, Write, Stat, OFF, OFF, FB_TYM)
        if(Cmd_Cnt == 7) then ARS_Stat(5) end
        Cmd_End(7) 
    end
    if(Cmd_Cnt == 0) then Chlr_Trig = -1 end
end

---comment Control Func for any device without Feedback check
---@param cluster any Device table
---@param clusterNum integer Selected Device
---@param clusterTP integer Selected cluster Trig param
---@param val integer Write value
---@return integer Status
function CntrlDev_NoFB2(cluster, clusterNum, clusterTP, val)
    local d_flg = 0
    print("Selected : " .. cluster[Keys][clusterNum])
    print("LBI:"..cluster[clusterTP][clusterNum]..", Val:"..val)        
    local e = Buff_Write_Wait(cluster[clusterTP][clusterNum], val)
    print("Res: ".. e)
    if e == PKT_SUCC then 
        print("Success on Write")
        d_flg = 1
    else 
        print("Fail on Write") 
        d_flg = 2
    end
    return d_flg
end

---comment Action Command
function Act_Com()
    local Aid = Read_ActCmdID()
    local Aval = Read_ActCmdVal()
    
    print("Com_Act : "..Aid..", "..Aval)
    if(Aid >= 1 and Aid <= 10) then --If succ/fail read
        
        Insrt_ActCom2(Aid, Aval, 1, Aval, ValWrt_Pt, Aval, "TRG", LBI[4])
    
        Insrt_ActCom2(Aid, Aval, 1, 1, CntrlDev4, CMP, CHLR_COMP1, Write, Stat, ON, ON, FB_TYM)
        Insrt_ActCom2(Aid, Aval, 1, 0, CntrlDev4, CMP, CHLR_COMP1, Write, Stat, OFF, OFF, FB_TYM)

        Insrt_ActCom2(Aid, Aval, 2, 1, CntrlDev4, NPMP, IC_PMP, Write, Stat, ON, ON, FB_TYM)
        Insrt_ActCom2(Aid, Aval, 2, 0, CntrlDev4, NPMP, IC_PMP, Write, Stat, OFF, OFF, FB_TYM)

        Insrt_ActCom2(Aid, Aval, 3, 1, CntrlDev4, NPMP, EC_PMP, Write, Stat, ON, ON, FB_TYM)
        Insrt_ActCom2(Aid, Aval, 3, 0, CntrlDev4, NPMP, EC_PMP, Write, Stat, OFF, OFF, FB_TYM)

        Insrt_ActCom2(Aid, Aval, 4, 1, CntrlDev4, AHU, AHU_SAC1, Write, Stat, ON, ON, FB_TYM)
        Insrt_ActCom2(Aid, Aval, 4, 0, CntrlDev4, AHU, AHU_SAC1, Write, Stat, OFF, OFF, FB_TYM)

        Insrt_ActCom2(Aid, Aval, 5, 1, CntrlDev4, AHU, AHU_SAC2, Write, Stat, ON, ON, FB_TYM)
        Insrt_ActCom2(Aid, Aval, 5, 0, CntrlDev4, AHU, AHU_SAC2, Write, Stat, OFF, OFF, FB_TYM)

        Insrt_ActCom2(Aid, Aval, 6, 1, CntrlDev4, AHU, AHU_SAC3, Write, Stat, ON, ON, FB_TYM)
        Insrt_ActCom2(Aid, Aval, 6, 0, CntrlDev4, AHU, AHU_SAC3, Write, Stat, OFF, OFF, FB_TYM)
        
        Insrt_ActCom2(Aid, Aval, 7, Aval, ValWrt_Pt, Aval, "STP", LBI[1])

        Insrt_ActCom2(Aid, Aval, 8, 1, CHLR_Start, ON, 0)
        Insrt_ActCom2(Aid, Aval, 8, 0, CHLR_Start, OFF, 0)

        Insrt_ActCom2(Aid, Aval, 9, Aval, ValWrt_Pt, Aval, "DLT", LBI[2])

        Insrt_ActCom2(Aid, Aval, 10, 1, CHLR_Start, 0, 1)
        Insrt_ActCom2(Aid, Aval, 10, 0, CHLR_Start, 0, 2)

    elseif (Aid ~= 0) then ARS_Stat(7)
    end
end

---comment Insert Action_Cmd
---@param AI integer Act id
---@param AVAL integer Act val
---@param AI_rslt integer Act id exp
---@param AVAL_rslt integer Act val exp
---@param func any DevFunction
---@param ... unknown parameters
function Insrt_ActCom2(AI, AVAL, AI_rslt, AVAL_rslt, func, ...)
    if((AI == AI_rslt)and(AVAL == AVAL_rslt)) then
        local rs, fs = func(...)
        if(rs ~= 0) then
            ActCMD_Reset()
            local AR_st = ARS_Resp(rs, fs)
            print("Ars : "..AR_st)
            ARS_Stat(AR_st)
        end
    end
end

---comment Mapping Ranges ActCommand
---@param AI integer Act id
---@param AVAL integer Act val
---@param AI_rslt1 integer Act id exp1
---@param AI_rslt2 integer Act id exp2
---@param AVAL_rslt integer Act val exp
---@param func any DevFunction
---@param cluster any Device table
---@param clusterNum1 integer Selected Start Device
---@param clusterNum2 integer Selected end Device 
---@param ... unknown
function Map_ActCom(AI, AVAL, AI_rslt1, AI_rslt2, AVAL_rslt, func, cluster, clusterNum1, clusterNum2, ...)
    local aI1, dV1 = AI_rslt1, clusterNum1
    while(aI1 <= AI_rslt2) do
        Insrt_ActCom2(AI, AVAL, aI1, AVAL_rslt, func, cluster, dV1, ...)
        aI1, dV1 = aI1 + 1, dV1 + 1
    end
end

---comment AHU Triggering func
---@param Seq_No integer Seq_No
---@param Mode integer Mode
function CHLR_Trig(Seq_No, Mode)
    Cmd_Start(Seq_No)
    SN_AMSW2 = Mode
    --print("CheckX")
end

---comment Value write point
---@param stp integer Setpoint
---@param nstr string NVS string
---@param lbi integer LBI variable to input
function ValWrt_Pt(stp, nstr, lbi)
    Buff_Write_NoWait(lbi, stp)
    NVS_WriteInt(nstr, stp)
    return 1,1
end

---comment Read from NVS to LBI
---@param nstr string NVS string
---@param lbi integer LBI variable to input
function NVS_Read(nstr, lbi)
    local stpt = NVS_GetVal(nstr)
   Buff_Write_NoWait(lbi, stpt)
end

---comment Execution only once
---@param seq integer Sequence no
---@param seg integer Segment in sequence
---@param cond boolean condition 
---@return boolean true = one time & cond true
function Once(seq, seg, cond)
    if(seg==0) then ONC[seq]=0  -- reset
    else
        if((cond==true)and(ONC[seq]~=seg)) then
            ONC[seq]=seg
            return(true)
        end
    end
    return(false)
end

---comment Do in every interval
---@param seq integer sequence
---@param sq_dly integer seq delay
---@return boolean true = Succ, false = fail 
function DoEvery(seq, sq_dly)
    if(DOEV[seq] == 0) then DOEV[seq] = millis() end
    if(millis() - DOEV[seq] >= sq_dly) then
        DOEV[seq] = millis()
        return(true) 
    end
    return(false)
end

---comment Compressor Logic
function Comp_Logic()
    local IC_PMP_Sts, EC_PMP_Sts = Read_Val(NPMP, IC_PMP, Stat), Read_Val(NPMP, EC_PMP, Stat)
    local SAC1_Sts, SAC2_Sts, SAC3_Sts = Read_Val(AHU, AHU_SAC1, Stat), Read_Val(AHU, AHU_SAC2, Stat), Read_Val(AHU, AHU_SAC3, Stat) 
    local CMP_Sts = Read_Val(CMP, CHLR_COMP1, Stat)

    print("COMP Logic Exec")
    if((Chlr_Md == 1) and (IC_PMP_Sts == ON) and (EC_PMP_Sts == ON) and ((SAC1_Sts == ON) or (SAC2_Sts == ON) or (SAC3_Sts == ON))) then
        print("Plant Logic")
        Temp_Logic()
    elseif((Chlr_Md == 2) and (IC_PMP_Sts == ON)) then
        print("Pre-Cool Logic")
        Temp_Logic()
    else
        print("No Logic Found")
    end

    --Trip check
    if((Chlr_Md == 1) and (CMP_Sts == ON) and (IC_PMP_Sts == OFF)) then
        print("CMP Stopped at PMP Trip")
        CntrlDev_NoFB2(CMP, CHLR_COMP1, Write, OFF)
    end
end

---comment Comp Temp Logic
function Temp_Logic()
    local CMP_Sts = Read_Val(CMP, CHLR_COMP1, Stat)
    
    if((Tank_Temp >= (ST_PT + Dlt_PT)) and (CMP_Sts == OFF)) then
        print("COM Trig ON")
        CntrlDev_NoFB2(CMP, CHLR_COMP1, Write, ON)
    elseif((Tank_Temp <= ST_PT) and (CMP_Sts == ON)) then
        print("COM Trig OFF")
        CntrlDev_NoFB2(CMP, CHLR_COMP1, Write, OFF)
    else
        print("COM-Not Set")
    end
end

---comment Assign global var
---@param Gvar string Global variable
---@param val any Assign value
function Assign_GVar(Gvar, val)
    _G[Gvar] = val
    print("Assigning "..Gvar.." :".._G[Gvar])
    return 1,1
end