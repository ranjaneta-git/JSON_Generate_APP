# Example6_21params - Quick Reference Card

**Print this page and keep it next to you while adding parameters!**

---

## 📋 All 21 Parameters at a Glance

| # | Slave | FC | Addr | Fmt | Mult | Access | Cloud | JSON Group | JSON Unit | JSON Key | Array | Paired | Lua Cat | LBI |
|---|-------|----|----- |-----|------|--------|-------|------------|-----------|----------|-------|--------|---------|-----|
| 1 | 1 | 1 | 0 | 3 | 1 | R | No | - | - | - | - | 7 | User Var | 1 |
| 2 | 1 | 1 | 1 | 3 | 1 | R | No | - | - | - | - | 8 | User Var | 2 |
| 3 | 1 | 1 | 2 | 3 | 1 | R | No | - | - | - | - | 9 | User Var | 3 |
| 4 | 1 | 1 | 3 | 3 | 1 | R | No | - | - | - | - | 10 | User Var | 4 |
| 5 | 1 | 1 | 4 | 3 | 1 | R | No | - | - | - | - | 11 | N/A | Auto |
| 6 | 1 | 1 | 5 | 3 | 1 | R | No | - | - | - | - | 12 | N/A | Auto |
| 7 | 1 | 5 | 0 | 3 | 1 | W | No | - | - | - | P2.MPI | - | Equipment | 5 |
| 8 | 1 | 5 | 1 | 3 | 1 | W | No | - | - | - | P2.MPI | - | Equipment | 7 |
| 9 | 1 | 5 | 2 | 3 | 1 | W | No | - | - | - | P2.MPI | - | Equipment | 9 |
| 10 | 1 | 5 | 3 | 3 | 1 | W | No | - | - | - | P2.MPI | - | Equipment | 11 |
| 11 | 1 | 5 | 4 | 3 | 1 | W | No | - | - | - | P2.MPI | - | Equipment | 13 |
| 12 | 1 | 5 | 5 | 3 | 1 | W | No | - | - | - | P2.MPI | - | Equipment | 15 |
| 13 | 3 | 1 | 1 | 3 | 1 | R | Yes | CH1_DIE1 | St | Cr1 | P2,P3 | - | Equipment | 6 |
| 14 | 3 | 1 | 2 | 3 | 1 | R | Yes | CH1_DIE2 | St | PP | P2,P3 | - | Equipment | 8 |
| 15 | 3 | 1 | 3 | 3 | 1 | R | Yes | CH1_DIE2 | St | SP | P2,P3 | - | Equipment | 10 |
| 16 | 3 | 1 | 4 | 3 | 1 | R | Yes | CH1_DIE4 | Sw | AM1 | P2,P3 | - | Equipment | 18 |
| 17 | 3 | 1 | 5 | 3 | 1 | R | Yes | CH1_AIE2 | AI | Spt | P2,P3 | - | Equipment | 12 |
| 18 | 3 | 1 | 6 | 3 | 1 | R | Yes | CH1_AIE2 | AI | DltPt | P2,P3 | - | Equipment | 14 |
| 19 | 3 | 1 | 7 | 3 | 1 | R | Yes | CH1_DIE5 | Sw | CH1_Mode | P2,P3 | - | Equipment | 16 |
| 20 | 3 | 1 | 8 | 3 | 1 | R | Yes | CH1_DIE6 | Sw | CH1_Cmd | P2,P3 | - | Equipment | 19 |
| 21 | 2 | 3 | 1561 | 3 | 0.1 | R | Yes | CH1_AIE1 | DegC | Tank_T | P2,P3 | - | Equipment | 17 |

---

## 🎯 Parameter Groups

### **Group 1: Feedback (1-6)**
- All on **Slave 1, FC 1**
- Pattern: Address 0-5 → Paired with 7-12
- **First 4** use Lua Buffer (LBI 1-4, User Variable)
- **Last 2** skip Lua Buffer (LBI Auto, N/A)

### **Group 2: Write (7-12)**
- All on **Slave 1, FC 5**
- Pattern: Address 0-5
- All have **Array: P2.MPI**, **Lua: Equipment**
- LBI: 5, 7, 9, 11, 13, 15 (odd after 5)

### **Group 3: Read-Only Cloud (13-21)**
- **13-20:** Slave 3, FC 1, Address 1-8
- **21:** Slave 2, FC 3, Address 1561, Multiplier 0.1
- All have **Cloud=Yes**, **Array: P2.MPI,P3.MPI**
- All use **Lua: Equipment**

---

## ⚡ Speed Entry Tips

**For Parameters 1-4 (Feedback with Lua):**
```
Copy-paste values, only change:
- Address: 0→1→2→3
- Paired: 7→8→9→10
- LBI: 1→2→3→4
```

**For Parameters 5-6 (Feedback without Lua):**
```
Copy-paste #4, then change:
- Address: 4→5
- Paired: 11→12
- Lua Buffer: Yes→No
- Lua Category: User Variable→N/A
- LBI: 4→Auto
```

**For Parameters 7-12 (Write):**
```
Copy-paste, only change:
- FC: 1→5
- Address: 0→1→2→3→4→5
- Access: R→W
- Array: (empty)→P2.MPI
- Paired: 7-12→(empty)
- Lua Category: User Variable→Equipment
- LBI: 5,7,9,11,13,15
```

**For Parameters 13-20 (Cloud on Slave 3):**
```
Copy-paste, change:
- Slave: 1→3
- Address: 1→2→3→4→5→6→7→8
- Cloud: No→Yes
- Fill JSON fields (see table)
- Array: P2.MPI→P2.MPI,P3.MPI
- Paired: (remove)
- LBI: 6,8,10,12,14,16,18,19
```

---

## 📝 Field Explanations

**Array Membership Shorthand:**
- `P2` = `P2.MPI`
- `P3` = `P3.MPI`
- `P2,P3` = `P2.MPI,P3.MPI`

**Lua Category:**
- `User Var` = `User Variable`
- `N/A` = Not in Lua Buffer

**Function Codes:**
- `1` = Read Coils
- `3` = Read Holding Registers
- `5` = Write Single Coil

**Format:**
- `3` = INT16 (2 bytes, 1 register)

---

## ✅ Verification Targets

After adding all 21 parameters, you should see:

**P3.MPI (Cloud Output):** 9 parameters
```json
[13, 14, 15, 17, 18, 19, 21, 16, 20]
```

**P2.MPI (Equipment Commands):** 15 parameters
```json
[7, 13, 8, 14, 9, 15, 10, 17, 11, 18, 12, 19, 21, 16, 20]
```

**P2.LBI (Lua Buffer):** 19 positions
```json
[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19]
```

**JKA Equipment Groups:** 8 groups
```
CH1_DIE1, CH1_DIE2, CH1_DIE4, CH1_AIE1, CH1_AIE2, CH1_DIE5, CH1_DIE6
```

---

## � After Entry: Calculate Packets (v6.6+)

**New Step:** After adding all 21 parameters, click **🔄 Calculate Packets**

**What it does:**
- Automatically assigns Packet #, Packet Start (SA), Packet Regs (NRT)
- Groups by Slave ID and Function Code
- Enforces firmware constraints (70 registers, 70 address span)

**Expected Results for Example6:**
- **Packet 1:** Slave 1, FC 1 - 6 feedback params (SA=0, NRT=6)
- **Packet 2:** Slave 1, FC 5 - 6 write params (SA=0, NRT=6)
- **Packet 3:** Slave 2, FC 3 - 1 param (SA=1561, NRT=1)
- **Packet 4:** Slave 3, FC 1 - 8 params (SA=1, NRT=8)

**Manual Override:** You can edit these fields manually if needed

---

## �🚨 Common Errors to Avoid

1. ❌ Setting Cloud=Yes on Write parameters (7-12)
2. ❌ Forgetting Array Membership on Write (must be P2.MPI)
3. ❌ Wrong LBI sequence (check table carefully)
4. ❌ Wrong Lua Category on Write (must be Equipment, not User Variable)
5. ❌ Missing JSON fields when Cloud=Yes (params 13-21)
6. ❌ Wrong pairing (1↔7, 2↔8, 3↔9, 4↔10, 5↔11, 6↔12)

---

**Print this card and follow the table row-by-row!**

*Time to complete: ~15 minutes*  
*Difficulty: ⭐ Beginner*
