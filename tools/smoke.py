# Smoke test: loads MageHelper (TOC order, incl. embedded Ace3) in Lua 5.1 against tools/wowstub.lua,
# once as deDE and once as enUS client, and runs scenarios with check() assertions.
# Usage (from the addon folder, with lupa installed):
#   python -I tools/smoke.py [-v]
import os, re, sys
from lupa import lua51

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
STUB = open(os.path.join(HERE, "wowstub.lua"), encoding="utf-8").read()


def toc_files():
    """Files in load order: TOC entries, XML <Script>/<Include> expanded recursively."""
    version, files = "?", []
    def add(rel, base):
        p = os.path.normpath(os.path.join(base, rel.replace("\\", "/")))
        if p.lower().endswith(".xml"):
            xml = open(p, encoding="utf-8").read()
            xml = re.sub(r"<!--.*?-->", "", xml, flags=re.S)
            for m in re.finditer(r'<(Script|Include)\s+file="([^"]+)"', xml):
                add(m.group(2), os.path.dirname(p))
        else:
            files.append(p)
    for line in open(os.path.join(ROOT, "MageHelper.toc"), encoding="utf-8"):
        line = line.strip()
        if line.startswith("## Version:"): version = line.split(":", 1)[1].strip()
        elif line and not line.startswith("#"): add(line, ROOT)
    return version, files


# Old (<= 2.3) flat per-character settings, as the update leaves them in the character's file.
LEGACY = r'''
return { shown = true, combustionLB = 7, x = 50, y = -100, focusMagicTarget = "Anya",
         moltenT9Legs = "Meine T9", moltenMainLegs = "Meine T10", moltenStep = 2, iceBlockLead = 1.5,
         analyzer = { bossFights = { { name = "Lord Mark'gar", duration = 100 } }, deathRecaps = {} } }
'''

COMMON = r'''
MH = LibStub("AceAddon-3.0"):GetAddon("MageHelper")
function check(cond, msg) if not cond then error("CHECK FAILED: " .. msg, 2) end end
function Slash(cmd) SlashCmdList.ACECONSOLE_MH(cmd) end
'''

# Legacy settings were taken over (variant: MageHelperLegacyDB for deDE, flat MageHelperDB for enUS).
MIGRATION = r'''
local p, c = MH.db.profile, MH.db.char
check(MageHelperLegacyDB == nil, "legacy table dropped")
check(MageHelperDB.profiles ~= nil, "MageHelperDB is an AceDB database")
check(p.combustionLB == 7 and p.x == 50 and p.iceBlockLead == 1.5, "profile settings taken over")
check(c.focusMagicTarget == "Anya" and c.focusMagicPartner == "Anya", "FM target taken over and used as partner")
check(c.moltenT9Legs == nil and c.moltenStep == nil and p.moltenT9Legs == nil, "old leg-name settings are dropped")
check(type(c.moltenSwap) == "table" and p.moltenT9 == true, "T9 swap defaults")
check(c.analyzer.bossFights[1].name == "Lord Mark'gar", "analyzer data per character")
check(MH.db:GetCurrentProfile() == "Kahuchan - Rising-Gods", "own profile per character: " .. MH.db:GetCurrentProfile())
OUT[#OUT + 1] = "MIGRATION OK"
'''

SCRIPT = r'''
local function upd(n) for i = 1, (n or 3) do Tick(0.15) end end
upd()
INCOMBAT = true
FireEvent("PLAYER_REGEN_DISABLED"); upd()
AURAS.player = { {"Hot Streak", 0, nil, 48108} }; upd()
-- 3.3.5 layout: timestamp, event, sourceGUID, sourceName, sourceFlags, destGUID, destName, destFlags, ...
FireEvent("COMBAT_LOG_EVENT_UNFILTERED", 0, "SPELL_CAST_SUCCESS", "GUID-player", "Kahuchan", 0x511, "GUID-target", "Dummy", 0xa48, 42833, GetSpellInfo(42833), 4)
FireEvent("COMBAT_LOG_EVENT_UNFILTERED", 0, "SPELL_DAMAGE", "GUID-target", "Dummy", 0xa48, "GUID-player", "Kahuchan", 0x511, 1, "Hit", 1, 500, 0)
FireEvent("COMBAT_LOG_EVENT_UNFILTERED", 0, "SWING_DAMAGE", "GUID-target", "Dummy", 0xa48, "GUID-player", "Kahuchan", 0x511, 300, 0)
FireEvent("UNIT_SPELLCAST_SUCCEEDED", "player", GetSpellInfo(11129)); AURAS.player = {}; upd()
AURAS.player = { {GetSpellInfo(66), 0, nil, 32612} }; upd(); AURAS.player = {}
upd(200)
INCOMBAT = false
FireEvent("PLAYER_REGEN_ENABLED")
FireEvent("PLAYER_DEAD")
for _, cmd in ipairs({"", "help", "lock", "unlock", "buffs lock", "comb 9", "skips off", "skips on", "utility off", "icelead 1.5", "icecancel off", "buffet 4", "instability 6", "debug", "debug on", "debug off", "analyse start", "analyse stop", "analyse a", "analyse b", "analyse compare", "analyse boss", "analyse death", "report", "autoreport off", "gloves off", "gloves on", "fm Partner", "fm clear", "fm", "molten", "molten reset", "lang", "analyse", "config"}) do
  Slash(cmd)
end
check(OPTIONS_OPENED ~= nil, "/mh config opens the options panel")
for _, n in ipairs({"MageHelperOneButton", "MageHelperMinimapButton", "MageHelperBuffMinimapButton", "MageHelperAnalyzerMinimapButton", "MageHelperBuff_FMSet", "MageHelperBuff_armor", "MageHelperBuff_brilliance", "MageHelperBuff_fmin", "MageHelperBuff_fmout", "MageHelperBuff_flask", "MageHelperBuff_wild"}) do
  local f = FRAMES[n]; if f and f.__scripts.OnEnter then f.__scripts.OnEnter(f) end
end
FRAMES.MageHelperOneButton.__scripts.OnClick(FRAMES.MageHelperOneButton)
FRAMES.MageHelperAnalyzerMinimapButton.__scripts.OnClick(FRAMES.MageHelperAnalyzerMinimapButton, "RightButton")
upd()
check(MH.db.profile.combustionLB == 9, "slash commands write into the profile")
'''

# Combat log in the 3.3.5 layout (no hideCaster, no raid flags):
#   timestamp, event, sourceGUID, sourceName, sourceFlags, destGUID, destName, destFlags, <event params>
COMBATLOG = r'''
local KR = MageHelperFrame
local function CL(...) FireEvent("COMBAT_LOG_EVENT_UNFILTERED", 0, ...) end
local ME, BOSS, OTHER = "GUID-player", "GUID-boss", "GUID-Anya"
local MEF, BOSSF, OTHERF = 0x511, 0xa48, 0x514
local FB, PYRO, LB, CS = GetSpellInfo(42833), GetSpellInfo(42891), GetSpellInfo(55360), GetSpellInfo(2139)
local BLIGHT = GetSpellInfo(69195)
INCOMBAT = true
FireEvent("PLAYER_REGEN_DISABLED"); Tick(0.15)
Slash("analyse start")
-- own casts: three max-rank Fireballs, one lower rank; another mage's Fireball must not count
for i = 1, 3 do CL("SPELL_CAST_SUCCESS", ME, "Kahuchan", MEF, BOSS, "Boss", BOSSF, 42833, FB, 4) end
CL("SPELL_CAST_SUCCESS", ME, "Kahuchan", MEF, BOSS, "Boss", BOSSF, 42832, FB, 4)
CL("SPELL_CAST_SUCCESS", OTHER, "Anya", OTHERF, BOSS, "Boss", BOSSF, 42833, FB, 4)
CL("SPELL_CAST_SUCCESS", ME, "Kahuchan", MEF, BOSS, "Boss", BOSSF, 42891, PYRO, 4)
CL("SPELL_CAST_SUCCESS", OTHER, "Anya", OTHERF, BOSS, "Boss", BOSSF, 42891, PYRO, 4)
CL("SPELL_CAST_SUCCESS", ME, "Kahuchan", MEF, BOSS, "Boss", BOSSF, 55360, LB, 4)
-- matching is by ID: a Fireball rank with an unexpected name still counts, a triggered spell that only
-- shares the name (Living Bomb explosion 55362) does not
CL("SPELL_CAST_SUCCESS", ME, "Kahuchan", MEF, BOSS, "Boss", BOSSF, 42832, "Some Other Name", 4)
CL("SPELL_CAST_SUCCESS", ME, "Kahuchan", MEF, BOSS, "Boss", BOSSF, 55362, LB, 4)
-- own damage: spell hit, LB tick, LB explosion; other player's damage is ignored
CL("SPELL_DAMAGE", ME, "Kahuchan", MEF, BOSS, "Boss", BOSSF, 42833, FB, 4, 1000, 0, 4, 0, 0, 0, nil, nil, nil)
CL("SPELL_PERIODIC_DAMAGE", ME, "Kahuchan", MEF, BOSS, "Boss", BOSSF, 55360, "Other Name", 4, 200, 0, 4, 0, 0, 0, nil, nil, nil)
CL("SPELL_DAMAGE", ME, "Kahuchan", MEF, BOSS, "Boss", BOSSF, 55362, LB, 4, 30, 0, 4, 0, 0, 0, nil, nil, nil)
CL("SPELL_DAMAGE", OTHER, "Anya", OTHERF, BOSS, "Boss", BOSSF, 42833, FB, 4, 99999, 0, 4, 0, 0, 0, nil, nil, nil)
CL("SPELL_PERIODIC_DAMAGE", OTHER, "Anya", OTHERF, BOSS, "Boss", BOSSF, 55360, LB, 4, 99999, 0, 4, 0, 0, 0, nil, nil, nil)
-- interrupts: mine counts, another player's does not; Counterspell cast is counted
CL("SPELL_CAST_SUCCESS", ME, "Kahuchan", MEF, BOSS, "Boss", BOSSF, 2139, CS, 64)
CL("SPELL_INTERRUPT", ME, "Kahuchan", MEF, BOSS, "Boss", BOSSF, 2139, CS, 64, 69397, "Frostbolt", 16)
CL("SPELL_INTERRUPT", OTHER, "Anya", OTHERF, BOSS, "Boss", BOSSF, 2139, CS, 64, 69397, "Frostbolt", 16)
-- incoming: boss spell and melee on me; boss hits on another player are not mine
CL("SPELL_DAMAGE", BOSS, "Boss", BOSSF, ME, "Kahuchan", MEF, 69195, BLIGHT, 32, 7000, 0, 32, 0, 0, 0, nil, nil, nil)
CL("SWING_DAMAGE", BOSS, "Boss", BOSSF, ME, "Kahuchan", MEF, 3000, 250, 1, 0, 0, 0, nil, nil, nil)
CL("SPELL_DAMAGE", BOSS, "Boss", BOSSF, OTHER, "Anya", OTHERF, 69195, BLIGHT, 32, 88888, 0, 32, 0, 0, 0, nil, nil, nil)
CL("SWING_DAMAGE", BOSS, "Boss", BOSSF, OTHER, "Anya", OTHERF, 77777, 0, 1, 0, 0, 0, nil, nil, nil)
Tick(0.15); Tick(0.15)

local fbpm = tonumber(KR.info.__text:match("FB/min: |c%x%x%x%x%x%x%x%x(%d+)"))
check(fbpm == 5, "FB/min counts own Fireballs (all ranks, by ID), got " .. tostring(fbpm) .. " in " .. KR.info.__text)
local before = #OUT
Slash("report")
local fbs, pyros, lbs
for i = before + 1, #OUT do
  local a, b = OUT[i]:match(": (%d+)%s+Pyros: (%d+)$"); if a then fbs, pyros = tonumber(a), tonumber(b) end
  local c = OUT[i]:match("^LB[%- ]%a+: (%d+)"); if c then lbs = tonumber(c) end
end
check(fbs == 5 and pyros == 1 and lbs == 1, string.format("fight report counts own casts: FB %s Pyro %s LB %s", tostring(fbs), tostring(pyros), tostring(lbs)))

Slash("analyse stop")
local r = MH.db.char.analyzer.lastTraining
check(r and r.damageDone == 1230, "analyzer damage = own SPELL_DAMAGE + SPELL_PERIODIC_DAMAGE, got " .. tostring(r and r.damageDone))
check(r.lbTicks == 1 and r.pyroCasts == 1 and r.lbApplications == 1, "analyzer LB ticks / Pyro / LB casts")
check(r.interrupts == 1 and r.counterspellUses == 1, "own interrupt counted once, got " .. tostring(r.interrupts))
check(r.damageTaken == 10000 and r.incomingDamage == 10000, "damage taken only from hits on me, got " .. tostring(r.damageTaken))

FireEvent("PLAYER_DEAD")
local hits = MH.db.char.analyzer.deathRecaps[1].hits
local blight, melee, foreign = false, false, false
for _, h in ipairs(hits) do
  if h.source == "Boss" and h.spell == BLIGHT and h.amount == 7000 then blight = true end
  if h.source == "Boss" and h.amount == 3000 and h.overkill == 250 then melee = true end
  if h.amount == 88888 or h.amount == 77777 or h.source == "Kahuchan" then foreign = true end
end
check(blight and melee, "death recap shows the boss spell and melee hit on me")
check(not foreign, "death recap ignores hits on others and my own damage")
before = #OUT
Slash("analyse death")
local shown = table.concat(OUT, "\n", before + 1)
check(shown:find(BLIGHT, 1, true) and shown:find("7000", 1, true) and shown:find("3000", 1, true), "death recap printout lists the hits")
INCOMBAT = false
FireEvent("PLAYER_REGEN_ENABLED")
OUT[#OUT + 1] = "COMBATLOG OK"
'''

# Options window (AceConfig validates the table) and profile switching.
OPTIONS = r'''
-- With a uiType, AceConfigRegistry validates the table and errors on a malformed option.
local o = LibStub("AceConfigRegistry-3.0"):GetOptionsTable("MageHelper", "dialog", "MyLib-1.0")
check(type(o) == "table", "options table registered and valid")
local KR = MageHelperFrame
o.args.rotation.set({ "rotation", "combustionLB" }, 8)
check(MH.db.profile.combustionLB == 8, "range option writes profile")
o.args.general.args.shown.set({ "general", "shown" }, false)
check(not KR.__shown and MH.db.profile.shown == false, "hide bar via options")
o.args.general.args.shown.set({ "general", "shown" }, true)
check(KR.__shown, "show bar via options")
o.args.rotation.args.useGloves.set({ "rotation", "useGloves" }, false)
check(not FRAMES.MageHelperButton_fireball.__attr.macrotext:find("/use 10", 1, true), "gloves off rebuilds macros")
o.args.rotation.args.useGloves.set({ "rotation", "useGloves" }, true)
check(FRAMES.MageHelperButton_fireball.__attr.macrotext:find("/use 10", 1, true), "gloves on rebuilds macros")
o.args.focusMagic.args.partner.set({ "focusMagic", "partner" }, " Anya ")
check(MH.db.char.focusMagicPartner == "Anya", "FM partner via options")
check(type(o.args.focusMagic.args.status.name()) == "string", "FM status text")
check(o.args.profiles ~= nil, "profiles page")

local own = MH.db:GetCurrentProfile()
MH.db:SetProfile("Raid")
check(MH.db.profile.combustionLB == 10, "new profile starts with defaults")
Slash("comb 4")
check(MH.db.profile.combustionLB == 4 and MH.db.profiles[own].combustionLB == 8, "addon follows the active profile")
MH.db:SetProfile(own)
check(MH.db.profile.combustionLB == 8, "back to own profile")
MH.db:CopyProfile("Raid")
check(MH.db.profile.combustionLB == 4, "copy profile")
check(MH.db.char.focusMagicPartner == "Anya", "character data unaffected by profiles")
OUT[#OUT + 1] = "OPTIONS OK"
'''

# Focus Magic picker: raid of 8, inspect, filters, target/partner/back, change in combat.
PICKER = r'''
RAID = {
  { name = "Kahuchan", class = "MAGE" },
  { name = "Anya", class = "MAGE" },
  { name = "Bheal", class = "PRIEST", talents = { 5, 51, 15 } },     -- holy
  { name = "Cshadow", class = "PRIEST", talents = { 13, 0, 58 } },   -- shadow
  { name = "Dresto", class = "DRUID", talents = { 0, 15, 56 } },     -- resto, already has FM from Anya
  { name = "Ehpala", class = "PALADIN", talents = { 51, 5, 15 }, range = false }, -- holy but out of range
  { name = "Fwar", class = "WARRIOR" },
  { name = "Gsham", class = "SHAMAN", talents = { 0, 0, 57 }, online = false },
}
AURAS.raid5 = { { "Focus Magic", 0, nil, 54646, "raid2" } }
INCOMBAT = false
if FRAMES.MageHelperFMPicker then FRAMES.MageHelperFMPicker:Hide() end -- the main scenario may have opened it
Slash("fm")
local P = FRAMES.MageHelperFMPicker
check(P and P.__shown, "picker opens with /mh fm")
for i = 1, 40 do
  Tick(0.4)
  if INSPECT_PENDING then INSPECT_PENDING = false; FireEvent("INSPECT_TALENT_READY") end
end
local function rows()
  local t = {}
  for _, r in ipairs(P.rows) do if r.__shown then t[#t + 1] = r.name.__text .. " [" .. r.info.__text .. "]" end end
  return t
end
local function dump(label) OUT[#OUT + 1] = "ROWS " .. label .. ": " .. table.concat(rows(), " | ") end
local function shownNames() local t = {}; for _, r in ipairs(P.rows) do if r.__shown then t[#t + 1] = r.name.__text end end; return table.concat(t, ",") end
dump("all")
check(shownNames() == "Anya,Bheal,Cshadow,Dresto,Ehpala,Fwar,Gsham", "all members except me, alphabetical: " .. shownNames())
-- healing classes that are online and in range: Bheal, Cshadow, Dresto
check(INSPECT_COUNT == 3, "inspected healing classes in range, got " .. INSPECT_COUNT)

local function setFilter(name, on)
  local cb = FRAMES[name]; cb:SetChecked(on); cb.__scripts.OnClick(cb)
end
setFilter("MageHelperFMFilterHealers", true); dump("healers")
-- Bheal healer; Ehpala/Gsham unknown (shown as Healer?); Cshadow is shadow; Dresto already has FM
check(shownNames() == "Bheal,Ehpala,Gsham", "healers without FM: " .. shownNames())
setFilter("MageHelperFMFilterHealers", false); setFilter("MageHelperFMFilterMages", true); dump("mages")
check(shownNames() == "Anya", "only mages: " .. shownNames())
setFilter("MageHelperFMFilterMages", false)

local C = MH.db.char
local function rowFor(name) for _, r in ipairs(P.rows) do if r.__shown and r.entryName == name then return r end end end
local function fmMacro() return FRAMES.MageHelperBuff_fmout.__attr.macrotext end
rowFor("Anya").partnerButton.__scripts.OnClick()
check(C.focusMagicPartner == "Anya" and fmMacro():find("/targetexact Anya", 1, true), "partner Anya set and used by FM OUT")
rowFor("Bheal").targetButton.__scripts.OnClick()
check(C.focusMagicTarget == "Bheal" and C.focusMagicPartner == "Anya", "temporary target keeps partner")
check(fmMacro():find("/targetexact Bheal", 1, true), "FM OUT now targets Bheal")
OUT[#OUT + 1] = "LABEL " .. FRAMES.MageHelperBuffBar.fmTargetText.__text
OUT[#OUT + 1] = "STATUS " .. P.status.__text
P.backButton.__scripts.OnClick()
check(C.focusMagicTarget == "Anya" and fmMacro():find("/targetexact Anya", 1, true), "back to partner")

-- in combat: secure button keeps the old target until combat ends
INCOMBAT = true
rowFor("Bheal").targetButton.__scripts.OnClick()
check(fmMacro():find("/targetexact Anya", 1, true), "macro unchanged in combat")
OUT[#OUT + 1] = "STATUS-COMBAT " .. P.status.__text
INCOMBAT = false
FireEvent("PLAYER_REGEN_ENABLED")
check(fmMacro():find("/targetexact Bheal", 1, true), "macro applied after combat")
OUT[#OUT + 1] = "PICKER OK"
'''

# Molten Armor with the T9 2-piece bonus: equip from bags by ID, cast, swap back, colors.
T9 = r'''
local B = FRAMES.MageHelperBuff_armor
local de = GetLocale() == "deDE"
local L_T9_ON, L_T9_CAST, L_ARMOR = de and "T9 an" or "T9 on", de and "Casten" or "Cast", de and "Rüstung" or "Armor"
local MOLTEN = GetSpellInfo(43046)
local T10 = { [1] = "|cffa335ee|Hitem:51281:0:0:0:0:0:0:0|h[T10 Head]|h|r", [3] = "|Hitem:51284|h[T10 Shoulders]|h",
              [5] = "|Hitem:51283|h[T10 Robe]|h", [7] = "|Hitem:51282:3719:0:0:0|h[T10 Legs heroic]|h", [10] = "|Hitem:51280|h[T10 Gloves]|h" }
local function reset()
  INCOMBAT = false; AURAS.player = {}; CASTS = {}
  EQUIPPED = {}; for s, l in pairs(T10) do EQUIPPED[s] = l end
  BAGS = { [0] = { "|Hitem:47760|h[Khadgar's Leggings of Triumph]|h", "|Hitem:12345|h[Junk]|h", "|Hitem:47753|h[Khadgar's Gauntlets of Triumph]|h" } }
  wipe(MH.db.char.moltenSwap); MH.db.char.moltenBonus = nil; MH.db.char.moltenRestorePending = false
  Tick(0.6)
end
-- a secure click: PreClick, the action the attributes describe, PostClick
local function click()
  if B.__scripts.PreClick then B.__scripts.PreClick(B, "LeftButton") end
  if B.__attr.type == "spell" then CASTS[#CASTS + 1] = B.__attr.spell end
  if B.__scripts.PostClick then B.__scripts.PostClick(B, "LeftButton") end
  Tick(0.6); Tick(0.6); Tick(0.6)
end
local function state() return B.text.__text .. " " .. B.timer.__text end
local function itemAt(slot) return tonumber((EQUIPPED[slot] or ""):match("item:(%d+)")) end

reset()
check(B.text.__text == L_T9_ON, "blue state before the swap: " .. state())
OUT[#OUT + 1] = "T9 start: " .. state()
click()
check(#CASTS == 0, "click 1 does not cast")
check(itemAt(7) == 47760 and itemAt(10) == 47753 and itemAt(1) == 51281, "click 1 equips T9 legs + hands only")
check(B.text.__text == L_T9_CAST and B.__attr.type == "spell", "orange state, cast action restored: " .. state())
OUT[#OUT + 1] = "T9 after click 1: " .. state()
click()
check(#CASTS == 1 and CASTS[1] == MOLTEN, "click 2 casts Molten Armor")
FireEvent("UNIT_SPELLCAST_SUCCEEDED", "player", MOLTEN)
check(EQUIPPED[7] == T10[7] and EQUIPPED[10] == T10[10], "exact original items back (heroic legs with enchant)")
Tick(0.6); Tick(0.6) -- VerifyRestore checks the slots one second after the restore
check(next(MH.db.char.moltenSwap) == nil and MH.db.char.moltenBonus == true, "swap cleared after verification, bonus remembered")
AURAS.player = { { MOLTEN, 0, GetTime() + 1800, 43046 } }; Tick(0.6)
check(B.text.__text == L_ARMOR, "green state with bonus: " .. state())
OUT[#OUT + 1] = "T9 with bonus: " .. state()

-- buff without bonus: cast while wearing no T9
reset(); MH.db.profile.moltenT9 = false; click()
check(#CASTS == 1 and itemAt(7) == 51282, "option off: casts without swapping")
FireEvent("UNIT_SPELLCAST_SUCCEEDED", "player", MOLTEN)
check(MH.db.char.moltenBonus == false, "cast without T9 is remembered as no bonus")
MH.db.profile.moltenT9 = true

-- in combat the button only casts
reset(); INCOMBAT = true; click()
check(#CASTS == 1 and itemAt(7) == 51282, "in combat: cast only, no swap")
INCOMBAT = false

-- fewer than 2 T9: grey, click casts without bonus
reset(); BAGS = { [0] = { "|Hitem:47760|h[Khadgar's Leggings of Triumph]|h" } }; Tick(0.6)
check(B.timer.__text == "1/2", "missing state shows 1/2: " .. state())
click()
check(#CASTS == 1, "not enough T9: plain cast")

-- one T9 piece already worn: only one more is swapped in
reset(); EQUIPPED[1] = "|Hitem:47761|h[Khadgar's Hood of Triumph]|h"; click()
check(#CASTS == 0 and itemAt(7) == 47760 and itemAt(10) == 51280, "only the missing second piece is equipped")
check(MH.db.char.moltenSwap[1] == nil and MH.db.char.moltenSwap[7].orig == T10[7], "worn T9 is not part of the swap")
-- review fixes ---------------------------------------------------------------
local function fill() return B.status.__vc end
local function isRed(c) return c and c[1] > 0.9 and c[2] < 0.1 and c[3] < 0.1 end
-- missing buff is red (fill) whatever the T9 step
reset()
check(isRed(fill()) and B.timer.__text == "!", "missing buff: red fill, '!' (" .. state() .. ")")
check(B.border.__vc[3] > 0.9, "border shows the T9 step (blue)")

-- fast double click: the second click inside the settle time does neither equip nor cast
reset()
B.__scripts.PreClick(B); if B.__attr.type == "spell" then CASTS[#CASTS + 1] = 1 end; B.__scripts.PostClick(B)
local equips = EQUIP_COUNT
B.__scripts.PreClick(B); if B.__attr.type == "spell" then CASTS[#CASTS + 1] = 1 end; B.__scripts.PostClick(B)
check(#CASTS == 0 and EQUIP_COUNT == equips, "double click is ignored while the server equips")
Tick(0.6); Tick(0.6); Tick(0.6)
check(B.text.__text == L_T9_CAST, "after the settle time the button says cast")

-- aborted click 1 + manual swap back + much later cast from the action bar: nothing old comes back
reset(); click()
EquipItemByName(T10[7], 7); EquipItemByName(T10[10], 10)                     -- player swaps back by hand
BAGS[0][5] = "|Hitem:51999|h[New Legs]|h"; EquipItemByName("|Hitem:51999|h", 7) -- and upgrades the legs
SetNow(GetTime() + 900); Tick(0.6)
FireEvent("UNIT_SPELLCAST_SUCCEEDED", "player", MOLTEN)                       -- cast from the action bar, 15 min later
Tick(0.6); Tick(0.6)
check(itemAt(7) == 51999 and next(MH.db.char.moltenSwap) == nil, "stale swap forgotten, new legs stay on")

-- click 1 while the buff is up (rebuff): the button must show the step
reset(); AURAS.player = { { MOLTEN, 0, GetTime() + 600, 43046 } }; Tick(0.6)
check(B.text.__text == L_ARMOR, "buff up without T9: armor label")
click()
check(B.text.__text == L_T9_CAST, "rebuff: after click 1 the button says cast (" .. state() .. ")")

-- option off + buff up: plain green, no promise of a swap
reset(); MH.db.profile.moltenT9 = false; AURAS.player = { { MOLTEN, 0, GetTime() + 600, 43046 } }; Tick(0.6)
check(B.status.__vc[2] > 0.9 and B.status.__vc[1] < 0.2, "option off: active armor is green")
MH.db.profile.moltenT9 = true

-- cast in combat with T9 on: gear comes back after combat (flag saved for reloads)
reset(); click(); INCOMBAT = true
click()
FireEvent("UNIT_SPELLCAST_SUCCEEDED", "player", MOLTEN)
check(itemAt(7) == 47760 and MH.db.char.moltenRestorePending == true, "in combat the T9 stays on, restore pending (saved)")
INCOMBAT = false; FireEvent("PLAYER_REGEN_ENABLED"); Tick(0.6); Tick(0.6)
check(EQUIPPED[7] == T10[7] and EQUIPPED[10] == T10[10] and not MH.db.char.moltenRestorePending, "restored after combat")

-- original item sold in the meantime: message, T9 stays, no endless retries
reset(); click()
for i = 1, 16 do if BAGS[0][i] == T10[7] then BAGS[0][i] = nil end end
local before = #OUT
FireEvent("UNIT_SPELLCAST_SUCCEEDED", "player", MOLTEN); Tick(0.6); Tick(0.6); Tick(0.6)
check(itemAt(7) == 47760 and EQUIPPED[10] == T10[10], "sold legs: T9 legs stay, gloves come back")
check(#OUT > before and next(MH.db.char.moltenSwap) == nil, "sold item reported, swap cleared")

-- a restore the server ignores is retried and then reported
reset(); click()
local realEquip = EquipItemByName
EquipItemByName = function() EQUIP_COUNT = (EQUIP_COUNT or 0) + 1 end -- server drops every request
before = #OUT
local tries = EQUIP_COUNT
FireEvent("UNIT_SPELLCAST_SUCCEEDED", "player", MOLTEN)
for i = 1, 10 do Tick(0.6) end
EquipItemByName = realEquip
check(EQUIP_COUNT - tries == 6 and #OUT > before and next(MH.db.char.moltenSwap) == nil, "failed restore tried 3x, then reported")

-- click 1 before the pull, cast in combat, fight longer than 10 minutes: gear still comes back
reset(); click(); INCOMBAT = true; click()
FireEvent("UNIT_SPELLCAST_SUCCEEDED", "player", MOLTEN)
SetNow(GetTime() + 900); Tick(0.6)
INCOMBAT = false; FireEvent("PLAYER_REGEN_ENABLED"); Tick(0.6); Tick(0.6)
check(EQUIPPED[7] == T10[7] and EQUIPPED[10] == T10[10], "long fight: restored after combat")

-- new click 1 right after a cast: the old restore check must not take the new T9 off again
reset(); click(); click()
FireEvent("UNIT_SPELLCAST_SUCCEEDED", "player", MOLTEN)               -- restore sent, check scheduled
AURAS.player = { { MOLTEN, 0, GetTime() + 1800, 43046 } }
B.__scripts.PreClick(B); B.__scripts.PostClick(B)                      -- immediate new click 1
for i = 1, 5 do Tick(0.6) end
check(itemAt(7) == 47760 and itemAt(10) == 47753, "new swap survives the old restore check")

Slash("t9")
OUT[#OUT + 1] = "T9 OK"
'''

# Color themes: panels, titles, labels and MF SET follow the theme; signal colors stay.
THEMES = r'''
local KR = MageHelperFrame
local function rgb(t) return string.format("%.2f,%.2f,%.2f", t[1], t[2], t[3]) end
check(MH.db.profile.theme == "standard" and rgb(KR.bg.__rgba) == "0.00,0.00,0.00" and KR.bg.__rgba[4] == 0.35, "standard look unchanged")
check(not KR.themeStripe.__shown, "no stripe in standard")
Slash("theme rosa")
check(MH.db.profile.theme == "pink", "/mh theme rosa")
check(rgb(KR.bg.__rgba) == "0.13,0.03,0.10" and KR.bg.__rgba[4] == 0.55, "bar background pink, more opaque")
check(KR.themeStripe.__shown and rgb(KR.themeStripe.__vc) == "1.00,0.42,0.74", "pink accent stripe")
check(rgb(FRAMES.MageHelperBuffBar.title.__tc) == "1.00,0.62,0.86", "buff bar title pink")
check(rgb(FRAMES.MageHelperBuff_FMSet.bg.__vc) == "0.58,0.10,0.40", "MF SET button pink")
check(rgb(FRAMES.MageHelperAnalyzerWindow.bg.__rgba) == "0.13,0.03,0.10" and FRAMES.MageHelperAnalyzerWindow.bg.__rgba[4] == 0.78, "analyzer window keeps its alpha")
Tick(0.15)
check(rgb(FRAMES.MageHelperButton_pyro.text.__tc) == "1.00,0.84,0.94", "button labels use theme text color")
-- signal colors are independent of the theme
local s = FRAMES.MageHelperBuff_flask.status.__vc
Slash("theme red"); Tick(0.15)
check(rgb(FRAMES.MageHelperBuff_flask.status.__vc) == rgb(s), "signal color unchanged by theme")
check(rgb(KR.themeStripe.__vc) == "0.80,0.24,0.38", "red theme uses the wine accent")
local o = LibStub("AceConfigRegistry-3.0"):GetOptionsTable("MageHelper", "dialog", "MyLib-1.0")
o.args.general.args.theme.set({ "general", "theme" }, "blue")
check(rgb(KR.bg.__rgba) == "0.02,0.06,0.16", "theme via options")
Slash("fm"); local P = FRAMES.MageHelperFMPicker
check(rgb(P.bg.__rgba) == "0.02,0.06,0.16" and rgb(P.title.__tc) == "0.55,0.80,1.00", "picker created later gets the theme")
P:Hide()
MH.db:SetProfile("Themes"); check(rgb(KR.bg.__rgba) == "0.00,0.00,0.00", "profile switch applies its theme")
Slash("theme bogus")
OUT[#OUT + 1] = "THEMES OK"
'''

# Flask choice: auto by class/spec, fixed flask, any flask; matched by buff ID.
FLASK = r'''
local F = FRAMES.MageHelperBuff_flask
local C = MH.db.char
local function active() Tick(0.15); return F.timer.__text ~= "!" end
local function useFlask(buffId) AURAS.player = { { GetSpellInfo(buffId) or "Flask", 0, GetTime() + 3600, buffId } } end
check(C.flask == "auto", "default flask choice is auto")
useFlask(53755)
check(active(), "mage: Frost Wyrm counts in auto")
useFlask(53760)
check(not active(), "mage: Endless Rage does not count")
Slash("flask rage")
check(C.flask == "endlessrage" and active(), "fixed choice Endless Rage")
Slash("flask any"); useFlask(62380)
check(active(), "any flask counts (resistance)")
Slash("flask auto")
PLAYER_CLASS, PLAYER_TALENTS = "WARRIOR", { 0, 5, 56 }; Slash("flask auto")
useFlask(53758)
check(active(), "protection warrior: Stoneblood in auto")
PLAYER_CLASS, PLAYER_TALENTS = "PALADIN", { 51, 5, 15 }; Slash("flask auto"); useFlask(53755)
check(active(), "holy paladin: Frost Wyrm in auto")
check(tostring(F.icon.__tex):find("item46376", 1, true), "icon follows the expected flask: " .. tostring(F.icon.__tex))
local o = LibStub("AceConfigRegistry-3.0"):GetOptionsTable("MageHelper", "dialog", "MyLib-1.0")
check(o.args.general.args.flask.values().stoneblood ~= nil, "options list the flasks")
o.args.general.args.flask.set({ "general", "flask" }, "stoneblood")
check(C.flask == "stoneblood", "flask via options")
Slash("flask"); Slash("flask auto")
-- tanks by form: death knight in Frost Presence, druid in Bear Form -> Stoneblood
PLAYER_CLASS, PLAYER_TALENTS, PLAYER_FORM = "DEATHKNIGHT", { 0, 51, 20 }, 48263; Slash("flask auto"); useFlask(53758)
check(active(), "death knight in Frost Presence: Stoneblood")
PLAYER_FORM = nil; Slash("flask auto"); useFlask(53760)
check(active(), "death knight without Frost Presence: Endless Rage")
PLAYER_CLASS, PLAYER_TALENTS, PLAYER_FORM = "DRUID", { 0, 56, 15 }, 9634; Slash("flask auto"); useFlask(53758)
check(active(), "druid in Dire Bear Form: Stoneblood")
-- an invalid saved value falls back to auto in the options
C.flask = "bogus"
check(o.args.general.args.flask.get() == "auto", "invalid flask value shows as auto")
C.flask = "auto"
PLAYER_CLASS, PLAYER_TALENTS, PLAYER_FORM, AURAS.player = nil, nil, nil, {}
OUT[#OUT + 1] = "FLASK OK"
'''

# T10 links not readable at login: the count cached as 0 is dropped once 5 s after login.
T10LOGIN = r'''
local function reco() return FRAMES.MageHelperOneButton.currentKey end
PLAYER_TALENTS = { 57, 3, 11 }; FireEvent("PLAYER_TALENT_UPDATE")
INCOMBAT, TARGETNAME, EQUIPPED = true, "Dummy", {}
Tick(0.15); Tick(0.15)
check(reco() == "pom", "login: no T10 pieces readable yet (" .. tostring(reco()) .. ")")
EQUIPPED = { [1] = "|Hitem:51281|h[x]|h", [3] = "|Hitem:51155|h[x]|h", [5] = "|Hitem:50278|h[x]|h", [7] = "|Hitem:51282|h[x]|h" }
for i = 1, 34 do Tick(0.15) end   -- links arrive without UNIT_INVENTORY_CHANGED; past the 5 s timer
check(reco() == "mirror", "T10 recounted 5 s after login (" .. tostring(reco()) .. ")")
INCOMBAT, TARGETNAME, EQUIPPED, PLAYER_TALENTS = false, nil, {}, nil
FireEvent("UNIT_INVENTORY_CHANGED", "player"); FireEvent("PLAYER_TALENT_UPDATE"); Tick(0.15)
check(FRAMES.MageHelperButton_lb.__shown, "back to Fire after the login check")
OUT[#OUT + 1] = "T10LOGIN OK"
'''

# Arcane rotation: auto mode by talents, button set, cooldowns, gem/Evocation, Missile Barrage,
# burn vs conserve (mana threshold and time-to-die estimate), movement, switching back to Fire.
ARCANE = r'''
local KR = MageHelperFrame
local de = GetLocale() == "deDE"
local function upd(n) for i = 1, (n or 8) do Tick(0.15) end end   -- 1.2 s: burn/conserve is re-decided every second
local function reco() return FRAMES.MageHelperOneButton.currentKey end
local function shown(k) return FRAMES["MageHelperButton_" .. k].__shown end
local function macro(k) return FRAMES["MageHelperButton_" .. k].__attr.macrotext end
local function S(id) return (GetSpellInfo(id)) end
local AP, POM, MI, IV, EVO, BARR = S(12042), S(12043), S(55342), S(12472), S(12051), S(44781)
local function state(mana, stacks)
  PLAYER_MANA = mana
  DEBUFFS.player = stacks > 0 and { { S(36032), stacks, nil, 36032 } } or {}
end
local function drain(hpPerSec, seconds, o)   -- o: boss = boss1-4 %/s, mana = mana/s lost,
  o = o or {}                                 -- gains = { { mana, every s }, ... } external mana
  local recos = {}
  for i = 1, seconds / 0.15 do
    TARGET_HP = TARGET_HP - hpPerSec * 0.15
    if o.boss then for _, b in pairs(BOSSES) do b.hp = b.hp - o.boss * 0.15 end end
    if o.mana then PLAYER_MANA = PLAYER_MANA - o.mana * 0.15 end
    for _, g in ipairs(o.gains or {}) do
      if i % math.floor(g[2] / 0.15 + 0.5) == 0 then PLAYER_MANA = math.min(PLAYER_MANA + g[1], PLAYER_MANA_MAX) end
    end
    Tick(0.15)
    if recos[#recos] ~= reco() then recos[#recos + 1] = reco() end
  end
  return #recos - 1   -- number of recommendation changes
end
local function debug() return KR.debugInfo.__text end
local function btnState(k) return FRAMES["MageHelperButton_" .. k].state end
local function newFight()
  INCOMBAT = false; FireEvent("PLAYER_REGEN_ENABLED"); upd(1)
  INCOMBAT = true; FireEvent("PLAYER_REGEN_DISABLED")
end
local UNSURE = de and "unsicher" or "unreliable"

INCOMBAT, MOVING, AURAS.player, TARGETNAME, TARGET_HP = false, false, {}, "Dummy", 100
PLAYER_CLASS, PLAYER_FORM, EQUIPPED, BAGS = nil, nil, {}, { [0] = { "|Hitem:33312|h[Mana Sapphire]|h" } }
KNOWN[12472] = false
check(MH.db.profile.rotationMode == "auto" and shown("lb") and not shown("ab"), "no talents: Fire")
PLAYER_TALENTS = { 57, 3, 11 }
FireEvent("PLAYER_TALENT_UPDATE"); upd()
for _, k in ipairs({ "ab", "am", "abarr", "ap", "pom", "mirror", "evo", "gem", "fb_move", "ice", "invis", "stop" }) do check(shown(k), "Arcane button shown: " .. k) end
for _, k in ipairs({ "lb", "pyro", "fireball", "comb", "cd" }) do check(not shown(k), "Fire button hidden: " .. k) end
check(not macro("ap"):find(IV, 1, true), "no Icy Veins in the AP macro while unknown")
check(macro("gem"):find("/use item:33312", 1, true), "gem button uses the Mana Sapphire")
KNOWN[12472] = nil; FireEvent("PLAYER_TALENT_UPDATE")
check(macro("ap"):find("/cast " .. IV, 1, true), "Icy Veins joins the AP macro once known")

-- cooldowns as soon as ready (in combat with a target)
local holder, anchor = CreateFrame("Frame", nil, UIParent), CreateFrame("Frame", nil, UIParent)
local sec = CreateFrame("Button", nil, UIParent, "SecureActionButtonTemplate")
sec:SetParent(holder); sec:SetPoint("LEFT", anchor, "RIGHT")
INCOMBAT = true; FireEvent("PLAYER_REGEN_DISABLED"); state(30000, 0); upd()
-- the stub blocks protected frames in combat like the client (every scenario must avoid it)
check(not pcall(FRAMES.MageHelperButton_ab.Hide, FRAMES.MageHelperButton_ab), "stub: secure button Hide() blocked in combat")
check(not pcall(KR.SetWidth, KR, 100), "stub: main bar SetWidth() blocked in combat")
check(not pcall(KR.SetHeight, KR, 50), "stub: main bar SetHeight() blocked in combat")
check(not pcall(KR.SetScale, KR, 1.2), "stub: main bar SetScale() blocked in combat")
check(not pcall(holder.Hide, holder), "stub: a frame a secure button was parented to later is protected")
check(not pcall(anchor.SetPoint, anchor, "CENTER"), "stub: a frame a secure button is anchored to is protected")
check(reco() == "pom", "Presence of Mind first: " .. tostring(reco()))
COOLDOWNS[POM] = 100; upd(); check(reco() == "ap", "then Arcane Power")
COOLDOWNS[AP] = 100; upd(); check(reco() == "ap", "AP on CD, Icy Veins ready: AP button (macro casts both)")
check(btnState("ap") == "urgent", "AP on CD, Icy Veins ready: the button shows usable, not blue: " .. tostring(btnState("ap")))
COOLDOWNS[IV] = 100; upd(); check(reco() == "mirror", "then Mirror Image")
COOLDOWNS[MI] = 1.2; upd()   -- only the GCD runs on Mirror Image
check(reco() == "mirror", "Mirror Image stays recommended during the GCD: " .. tostring(reco()))
check(btnState("mirror") == "prep", "... but the button is not shown as clickable during the GCD")
COOLDOWNS[MI] = nil
-- right after the cast the client briefly reports only the GCD: no re-recommendation
FireEvent("UNIT_SPELLCAST_SUCCEEDED", "player", MI); COOLDOWNS[MI] = 1.4; upd(3)
check(reco() ~= "mirror", "Mirror Image not re-recommended right after its cast (" .. tostring(reco()) .. ")")
COOLDOWNS[MI] = 180; upd(); check(reco() ~= "mirror", "Mirror Image on its real cooldown")
COOLDOWNS[MI] = nil; upd(); check(reco() == "mirror", "Mirror Image again once ready")
COOLDOWNS[POM], COOLDOWNS[AP] = nil, nil
EQUIPPED = { [1] = "|Hitem:51281|h[x]|h", [3] = "|Hitem:51155|h[x]|h", [5] = "|Hitem:50278|h[x]|h", [7] = "|Hitem:51282|h[x]|h" }
upd(); check(reco() == "pom", "T10 count is cached until UNIT_INVENTORY_CHANGED")
FireEvent("UNIT_INVENTORY_CHANGED", "player"); upd()
check(reco() == "mirror", "T10 4-piece: Mirror Image before PoM/AP")
EQUIPPED = { [1] = "|Hitem:51715|h[x]|h", [3] = "|Hitem:51712|h[x]|h", [5] = "|Hitem:51713|h[x]|h", [7] = "|Hitem:51714|h[x]|h" }
FireEvent("UNIT_INVENTORY_CHANGED", "player"); upd()
check(reco() == "mirror", "T10 4-piece from the 51712-51716 Bloodmage set")
EQUIPPED = {}; FireEvent("UNIT_INVENTORY_CHANGED", "player")
for _, n in ipairs({ AP, POM, MI, IV, EVO }) do COOLDOWNS[n] = 100 end

-- burn/conserve by mana threshold
Slash("burn mana 35")
check(MH.db.profile.arcaneBurnMode == "mana" and MH.db.profile.arcaneBurnMana == 35, "/mh burn mana 35")
state(30000, 0); upd(); check(reco() == "ab", "full mana: Arcane Blast")
state(30000, 4); upd(); check(reco() == "ab", "burn: Arcane Blast also at 4 stacks")
AURAS.player = { { S(44401), 0, nil, 44401 } }; upd()
check(reco() == "am", "Missile Barrage: Arcane Missiles"); AURAS.player = {}
ITEM_COOLDOWNS[33312] = 60
state(9900, 3); upd(); check(reco() == "am", "conserve (33% < 35%): 3 stacks -> Arcane Missiles")
state(9900, 2); upd(); check(reco() == "ab", "conserve: Arcane Blast up to 3 stacks")
state(11100, 3); upd(); check(reco() == "am", "hysteresis: 37% is not enough to burn again")
state(12000, 3); upd(); check(reco() == "ab", "40%: burn again")

-- Presence of Mind only while burning; burst buffs always burn (in mana mode too)
COOLDOWNS[POM] = nil
state(9900, 2); upd(); check(reco() == "ab", "conserve: no Presence of Mind (" .. tostring(reco()) .. ")")
state(9900, 3); upd(); check(reco() == "am", "conserve: still no PoM")
state(12000, 3); upd(); check(reco() == "pom", "burn: Presence of Mind")
COOLDOWNS[POM] = 100
for _, buff in ipairs({ { S(12042), 12042 }, { S(32182), 32182 }, { "Kampfrausch", 2825 }, { "Quad Core", 70747 } }) do
  AURAS.player = { { buff[1], 0, nil, buff[2] } }
  state(6000, 3); upd(); check(reco() == "ab", "burst buff " .. buff[2] .. ": burn at 20% mana")
end
AURAS.player = {}; state(9900, 3); upd(); check(reco() == "am", "burst buff gone: conserve again")

-- Mana Gem only when the missing mana >= its yield; Evocation below 30% without stacks
ITEM_COOLDOWNS[33312] = nil
state(27000, 0); upd(); check(reco() == "ab", "3000 missing: no gem yet")
state(26000, 0); upd(); check(reco() == "gem", "4000 missing: Mana Gem")
ITEM_CHARGES[33312] = 0; upd(); check(reco() ~= "gem", "gem with 0 charges left: not recommended (" .. tostring(reco()) .. ")")
ITEM_CHARGES[33312] = nil
ITEM_COOLDOWNS[33312] = 60; COOLDOWNS[EVO] = nil
state(6000, 2); upd(); check(reco() == "abarr", "20% with stacks: drop them with Arcane Barrage first")
state(6000, 0); upd(); check(reco() == "evo", "20% without stacks: Evocation")
COOLDOWNS[EVO] = 1.0; upd(); check(reco() == "evo", "Evocation stays recommended during the GCD")
COOLDOWNS[EVO] = nil; ITEM_COOLDOWNS[33312] = nil
INCOMBAT = false; state(6000, 0); upd()
check(reco() ~= "evo" and reco() ~= "gem", "out of combat: no Evocation or Mana Gem (" .. tostring(reco()) .. ")")
INCOMBAT = true; ITEM_COOLDOWNS[33312] = 60
COOLDOWNS[EVO] = 100

-- moving
local FB = S(42873)
MOVING = true; state(20000, 0); upd(); check(reco() == "abarr", "moving: Arcane Barrage")
COOLDOWNS[BARR] = 2; upd(); check(reco() == "fb_move", "moving, Barrage on CD: Fire Blast")
COOLDOWNS[FB] = 5; upd(); check(reco() == "abarr" and KR.info.__text:find("CD 2", 1, true), "moving, both on CD: Barrage CD")
KNOWN[44781] = false; upd()
check(reco() ~= "abarr" and not KR.info.__text:find("999", 1, true), "moving without Arcane Barrage, Fire Blast on CD: no move hint (" .. KR.info.__text .. ")")
COOLDOWNS[FB] = nil; upd(); check(reco() == "fb_move", "moving without Arcane Barrage: Fire Blast")
KNOWN[44781], COOLDOWNS[BARR], NOTARGET = nil, nil, true; COOLDOWNS[FB] = 5; upd()
check(reco() ~= "abarr", "moving without a target: no Arcane Barrage (" .. tostring(reco()) .. ")")
-- moving without any instant: no cast at all (never Evocation, Missiles or Blast), only a hint
KNOWN[44781], NOTARGET, COOLDOWNS[EVO] = false, nil, nil
AURAS.player = { { S(44401), 0, nil, 44401 } }; state(6000, 0); upd()
check(reco() == nil and FRAMES.MageHelperOneButton.dynamicMacroText == nil, "moving without instants: no cast recommendation (" .. tostring(reco()) .. ")")
check(btnState("evo") == "normal" and btnState("am") == "normal" and btnState("ab") == "normal", "moving without instants: no cast button lit")
check(KR.info.__text:find(de and "Bewegung" or "Moving", 1, true), "moving without instants: move hint (" .. KR.info.__text .. ")")
AURAS.player = { { S(12043), 0, nil, 12043 } }; upd()
check(reco() == "ab", "moving with Presence of Mind up: instant Arcane Blast (" .. tostring(reco()) .. ")")
AURAS.player, KNOWN[44781], COOLDOWNS[EVO] = {}, nil, 100
MOVING = false; state(20000, 0); upd()
check(reco() == "ab" and FRAMES.MageHelperOneButton.dynamicMacroText ~= nil, "standing again: one-button back")
MOVING, COOLDOWNS[FB], NOTARGET = false, nil, nil
OUT[#OUT + 1] = "ARCANE INFO " .. KR.info.__text

-- fight report in the Arcane rotation: no Fireball rating
local mark = #OUT
Slash("report")
local report = table.concat(OUT, "\n", mark + 1)
check(report:find(de and "keine Feuerball-Wertung" or "no Fireball rating", 1, true), "Arcane fight report: " .. report)
check(not report:find("FB/min", 1, true) and not report:find(de and "Feuerbälle/min" or "Fireballs/min", 1, true), "Arcane fight report has no Fireball rating")
check(not report:find("LB", 1, true) and not report:find("Combustion", 1, true), "Arcane fight report has no Fire LB/Combustion line")
check(report:find(de and "Spiegelbilder" or "Mirror Images", 1, true), "Arcane fight report: Mirror Image/Ice Block line")

-- burn auto (owner's rule): burst buff, or mana >= threshold, or a reliable estimate says the
-- mana lasts until the boss dies. Every case starts a fresh fight (the drain is measured per fight).
-- Evocation 4 min, gem in the bags: restore spread ~75 + ~29 mana/s; model drain ~215 mana/s.
Slash("burn auto"); Slash("debug on")
check(MH.db.profile.arcaneBurnMode == "auto" and MH.db.profile.arcaneBurnMana == 35, "/mh burn auto keeps the threshold")
COOLDOWNS[EVO] = 240

newFight(); TARGETNAME, TARGET_HP = "Long boss", 100; state(30000, 3); upd(4)
check(reco() == "ab" and debug():find(UNSURE, 1, true), "new target, estimate unreliable, full mana: burn (" .. debug() .. ")")
drain(0.1, 8)   -- ~1000 s to live: the mana can't last, but it is above the threshold
check(reco() == "ab" and debug():find("TTD", 1, true), "full mana on a very long fight: burn (" .. debug() .. ")")
OUT[#OUT + 1] = "ARCANE DEBUG " .. debug()

newFight(); TARGETNAME, TARGET_HP = "Fast boss", 60; state(9000, 3); upd(8)   -- 30% < 35%
check(reco() == "am", "below the threshold, estimate unreliable: conserve")
drain(5, 6)     -- dies in ~6 s, 9000 mana last ~80 s
check(reco() == "ab" and debug():find("TTD", 1, true), "below the threshold, short reliable TTD: burn (" .. debug() .. ")")
OUT[#OUT + 1] = "ARCANE DEBUG " .. debug()
-- immune phase: the estimate becomes unreliable; the last decision holds (no flip-flop), then
-- after BURN_HOLD (15 s) the mana rule alone decides
local changes = drain(0, 12)
check(changes == 0 and reco() == "ab" and debug():find(UNSURE, 1, true), "unreliable: keeps burning, no flip (" .. changes .. " changes, " .. debug() .. ")")
changes = drain(0, 10)
check(changes == 1 and reco() == "am", "after the hold: the mana rule, one single switch (" .. changes .. ", " .. debug() .. ")")

newFight(); TARGETNAME, TARGET_HP = "Slow boss", 60; state(9000, 3); upd(2)
drain(0.2, 8)   -- ~290 s to live, the mana lasts ~80 s
check(reco() == "am", "below the threshold, long TTD: conserve (" .. debug() .. ")")
OUT[#OUT + 1] = "ARCANE DEBUG " .. debug()
changes = drain(0, 8)
check(changes == 0 and reco() == "am" and debug():find(UNSURE, 1, true), "below the threshold, unreliable: keeps conserving (" .. debug() .. ")")

-- realistic projection: 50% mana, 2-minute kill, threshold 60%: the old "every Arcane Blast at
-- 4 stacks" model (~730 mana/s, 20 s) conserved; the Missile Barrage cycle (~110 mana/s net) burns
Slash("burn auto 60")
newFight(); TARGETNAME, TARGET_HP = "Two-minute boss", 60; state(15000, 3); upd(2)
check(reco() == "am", "50% < 60%, no estimate yet: conserve")
drain(0.5, 8)   -- ~110 s to live
check(reco() == "ab" and debug():find(de and "Modell" or "model", 1, true), "2-min kill at 50% mana: burn on the model (" .. debug() .. ")")
OUT[#OUT + 1] = "ARCANE DEBUG " .. debug()
-- measured drain replaces the model after 20 s of burning (here 600 mana/s, much more than the model)
Slash("burn auto 35")
newFight(); TARGETNAME, TARGET_HP = "Measured boss", 100; state(30000, 0); upd(2)
drain(0.1, 24, { mana = 600 })
local rate = tonumber(debug():match("(%d+) [Mm]ana/s"))
check(debug():find(de and "gemessen" or "measured", 1, true) and rate and rate > 550 and rate < 650, "measured drain ~600 mana/s: " .. debug())
-- Arcane Power does not distort the measurement
AURAS.player = { { S(12042), 0, nil, 12042 } }
drain(0.1, 6, { mana = 2000 })
rate = tonumber(debug():match("(%d+) [Mm]ana/s"))
check(rate and rate < 650, "Arcane Power time is not measured: " .. debug())
AURAS.player = {}
-- external mana (Mana Tide ~1800 every 3 s, Hymn of Hope ~900 every 2 s) during the burn: gains
-- are not negative drain, so below the threshold the mana doesn't "last forever" (burn until OOM)
local MEASURED = de and "gemessen" or "measured"
newFight(); TARGETNAME, TARGET_HP = "Tide boss", 100; state(15000, 0); upd(2)
drain(0.1, 24, { mana = 300, gains = { { 1800, 3 }, { 900, 2 } } })
rate = tonumber(debug():match("(%d+) [Mm]ana/s"))
check(debug():find(MEASURED, 1, true) and rate and rate > 250, "Mana Tide/Hymn during the burn: drain stays ~300 mana/s: " .. debug())
state(9000, 3); drain(0.1, 3)
check(reco() == "am", "below the threshold after Mana Tide/Hymn: conserve, no burn until OOM (" .. debug() .. ")")
-- a measured drain far below the model is floored at half the gross model (~107 mana/s)
newFight(); TARGETNAME, TARGET_HP = "Floor boss", 100; state(30000, 0); upd(2)
drain(0.1, 24, { mana = 20 })
rate = tonumber(debug():match("(%d+) [Mm]ana/s"))
check(debug():find(MEASURED, 1, true) and rate and rate >= 100, "measured drain floored at half the model: " .. debug())

-- Blood Prince Council: switching the target among boss1-3 keeps the samples and the decision
newFight(); BOSSES = { boss1 = { name = "Valanar", hp = 60 }, boss2 = { name = "Keleseth", hp = 60 }, boss3 = { name = "Taldaram", hp = 60 } }
TARGETNAME, TARGET_HP = "Valanar", 60; state(9000, 3); upd(2)
drain(1, 8, { boss = 1 })   -- shared health, ~50 s to live, the mana lasts ~80 s
check(reco() == "ab" and debug():find("TTD", 1, true), "Council: burn on the estimate (" .. debug() .. ")")
TARGETNAME = "Keleseth"; local changes = drain(1, 4, { boss = 1 })
check(changes == 0 and reco() == "ab" and debug():find("TTD", 1, true), "target swap boss1 -> boss2: estimate and decision kept (" .. changes .. ", " .. debug() .. ")")
drain(0, 4)   -- invulnerable phase: the estimate becomes unreliable, the decision holds
TARGETNAME = "Taldaram"; changes = drain(0, 4)
check(changes == 0 and reco() == "ab" and debug():find(UNSURE, 1, true), "target swap during the hold: still burning (" .. changes .. ", " .. debug() .. ")")
-- no boss units: a different target doesn't inherit the held decision of the old one
BOSSES = {}
newFight(); TARGETNAME, TARGET_HP = "Trash A", 60; state(9000, 3); upd(2)
drain(5, 6)
check(reco() == "ab", "trash A: burn on the estimate (" .. debug() .. ")")
TARGETNAME, TARGET_HP = "Trash B", 100; drain(0, 2)
check(reco() == "am", "new trash target without data: the mana rule, not trash A's decision (" .. debug() .. ")")

-- boss units: the estimate follows boss1, not the add in the target; Evocation is never skipped
-- because of an add
newFight(); BOSSES.boss1 = { name = "Deathwhisper", hp = 60 }
TARGETNAME, TARGET_HP = "Adherent", 60; COOLDOWNS[EVO] = nil; state(6000, 0); upd(2)
drain(5, 6, { boss = 0.2 })  -- the add dies in seconds, the boss in ~5 min
check(debug():find("Boss", 1, true), "estimate from boss1: " .. debug())
check(reco() == "evo", "add dying fast: Evocation is not skipped (" .. tostring(reco()) .. ", " .. debug() .. ")")
TARGET_HP = 60; BOSSES.boss1.hp = 20; drain(0, 1); drain(3, 6, { boss = 3 })  -- the boss itself dies in ~1 s
check(reco() ~= "evo", "boss dying before the mana runs out: Evocation skipped (" .. debug() .. ")")
BOSSES.boss1 = { name = "Valithria", hp = 50, attackable = false }; TARGET_HP = 60
drain(5, 6)   -- friendly boss: the add's health must not be used
check(debug():find(de and "Boss nicht angreifbar" or "boss not attackable", 1, true), "friendly boss: no estimate (" .. debug() .. ")")
check(reco() == "evo", "friendly boss, low mana: Evocation")
BOSSES = {}; COOLDOWNS[EVO] = 100
Slash("burn mana"); TARGET_HP = 60; state(18000, 3); drain(0.5, 2)
check(reco() == "ab", "mana mode ignores the estimate")

-- switching the rotation: in combat only after the fight; Fire unchanged
Slash("rota feuer")
check(MH.db.profile.rotationMode == "fire" and shown("ab") and not shown("lb"), "in combat the buttons stay")
check(reco() == "ab" or reco() == "am", "Arcane recommendations until the switch")
INCOMBAT = false; FireEvent("PLAYER_REGEN_ENABLED"); upd()
check(shown("lb") and shown("fireball") and not shown("ab") and not shown("gem"), "after combat: Fire buttons")
AURAS.player = { { "Hot Streak", 0, nil, 48108 } }; upd()
check(reco() == "pyro", "Fire rotation: Hot Streak -> Pyroblast"); AURAS.player = {}
check(KR.info.__text:find("FB/min", 1, true), "Fire info line")
Slash("rota arkan"); check(shown("ab") and not shown("lb"), "/mh rota arkan")
Slash("rota auto"); check(shown("ab"), "auto with Arcane talents")
PLAYER_TALENTS = { 0, 55, 16 }; FireEvent("ACTIVE_TALENT_GROUP_CHANGED"); check(shown("lb") and not shown("ab"), "spec switch to Fire")
PLAYER_TALENTS = { 0, 17, 54 }; FireEvent("PLAYER_TALENT_UPDATE"); check(shown("fbolt") and not shown("lb") and not shown("ab"), "Frost talents: Frost")
Slash("rota"); Slash("burn"); Slash("rota bogus")

-- options
local o = LibStub("AceConfigRegistry-3.0"):GetOptionsTable("MageHelper", "dialog", "MyLib-1.0")
local a = o.args.arcane.args
check(a.arcaneBurnMana.min == 10 and a.arcaneBurnMana.max == 90 and a.arcaneBurnMode.values.auto ~= nil, "Arcane options group")
o.args.arcane.set({ "arcane", "arcaneBurnMana" }, 50); check(MH.db.profile.arcaneBurnMana == 50, "threshold via options")
o.args.arcane.set({ "arcane", "arcaneBurnMode" }, "auto"); check(MH.db.profile.arcaneBurnMode == "auto", "burn mode via options")
check(o.args.rotation.args.rotationMode.values().auto ~= nil, "rotation mode values")
o.args.rotation.args.rotationMode.set({ "rotation", "rotationMode" }, "arcane"); check(shown("ab"), "rotation mode via options")
Slash("help")
Slash("debug off"); Slash("rota auto")
PLAYER_TALENTS, DEBUFFS.player = nil, {}
OUT[#OUT + 1] = "ARCANE OK"
'''

# Spellsteal: worth list by ID, isStealable decides, range, focus hint, setting, cache, indicator,
# Fire and Arcane, emergencies first, nothing protected changes in combat.
SPELLSTEAL = r'''
local KR = MageHelperFrame
local de = GetLocale() == "deDE"
local function upd(n) for i = 1, (n or 2) do Tick(0.15) end end
local function reco() return FRAMES.MageHelperOneButton.currentKey end
local function st(k) return FRAMES["MageHelperButton_" .. k].state end
local function shown(k) return FRAMES["MageHelperButton_" .. k].__shown end
local function info() return KR.info.__text end
local IND = FRAMES.MageHelperStealIndicator
local STEAL = GetSpellInfo(30449)
local NP = de and "Netherkraft" or "Nether Power"
local VM = de and "Vampirmacht" or "Vampiric Might"
local OTHER = de and "Irgendein Buff" or "Some buff"
-- aura with an explicit expiry: { name, count, expires, spellId, caster, isStealable }
local function aura(name, id, stealable, count) return { name, count or 0, GetTime() + 600, id, nil, stealable and 1 or nil } end
local function setTarget(list) AURAS.target = list; FireEvent("UNIT_AURA", "target") end
local errors = #ERRORS

INCOMBAT, MOVING, NOTARGET, TARGETNAME, FOCUS, TARGET_HP = false, false, nil, "Lord Jaraxxus", nil, 100
AURAS.player, DEBUFFS.player, COOLDOWNS, ITEM_COOLDOWNS, BOSSES = {}, {}, {}, {}, {}
check(MH.db.profile.spellsteal == true and MH.db.profile.spellstealAll == false, "Spellsteal defaults: on, worth list only")
Slash("rota feuer"); upd()
local m = FRAMES.MageHelperButton_steal.__attr.macrotext
check(m:find("/cast [mod:shift,@mouseover,harm,nodead][@target,harm,nodead] " .. STEAL, 1, true) and m:find("#showtooltip " .. STEAL, 1, true), "Spellsteal macro: target, Shift = mouseover: " .. m)
check(not m:find("[@mouseover,harm,nodead][]", 1, true), "Spellsteal macro: no plain mouseover first")
check(shown("steal") and shown("lb") and KR.__w == 8 + 10 * 53 + 95, "Fire set has the steal button, bar width " .. tostring(KR.__w))
check(not IND.__shown, "indicator hidden without stealable buffs")

-- Fire: listed stealable buff on the target -> urgent Spellsteal, above Hot Streak
INCOMBAT = true; FireEvent("PLAYER_REGEN_DISABLED")
setTarget({ aura(OTHER, 12345, true), aura(NP, 67108, true, 2) }); upd()
check(reco() == "steal" and st("steal") == "urgent", "Fire: listed buff -> urgent steal (" .. tostring(reco()) .. ", " .. tostring(st("steal")) .. ")")
check(info():find(NP, 1, true), "info line names the buff: " .. info())
AURAS.player = { { "Hot Streak", 0, nil, 48108 } }; upd()
check(reco() == "steal", "Spellsteal before Hot Streak"); AURAS.player = {}
check(IND.__shown and IND.icon.__tex == "aura67108" and IND.count.__text == "2" and IND.worth and IND.timer.__text ~= "", "indicator: worth buff first, icon, stacks, time")
check(IND.border.__vc[1] == 1 and IND.border.__vc[4] == 1, "indicator: strong border for the worth list")
local mark = #OUT
IND.__scripts.OnEnter(IND)
local tip = table.concat(OUT, "\n", mark + 1)
check(tip:find(NP, 1, true) and tip:find(OTHER, 1, true), "tooltip lists every stealable buff: " .. tip)
OUT[#OUT + 1] = "STEAL TIP " .. tip:gsub("\n", " | ")

-- emergencies still win
AURAS.player = { { GetSpellInfo(45438), 0, nil, 45438 } }; upd()
check(reco() == "ice", "Ice Block cancel beats Spellsteal (" .. tostring(reco()) .. ")"); AURAS.player = {}
upd(); check(reco() == "steal", "steal again after the emergency")

-- out of range: no recommendation, blue button, note in the info line
RANGE.target = 0; upd()
check(reco() ~= "steal" and st("steal") == "prep", "out of range: rotation goes on, steal button blue (" .. tostring(reco()) .. ", " .. tostring(st("steal")) .. ")")
check(info():find(de and "außer Reichweite" or "out of range", 1, true), "out of range note: " .. info())
OUT[#OUT + 1] = "STEAL INFO " .. info()
RANGE.target = nil
-- not usable (e.g. no mana): no recommendation
USABLE[STEAL] = false; upd(); check(reco() ~= "steal", "not usable: no recommendation"); USABLE[STEAL] = nil

-- listed but not stealable (isStealable nil): nothing
setTarget({ aura(NP, 67108, false) }); upd()
check(reco() ~= "steal" and not IND.__shown and st("steal") == "normal", "listed buff without isStealable: nothing")

-- unlisted stealable buff: indicator (weak border) but only recommended with spellstealAll
setTarget({ aura(OTHER, 12345, true) }); upd()
check(reco() ~= "steal" and IND.__shown and not IND.worth and IND.border.__vc[4] < 1, "unlisted stealable: indicator only")
Slash("raub alle"); upd()
check(MH.db.profile.spellstealAll and reco() == "steal" and st("steal") == "glow", "/mh raub alle: unlisted -> steal, not urgent (" .. tostring(st("steal")) .. ")")
Slash("steal worth"); upd()
check(not MH.db.profile.spellstealAll and reco() ~= "steal", "/mh steal worth: unlisted ignored again")

-- the cache: no scan per update, rescan on UNIT_AURA / target change only
local calls = AURA_CALLS
upd(10)
check(AURA_CALLS == calls, "no aura scan on display updates")
AURAS.target = { aura(NP, 66228, true) }; upd()
check(reco() ~= "steal", "cache unchanged without an event")
FireEvent("UNIT_AURA", "raid3"); check(AURA_CALLS == calls, "UNIT_AURA of other units ignored")
FireEvent("UNIT_AURA", "target"); upd()
check(reco() == "steal" and AURA_CALLS > calls, "UNIT_AURA on the target rescans")
AURAS.target = {}; TARGETNAME = "Add"; FireEvent("PLAYER_TARGET_CHANGED"); upd()
check(reco() ~= "steal" and not IND.__shown, "target change rescans (buff gone, indicator hidden)")
TARGET_FRIENDLY = true; AURAS.target = { aura(NP, 66228, true) }; FireEvent("PLAYER_TARGET_CHANGED"); upd()
check(reco() ~= "steal" and not IND.__shown, "friendly target is not scanned")
TARGET_FRIENDLY = nil; FireEvent("PLAYER_TARGET_CHANGED"); upd()
check(reco() == "steal", "hostile again: steal")
TARGET_DEAD = true; upd()   -- died without UNIT_AURA: the cache still has the buff
check(reco() ~= "steal" and st("steal") ~= "prep", "dead target (stale cache): no steal (" .. tostring(reco()) .. ")")
TARGET_DEAD = nil; upd(); check(reco() == "steal", "alive again: steal")
TARGET_FRIENDLY = true; upd()   -- turned friendly (mind control ended etc.) without an event
check(reco() ~= "steal", "friendly target (stale cache): no steal (" .. tostring(reco()) .. ")")
TARGET_FRIENDLY = nil; AURAS.target = {}; FireEvent("PLAYER_TARGET_CHANGED")
-- expired buff in the cache is ignored
AURAS.target = { { NP, 0, GetTime() + 1, 66228, nil, 1 } }; FireEvent("UNIT_AURA", "target"); upd(10)
check(reco() ~= "steal" and not IND.__shown, "expired cached buff ignored")
AURAS.target = {}; FireEvent("UNIT_AURA", "target")

-- focus only: hint in the info line, no recommendation
FOCUS = { name = "Cult Fanatic" }; AURAS.focus = { aura(VM, 70674, true) }; FireEvent("PLAYER_FOCUS_CHANGED"); upd()
check(reco() ~= "steal" and info():find(VM, 1, true) and info():find(de and "Fokus" or "Focus", 1, true), "focus only: hint (" .. info() .. ")")
check(info():find("Shift", 1, true), "focus hint names Shift + mouseover: " .. info())
OUT[#OUT + 1] = "STEAL FOCUS " .. info()
mark = #OUT; IND.__scripts.OnEnter(IND)
check(table.concat(OUT, "\n", mark + 1):find(VM, 1, true), "tooltip lists the focus buff")
-- target and focus both: the target wins
setTarget({ aura(NP, 66228, true) }); upd()
check(reco() == "steal" and info():find(NP, 1, true), "target buff before the focus hint")
setTarget({})
FOCUS = nil; AURAS.focus = nil; FireEvent("PLAYER_FOCUS_CHANGED"); upd()
check(not info():find(VM, 1, true), "focus cleared: hint gone")

-- feature off: nothing at all
Slash("raub aus")
setTarget({ aura(NP, 66228, true) }); upd()
check(not MH.db.profile.spellsteal and reco() ~= "steal" and not IND.__shown and st("steal") == "normal", "/mh raub aus: nothing")
RANGE.target = 0; upd(); check(st("steal") == "normal" and not info():find(NP, 1, true), "off: no out-of-range hint either"); RANGE.target = nil
Slash("steal on"); upd()
check(MH.db.profile.spellsteal and reco() == "steal", "/mh steal on: rescans at once")

-- Arcane: same hook (switch out of combat), emergencies first
INCOMBAT = false; FireEvent("PLAYER_REGEN_ENABLED")
Slash("rota arkan"); upd()
check(shown("steal") and shown("ab") and KR.__w == 8 + 13 * 53 + 95, "Arcane set has the steal button, bar width " .. tostring(KR.__w))
INCOMBAT = true; FireEvent("PLAYER_REGEN_DISABLED")
for _, n in ipairs({ GetSpellInfo(12042), GetSpellInfo(12043), GetSpellInfo(55342), GetSpellInfo(12472), GetSpellInfo(12051) }) do COOLDOWNS[n] = 100 end
upd()
check(reco() == "steal" and st("steal") == "urgent", "Arcane: listed buff -> urgent steal (" .. tostring(reco()) .. ")")
AURAS.player = { { GetSpellInfo(45438), 0, nil, 45438 } }; upd()
check(reco() == "ice", "Arcane: emergency beats Spellsteal"); AURAS.player = {}
RANGE.target = 0; upd()
check(reco() ~= "steal" and st("steal") == "prep", "Arcane: out of range -> prep, Arcane goes on (" .. tostring(reco()) .. ")")
RANGE.target = nil
setTarget({}); upd(); check(reco() ~= "steal", "Arcane: buff gone")

-- options
local o = LibStub("AceConfigRegistry-3.0"):GetOptionsTable("MageHelper", "dialog", "MyLib-1.0")
local g = o.args.spellsteal
check(g and g.args.spellsteal and g.args.spellstealAll and g.args.help, "options group Spellsteal")
g.set({ "spellsteal", "spellstealAll" }, true); check(MH.db.profile.spellstealAll == true, "spellstealAll via options")
g.set({ "spellsteal", "spellstealAll" }, false)
g.set({ "spellsteal", "spellsteal" }, false); check(MH.db.profile.spellsteal == false, "spellsteal off via options")
g.set({ "spellsteal", "spellsteal" }, true)
Slash("raub"); Slash("help")

check(#ERRORS == errors, "no Lua errors (protected frames untouched in combat)")
INCOMBAT = false; FireEvent("PLAYER_REGEN_ENABLED"); COOLDOWNS = {}
Slash("rota auto")
OUT[#OUT + 1] = "SPELLSTEAL OK"
'''

# Frost rotation: auto mode by talents, button set, Water Elemental, cooldown button (Icy Veins,
# Mirror Image, trinkets, T10 order), gem/Evocation, Deep Freeze on Fingers of Frost or a frozen
# target, Cold Snap, Brain Freeze, movement, switching modes in combat.
FROST = r'''
local KR = MageHelperFrame
local de = GetLocale() == "deDE"
local function upd(n) for i = 1, (n or 3) do Tick(0.15) end end
local function reco() return FRAMES.MageHelperOneButton.currentKey end
local function shown(k) return FRAMES["MageHelperButton_" .. k].__shown end
local function macro(k) return FRAMES["MageHelperButton_" .. k].__attr.macrotext end
local function btnState(k) return FRAMES["MageHelperButton_" .. k].state end
local function info() return KR.info.__text end
local function S(id) return (GetSpellInfo(id)) end
local DF, SNAP, ELE, IV, MI, FBL = S(44572), S(11958), S(31687), S(12472), S(55342), S(42873)
local FOF = { S(74396), 2, nil, 74396 }
local FROZEN = { { S(42917), 0, nil, 42917, "player" } }

INCOMBAT, MOVING, NOTARGET, TARGETNAME, TARGET_HP, PET = false, false, nil, "Dummy", 100, false
AURAS.player, DEBUFFS.player, DEBUFFS.target, BOSSES = {}, {}, {}, {}
EQUIPPED, BAGS = {}, { [0] = { "|Hitem:33312|h[Mana Sapphire]|h" } }
COOLDOWNS, ITEM_COOLDOWNS, SLOT_COOLDOWNS, ITEM_USE, KNOWN = {}, {}, {}, {}, {}
PLAYER_MANA, PLAYER_MANA_MAX = 30000, 30000
Slash("rota auto")
PLAYER_TALENTS = { 0, 0, 0 }; FireEvent("PLAYER_TALENT_UPDATE"); upd()
check(shown("lb") and not shown("fbolt"), "no talents: Fire")
PLAYER_TALENTS = { 18, 0, 53 }; FireEvent("PLAYER_TALENT_UPDATE"); upd()
check(MH.db.profile.rotationMode == "auto", "auto mode")
for _, k in ipairs({ "fbolt", "ilance", "dfreeze", "ffb", "fcd", "csnap", "elem", "gem", "evo", "fb_move", "ice", "invis", "stop" }) do check(shown(k), "Frost button shown: " .. k) end
for _, k in ipairs({ "lb", "pyro", "fireball", "comb", "cd", "ab", "am", "abarr", "ap", "pom", "mirror" }) do check(not shown(k), "Fire/Arcane button hidden: " .. k) end
local m = macro("fcd")
check(m:find("#showtooltip " .. IV, 1, true) and not m:find("/use 13", 1, true) and not m:find("/use 14", 1, true), "cooldown button macro without trinkets: no /use 13/14: " .. m)
EQUIPPED = { [13] = "|Hitem:50353|h[x]|h", [14] = "|Hitem:50365|h[x]|h" }; ITEM_USE[50365] = "Use"
FireEvent("UNIT_INVENTORY_CHANGED", "player"); m = macro("fcd")
check(not m:find("/use 13", 1, true) and m:find("/use 14", 1, true), "passive trinket 13: no /use 13, on-use 14: /use 14: " .. m)
check(m:find("/use 14", 1, true) < m:find("/cast " .. MI, 1, true), "trinket before Mirror Image")
EQUIPPED, ITEM_USE = {}, {}; FireEvent("UNIT_INVENTORY_CHANGED", "player"); m = macro("fcd")
check(not m:find("/use 1[34]"), "trinkets gone: no /use 13/14 again: " .. m)
check(not m:find("/use 10", 1, true) == not MH.db.profile.useGloves, "gloves line follows the gloves option: " .. m)
check(m:find("/cast " .. IV, 1, true) < m:find("/cast " .. MI, 1, true), "without T10: Icy Veins before Mirror Image")

-- Water Elemental whenever no pet is out (also out of combat); out of combat no cooldowns, gem or Evocation
upd(); check(reco() == "elem" and btnState("elem") == "glow", "no pet, out of combat with a target: Water Elemental, not urgent (" .. tostring(reco()) .. ", " .. tostring(btnState("elem")) .. ")")
check(info():find(de and "Vor dem Pull" or "Pre-pull", 1, true), "pre-pull note: " .. info())
NOTARGET = true; upd(); check(reco() ~= "elem" and btnState("elem") == "normal", "no pet, out of combat, no target: no Water Elemental (" .. tostring(reco()) .. ")")
TARGET_FRIENDLY = true; NOTARGET = nil; upd(); check(reco() ~= "elem", "friendly target out of combat: no Water Elemental")
TARGET_FRIENDLY = nil
PET = true; upd(); check(reco() == "fbolt", "pet out, out of combat: Frostbolt (" .. tostring(reco()) .. ")")
PLAYER_MANA = 3000; upd(); check(reco() == "fbolt", "out of combat: no Mana Gem or Evocation (" .. tostring(reco()) .. ")")
PLAYER_MANA = 30000

-- cooldowns only in combat with a target
INCOMBAT = true; FireEvent("PLAYER_REGEN_DISABLED"); NOTARGET = true; upd()
check(reco() ~= "fcd", "in combat without a target: no cooldowns (" .. tostring(reco()) .. ")")
NOTARGET = nil; upd(); check(reco() == "fcd", "in combat with a target: cooldown button")
check(info():find(IV, 1, true), "Icy Veins named: " .. info())
check(not pcall(FRAMES.MageHelperButton_fbolt.Hide, FRAMES.MageHelperButton_fbolt), "stub: secure button Hide() blocked in combat")
COOLDOWNS[IV] = 100; upd(); check(reco() == "fcd" and info():find(MI, 1, true), "Icy Veins on CD: Mirror Image via the button")
COOLDOWNS[MI] = 1.2; upd()   -- only the GCD runs on Mirror Image
check(reco() == "fcd" and btnState("fcd") == "prep", "GCD: stays recommended, not clickable yet (" .. tostring(btnState("fcd")) .. ")")
COOLDOWNS[MI] = 100; upd(); check(reco() == "fbolt", "all cooldowns used: Frostbolt")
-- on-use trinket (a passive one doesn't count)
EQUIPPED[14] = "|Hitem:50353|h[x]|h"; upd(); check(reco() == "fbolt", "passive trinket: no cooldown hint")
EQUIPPED[13] = "|Hitem:50365|h[x]|h"; ITEM_USE[50365] = "Use"; upd()
check(reco() == "fcd" and btnState("fcd") == "urgent", "on-use trinket ready: cooldown button (" .. tostring(btnState("fcd")) .. ")")
SLOT_COOLDOWNS[13] = 60; upd(); check(reco() == "fbolt", "trinket on CD: Frostbolt")
EQUIPPED, SLOT_COOLDOWNS, ITEM_USE = {}, {}, {}
-- T10 4-piece: Mirror Image first; the macro changes only after combat
COOLDOWNS[IV], COOLDOWNS[MI] = nil, nil
EQUIPPED = { [1] = "|Hitem:51281|h[x]|h", [3] = "|Hitem:51155|h[x]|h", [5] = "|Hitem:50278|h[x]|h", [7] = "|Hitem:51282|h[x]|h" }
FireEvent("UNIT_INVENTORY_CHANGED", "player"); upd()
check(reco() == "fcd" and info():find("T10", 1, true), "T10: Mirror Image first (" .. info() .. ")")
check(macro("fcd") == m, "macro unchanged in combat")
INCOMBAT = false; FireEvent("PLAYER_REGEN_ENABLED"); upd(1)
m = macro("fcd")
check(m:find("/cast " .. MI, 1, true) < m:find("/cast " .. IV, 1, true), "T10 after combat: Mirror Image before Icy Veins: " .. m)
INCOMBAT = true; FireEvent("PLAYER_REGEN_DISABLED")
EQUIPPED = {}; FireEvent("UNIT_INVENTORY_CHANGED", "player")
COOLDOWNS[IV], COOLDOWNS[MI] = 100, 100

-- the pet dies in combat: summon again (unless on cooldown)
PET = false; upd(); check(reco() == "elem" and btnState("elem") == "urgent", "pet died in combat: Water Elemental, urgent (" .. tostring(btnState("elem")) .. ")")
NOTARGET = true; upd(); check(reco() == "elem" and btnState("elem") == "urgent", "in combat without a target: Water Elemental still urgent"); NOTARGET = nil
COOLDOWNS[ELE] = 150; upd(); check(reco() == "fbolt", "Water Elemental on CD: Frostbolt")
PET, COOLDOWNS[ELE] = true, nil

-- Mana Gem when the missing mana >= its yield
PLAYER_MANA = 27000; upd(); check(reco() == "fbolt", "3000 missing: no gem yet")
PLAYER_MANA = 26000; upd(); check(reco() == "gem", "4000 missing: Mana Gem")
ITEM_CHARGES[33312] = 0; upd(); check(reco() ~= "gem", "Frost: gem with 0 charges left: not recommended (" .. tostring(reco()) .. ")")
ITEM_CHARGES[33312] = nil
ITEM_COOLDOWNS[33312] = 60; PLAYER_MANA = 30000

-- Deep Freeze on Fingers of Frost (both aura IDs) or a frozen target
AURAS.player = { FOF }; upd()
check(reco() == "dfreeze", "Fingers of Frost: Deep Freeze (" .. tostring(reco()) .. ")")
check(info():find("FoF: |cff33ff332", 1, true), "info line shows 2 FoF charges: " .. info())
COOLDOWNS[DF] = 1.2; upd(); check(reco() == "dfreeze", "Deep Freeze stays recommended during the GCD")
COOLDOWNS[DF] = nil
AURAS.player = { { S(44544), 0, nil, 44544 } }; upd(); check(reco() == "dfreeze", "Fingers of Frost (44544): Deep Freeze")
AURAS.player = {}; DEBUFFS.target = FROZEN; upd(); check(reco() == "dfreeze", "frozen target: Deep Freeze")
DEBUFFS.target = {}; upd(); check(reco() == "fbolt", "nothing up: Frostbolt")

-- SimC 3.3 order: Deep Freeze > Frostbolt with FoF/frozen (not moving) > Cold Snap > Frostfire Bolt
local BF = { S(57761), 0, nil, 57761 }
AURAS.player = { FOF, BF }; COOLDOWNS[DF] = 28; upd()
check(reco() == "fbolt" and info():find(S(74396), 1, true), "FoF + Brain Freeze, Deep Freeze on CD: Frostbolt first (" .. tostring(reco()) .. ", " .. info() .. ")")
AURAS.player = { BF }; DEBUFFS.target = FROZEN; upd(); check(reco() == "fbolt", "frozen + Brain Freeze: Frostbolt first (" .. tostring(reco()) .. ")")
DEBUFFS.target = {}
-- Cold Snap when Deep Freeze has more than 15 s left and Icy Veins is on cooldown, not active
AURAS.player = {}; upd()
check(reco() == "csnap", "Deep Freeze 28 s, Icy Veins on CD: Cold Snap (" .. tostring(reco()) .. ")")
check(info():find("DF 28", 1, true), "info line: Deep Freeze cooldown: " .. info())
AURAS.player = { BF }; upd(); check(reco() == "csnap", "Cold Snap above Brain Freeze")
AURAS.player = { { IV, 0, nil, 12472 } }; upd(); check(reco() ~= "csnap", "Icy Veins active: no Cold Snap (" .. tostring(reco()) .. ")")
AURAS.player = {}; COOLDOWNS[IV] = nil; COOLDOWNS[MI] = 100; upd()
check(reco() == "fcd", "Icy Veins ready: cooldown button, not Cold Snap (" .. tostring(reco()) .. ")")
KNOWN[12472] = false; upd(); check(reco() ~= "csnap", "Icy Veins not known: no Cold Snap (" .. tostring(reco()) .. ")")
KNOWN[12472] = nil; COOLDOWNS[IV] = 100; upd(); check(reco() == "csnap", "Icy Veins on CD again: Cold Snap")
KNOWN[11958] = false; upd(); check(reco() == "fbolt", "Cold Snap not talented: Frostbolt")
KNOWN[11958] = nil
COOLDOWNS[DF] = 12; upd(); check(reco() == "fbolt", "Deep Freeze 12 s CD: no Cold Snap")
COOLDOWNS[SNAP], COOLDOWNS[DF] = 400, 28; upd(); check(reco() == "fbolt", "Cold Snap on CD: Frostbolt")
AURAS.player = {}

-- Brain Freeze: Frostfire Bolt
AURAS.player = { { S(57761), 0, nil, 57761 } }; upd()
check(reco() == "ffb" and info():find("BF!", 1, true), "Brain Freeze: Frostfire Bolt (" .. tostring(reco()) .. ")")
check(macro("ffb"):find("/cast " .. S(47610), 1, true), "Brain Freeze button casts Frostfire Bolt: " .. macro("ffb"))
local FBALL = S(42833)
KNOWN[47610] = false; upd()
check(reco() == "ffb" and info():find(FBALL, 1, true), "no Frostfire Bolt: Fireball on Brain Freeze (" .. info() .. ")")
INCOMBAT = false; FireEvent("PLAYER_REGEN_ENABLED"); upd()
check(macro("ffb"):find("/cast " .. FBALL, 1, true) and not macro("ffb"):find(S(47610), 1, true), "button falls back to Fireball: " .. macro("ffb"))
KNOWN[47610] = nil; FireEvent("PLAYER_TALENT_UPDATE")
check(macro("ffb"):find("/cast " .. S(47610), 1, true), "Frostfire Bolt known again: button casts it: " .. macro("ffb"))
INCOMBAT = true; FireEvent("PLAYER_REGEN_DISABLED"); upd()
MOVING = true; upd(); check(reco() == "ffb", "Brain Freeze while moving: Frostfire Bolt (instant)")

-- moving: Ice Lance with FoF or frozen, else Fire Blast, else Ice Lance
AURAS.player = { FOF }; upd(); check(reco() == "ilance", "moving with FoF: Ice Lance")
AURAS.player = {}; upd(); check(reco() == "fb_move", "moving without FoF: Fire Blast")
DEBUFFS.target = FROZEN; upd(); check(reco() == "ilance", "moving, frozen target: Ice Lance")
DEBUFFS.target = {}; COOLDOWNS[FBL] = 5; upd(); check(reco() == "ilance", "moving, Fire Blast on CD: Ice Lance")
MOVING, COOLDOWNS[FBL] = false, nil

-- Evocation in combat below 30% mana
PLAYER_MANA = 6000; upd(); check(reco() == "evo", "20% mana: Evocation")
INCOMBAT = false; upd(); check(reco() == "fbolt", "out of combat: no Evocation")
INCOMBAT = true; PLAYER_MANA = 30000; AURAS.player = { FOF, { S(57761), 0, nil, 57761 } }; upd()
OUT[#OUT + 1] = "FROST INFO " .. info()
AURAS.player = {}
Slash("debug on"); upd(); OUT[#OUT + 1] = "FROST DEBUG " .. KR.debugInfo.__text; Slash("debug off")

-- fight report: no Fireball rating
local mark = #OUT
Slash("report")
local report = table.concat(OUT, "\n", mark + 1)
check(report:find(de and "Frost-Rota: keine Feuerball-Wertung" or "Frost rotation: no Fireball rating", 1, true), "Frost fight report: " .. report)

-- switching the rotation in combat waits for the end of the fight; Fire and Arcane unchanged
Slash("rota feuer")
check(MH.db.profile.rotationMode == "fire" and shown("fbolt") and not shown("lb"), "in combat the Frost buttons stay")
INCOMBAT = false; FireEvent("PLAYER_REGEN_ENABLED"); upd()
check(shown("lb") and not shown("fbolt") and not shown("fcd"), "after combat: Fire buttons")
AURAS.player = { { "Hot Streak", 0, nil, 48108 } }; upd(); check(reco() == "pyro", "Fire rotation: Hot Streak -> Pyroblast"); AURAS.player = {}
Slash("rota frost"); check(MH.db.profile.rotationMode == "frost" and shown("fbolt") and not shown("lb"), "/mh rota frost")
Slash("rota arkan"); upd(); check(shown("ab") and not shown("fbolt") and (reco() == "ab" or reco() == "am"), "/mh rota arkan")
Slash("rota auto"); check(shown("fbolt"), "auto with Frost talents")
local o = LibStub("AceConfigRegistry-3.0"):GetOptionsTable("MageHelper", "dialog", "MyLib-1.0")
check(o.args.rotation.args.rotationMode.values().frost ~= nil, "rotation mode value frost")
o.args.rotation.args.rotationMode.set({ "rotation", "rotationMode" }, "fire"); check(shown("lb"), "options: Fire")
o.args.rotation.args.rotationMode.set({ "rotation", "rotationMode" }, "frost"); check(shown("fbolt"), "options: Frost")
-- Spellsteal hook in the Frost rotation
Slash("rota frost"); INCOMBAT = true; FireEvent("PLAYER_REGEN_DISABLED"); PET = true
COOLDOWNS[IV], COOLDOWNS[MI] = 100, 100
check(shown("steal"), "Frost set has the steal button")
AURAS.target = { { (de and "Netherkraft" or "Nether Power"), 1, GetTime() + 600, 67108, nil, 1 } }; FireEvent("UNIT_AURA", "target"); upd()
check(reco() == "steal", "Frost: listed stealable buff -> Spellsteal (" .. tostring(reco()) .. ")")
RANGE.target = 0; upd()
check(reco() ~= "steal" and info():find(de and "außer Reichweite" or "out of range", 1, true), "Frost: out-of-range hint in the info line: " .. info())
RANGE.target = nil; AURAS.target = {}; FireEvent("UNIT_AURA", "target")
INCOMBAT = false; FireEvent("PLAYER_REGEN_ENABLED")
Slash("rota")
Slash("rota auto")
PLAYER_TALENTS, PET, COOLDOWNS, ITEM_COOLDOWNS, DEBUFFS.target = nil, false, {}, {}, {}
OUT[#OUT + 1] = "FROST OK"
'''

# Professor Putricide Tear Gas (normal only): Invisibility just above 80%/35% (cfg.putricideInvisLead),
# hold while invisible, cancel after the gas lands, re-engage countdown (yells, drinks), threat check
# -> Ice Block or stop casting, ends on 71615 removed / 71620 / timeout / combat end; cast start is a
# late fallback (combat log in the 3.3.5 layout or UnitCastingInfo); heroic and other casters ignored.
TEARGAS = r"""
local KR = MageHelperFrame
local de = GetLocale() == "deDE"
local function upd(n) for i = 1, (n or 2) do Tick(0.15) end end
local function reco() return FRAMES.MageHelperOneButton.currentKey end
local function st(k) return FRAMES["MageHelperButton_" .. k].state end
local function info() return KR.info.__text end
local function S(id) return (GetSpellInfo(id)) end
local function has(s, ger, eng) return s:find(de and ger or eng, 1, true) ~= nil end
local function CL(...) FireEvent("COMBAT_LOG_EVENT_UNFILTERED", 0, ...) end
local INVIS, ICE, GAS = S(66), S(45438), S(71617)
local PG, PN = "0xF130008F46000123", "Professor Putricide"
local RAIDG = "0x0000000000000042"
local errors = #ERRORS
local function invisible(on) AURAS.player = on and { { INVIS, 0, GetTime() + 20, 32612 } } or {} end
local function fight() INCOMBAT = false; FireEvent("PLAYER_REGEN_ENABLED"); INCOMBAT = true; FireEvent("PLAYER_REGEN_DISABLED") end
local function hp(v) BOSSES.boss1.hp = v; upd() end
local function gasCast(src) CL("SPELL_CAST_START", src or PG, PN, 0xa48, "", nil, 0x80000000, 71617, GAS, 8) end
local function show(tag) OUT[#OUT + 1] = "TEARGAS " .. tag .. " " .. info() end

INCOMBAT, MOVING, NOTARGET, FOCUS, TARGET_HP, PET = false, false, nil, nil, 100, true
AURAS.player, DEBUFFS.player, DEBUFFS.target, AURAS.target, COOLDOWNS, ITEM_COOLDOWNS, CASTING, THREAT = {}, {}, {}, {}, {}, {}, {}, {}
INSTANCE = { difficulty = 1 }
BOSSES = { boss1 = { name = PN, hp = 90, guid = PG } }
TARGETNAME, TARGETGUID = PN, PG
check(MH.db.profile.putricideInvis == true and MH.db.profile.putricideInvisLead == 1.0, "Tear Gas defaults: on, lead 1%")

-- every rotation: pre-warning (blue, no override) and the trigger at threshold + lead (urgent)
for _, mode in ipairs({ "feuer", "arkan", "frost" }) do
  INCOMBAT = false; FireEvent("PLAYER_REGEN_ENABLED"); Slash("rota " .. mode); INCOMBAT = true; FireEvent("PLAYER_REGEN_DISABLED")
  hp(90); check(reco() ~= "invis" and st("invis") == "normal", mode .. ": 90% nothing")
  hp(81.6); check(reco() ~= "invis" and st("invis") == "prep" and has(info(), "Gleich Tränengas", "Tear Gas soon"), mode .. ": 81.6% pre-warning, blue: " .. info())
  hp(80.9); check(reco() == "invis" and st("invis") == "urgent", mode .. ": 80.9% urgent Invisibility (" .. tostring(reco()) .. ")")
  hp(35.8); check(reco() == "invis" and st("invis") == "urgent", mode .. ": 35.8% urgent Invisibility")
  hp(79); check(reco() ~= "invis", mode .. ": below 80% without a cast: nothing")
  if not de then check(not info():find("[\195]") and not info():find("Seuchenmord", 1, true), "English info line: " .. info()) end
end
show("TRIGGER")

-- full transition in Fire
fight(); INCOMBAT = false; Slash("rota feuer"); INCOMBAT = true
hp(80.9); check(reco() == "invis", "Fire: trigger")
invisible(true); COOLDOWNS[INVIS] = 180; upd()
check(reco() == nil and st("invis") == "normal" and has(info(), "Unsichtbar noch 20 s - Seuchenmord 80.9%", "Invisible for 20 s - Putricide 80.9%"), "invisible: wait, time left and health: " .. info())
show("WAIT")
gasCast(); upd()
check(reco() == nil, "cast started, still invisible: keep waiting")
upd(16) -- 2.4 s later the gas has landed
check(reco() == "invis" and st("invis") == "urgent" and has(info(), "greift in ~", "re-engages in ~"), "gas landed, invisible: cancel Invisibility (" .. tostring(reco()) .. ") " .. info())
check(FRAMES.MageHelperButton_invis.__attr.macrotext:find("/cancelaura " .. INVIS, 1, true), "invis macro cancels the aura first")
show("CANCEL")
invisible(false); CL("SPELL_AURA_APPLIED", PG, PN, 0xa48, RAIDG, "Anya", 0x514, 71615, GAS, 8, "DEBUFF"); upd()
check(reco() ~= "invis" and reco() ~= nil and has(info(), "Vorsicht Bedrohung", "watch your threat"), "cancelled: rotation + threat hint (" .. tostring(reco()) .. ") " .. info())
CL("SPELL_CAST_START", PG, PN, 0xa48, "", nil, 0x80000000, 71621, "Create Concoction", 8); upd()
check(has(info(), "greift in 9 s", "re-engages in 9 s"), "Create Concoction: re-engage in 4 + 5.5 s: " .. info())
FireEvent("CHAT_MSG_MONSTER_YELL", de and "Hm, ich spüre gar nichts. Nanu?! Wo kommen die denn her?" or "Hrm, I don't feel a thing. Wha?! Where'd those come from?", PN); upd()
check(has(info(), "greift in 5 s", "re-engages in 5 s"), "yell 1: re-engage in 5.5 s: " .. info())
show("COUNTDOWN")
upd(15) -- 2.25 s later: 3 s left, low threat
check(reco() ~= "ice" and reco() ~= nil, "low threat before re-engage: rotation")
upd(8) -- below 2 s left: threat check
THREAT.boss1 = { true, 3, 100, 100 }; upd()
check(reco() == "ice" and st("ice") == "urgent", "tanking Putricide before his re-engage: urgent Ice Block (" .. tostring(reco()) .. ")")
COOLDOWNS[ICE] = 200; upd()
check(reco() == nil and has(info(), "Stop casten", "stop casting"), "Ice Block on cooldown: stop-casting warning: " .. info())
show("THREAT")
THREAT.boss1 = { false, 1, 92, 92 }; COOLDOWNS[ICE] = nil; upd()
check(reco() == "ice", "92% scaled threat: Ice Block")
BOSSES.boss1.hp = 79.5; THREAT.boss1 = nil; CL("SPELL_CAST_SUCCESS", PG, PN, 0xa48, "", nil, 0x80000000, 71620, GAS, 8); upd()
check(has(info(), "greift wieder an", "re-engages"), "71620: re-engaged, threat check still running: " .. info())
upd(22)
check(not has(info(), "Seuchenmord", "Putricide"), "3 s after the re-engage: helper done: " .. info())
hp(80.8); check(reco() ~= "invis", "80% trigger does not fire again")
hp(35.9); check(reco() ~= "invis" and has(info(), "Gleich", "soon"), "35%: Invisibility still on cooldown, only a hint")
COOLDOWNS[INVIS] = nil; upd(); check(reco() == "invis", "35% trigger still pending")
COOLDOWNS[INVIS] = 180

-- 71615 removed ends the transition (Guzzle Potions / yell 2 timings)
invisible(true); upd(); gasCast(); upd(18); invisible(false); upd()
CL("SPELL_CAST_START", PG, PN, 0xa48, "", nil, 0x80000000, 71893, "Guzzle Potions", 8); upd()
check(has(info(), "greift in 12 s", "re-engages in 12 s"), "Guzzle Potions: 4 + 8.5 s: " .. info())
FireEvent("CHAT_MSG_MONSTER_YELL", de and "Schmeckt nach... Kirsche! OH! Verzeihung!" or "Tastes like... Cherry! OH! Excuse me!", PN); upd()
check(has(info(), "greift in 8 s", "re-engages in 8 s"), "yell 2: 8.5 s: " .. info())
BOSSES.boss1.hp = 34.5; CL("SPELL_AURA_REMOVED", PG, PN, 0xa48, RAIDG, "Anya", 0x514, 71615, GAS, 8, "DEBUFF"); upd(22)
check(not has(info(), "Seuchenmord", "Putricide"), "71615 removed: done after the threat check: " .. info())

-- lead setting: slash and options
fight(); COOLDOWNS = {}
local before = #OUT
Slash(de and "tr\195\164nengas 3" or "teargas 3")
check(MH.db.profile.putricideInvisLead == 3 and OUT[before + 1]:find("3.0", 1, true), "/mh tränengas 3 sets the lead: " .. tostring(OUT[before + 1]))
hp(83.2); check(reco() ~= "invis" and st("invis") == "prep", "lead 3: 83.2% only pre-warning")
hp(82.9); check(reco() == "invis", "lead 3: 82.9% urgent")
Slash("traenengas 9"); check(MH.db.profile.putricideInvisLead == 5, "lead clamped to 5")
local o = LibStub("AceConfigRegistry-3.0"):GetOptionsTable("MageHelper", "dialog", "MyLib-1.0")
local b = o.args.bosses.args
check(b.putricideInvisLead.min == 0.5 and b.putricideInvisLead.max == 5, "options: lead slider 0.5-5")
o.args.bosses.set({ "bosses", "putricideInvisLead" }, 0.5); fight()
check(MH.db.profile.putricideInvisLead == 0.5, "options: lead 0.5")
hp(80.6); check(reco() ~= "invis", "lead 0.5: 80.6% not yet")
hp(80.4); check(reco() == "invis", "lead 0.5: 80.4% urgent")
b.putricideInvis.set({ "bosses", "putricideInvis" }, false); upd()
check(MH.db.profile.putricideInvis == false and reco() ~= "invis" and st("invis") == "normal", "options: off -> nothing")
Slash("teargas on"); Slash("teargas 1"); upd(); check(reco() == "invis", "/mh teargas on")
Slash("teargas off"); upd(); check(reco() ~= "invis", "/mh teargas off -> nothing")
gasCast(); upd(); check(reco() ~= "invis", "off: cast start ignored")
Slash("teargas on"); fight()

-- heroic and other instances: off
INSTANCE.difficulty = 3; hp(80.9); check(reco() ~= "invis" and st("invis") == "normal", "10 heroic: nothing")
INSTANCE.difficulty = 4; gasCast(); upd(); check(reco() ~= "invis", "25 heroic: cast ignored")
INSTANCE = { difficulty = 2, dynamic = 1 }; hp(80.9); check(reco() ~= "invis", "heroic reported as 25 + dynamic flag: nothing")
INSTANCE = nil; hp(80.9); check(reco() ~= "invis", "outside a raid: nothing")
INSTANCE = { difficulty = 2 }; hp(80.9); check(reco() == "invis", "25 normal: trigger")

-- fallback on the cast start (window missed)
fight(); hp(70)
gasCast("0xF130001234000001"); upd(); check(reco() ~= "invis", "71617 from another NPC: ignored")
BOSSES.boss1.guid = "0xF130001234000001"; TARGETGUID = "GUID-x"; hp(80.9); check(reco() ~= "invis", "not Putricide: no trigger")
BOSSES.boss1.guid = PG; TARGETGUID = PG; hp(70)
gasCast(); upd(); check(reco() == "invis" and st("invis") == "urgent", "cast start fallback: urgent Invisibility")
show("FALLBACK")
upd(22); check(reco() ~= "invis", "3 s after the cast: too late, nothing")
DEBUFFS.player = { { GAS, 0, GetTime() + 18, 71615 } }; upd(); check(reco() ~= "invis" and reco() ~= nil, "stunned anyway: no Tear Gas recommendation")
DEBUFFS.player = {}; fight()
CASTING.boss1 = { GAS, GetTime() * 1000, GetTime() * 1000 + 2500 }; upd()
check(reco() == "invis", "UnitCastingInfo fallback (name from GetSpellInfo)")
CASTING.boss1 = nil
COOLDOWNS[INVIS] = 100; fight(); gasCast(); upd(); check(reco() ~= "invis", "Invisibility on cooldown: no fallback")
upd(300); check(not has(info(), "Seuchenmord", "Putricide"), "timeout ends the transition")
COOLDOWNS = {}; hp(80.9); invisible(true); upd(); check(reco() == nil, "invisible in the window: wait")
INCOMBAT = false; FireEvent("PLAYER_REGEN_ENABLED"); invisible(false); hp(70)
check(reco() ~= nil, "combat end: back to the rotation")

check(#ERRORS == errors, "no Lua errors (protected frames untouched in combat)")
INCOMBAT = false; FireEvent("PLAYER_REGEN_ENABLED")
BOSSES, TARGETNAME, TARGETGUID, INSTANCE, THREAT, CASTING, AURAS.player, DEBUFFS.player, COOLDOWNS, PET = {}, nil, nil, nil, {}, {}, {}, {}, {}, false
Slash("rota auto")
OUT[#OUT + 1] = "TEARGAS OK"
"""

GERMAN = re.compile(r"[äöüßÄÖÜ]|\b(Klick|Linksklick|Rechtsklick|gesetzt|gespeichert|Befehle|Ziel|Hose|Eisblock|Feuerball|Kampf|Lauf|keine?|nach|anzeigen|AUS|AN)\b")

version, files = toc_files()
failed = False
for loc in ("deDE", "enUS"):
    lua = lua51.LuaRuntime(unpack_returned_tuples=True)
    g = lua.globals()
    g.LOCALE, g.ADDON_VERSION = loc, version
    lua.execute(STUB)
    # SavedVariables as the client provides them before ADDON_LOADED
    legacy = lua.execute(LEGACY)
    if loc == "deDE": g.MageHelperLegacyDB = legacy
    else: g.MageHelperDB = legacy  # variant: per-character file was not renamed
    for f in files:
        g.LoadAddonFile(open(f, encoding="utf-8-sig").read(), os.path.relpath(f, ROOT), "MageHelper")
    g.FireEvent("ADDON_LOADED", "MageHelper")
    g.LOGGEDIN = True
    g.FireEvent("PLAYER_LOGIN")
    g.FireEvent("PLAYER_ENTERING_WORLD")
    try:
        for name, part in (("t10login", T10LOGIN), ("migration", MIGRATION), ("main", SCRIPT), ("combatlog", COMBATLOG), ("options", OPTIONS), ("picker", PICKER), ("t9", T9), ("themes", THEMES), ("flask", FLASK), ("arcane", ARCANE), ("spellsteal", SPELLSTEAL), ("frost", FROST), ("teargas", TEARGAS)):
            lua.execute(COMMON + part)
    except Exception as e:
        failed = True
        print(f"!!!!! {loc} scenario '{name}' failed: {e}")
    out = list(g.OUT.values())
    for l in out:
        if l.startswith(("T10LOGIN", "ROWS", "LABEL", "STATUS", "PICKER", "MIGRATION", "COMBATLOG", "OPTIONS", "T9", "THEMES", "FLASK", "ARCANE", "STEAL", "SPELLSTEAL", "FROST", "TEARGAS", "|cffff7d0aMageHelper v")): print("  " + l)
    errors = list(g.ERRORS.values())
    for e in errors: print("  LUA ERROR:", e)
    failed = failed or bool(errors)
    print(f"===== {loc}: {len(files)} files, {len(out)} output lines, {len(errors)} Lua errors, unknown globals: {sorted(g.MISSING.keys())}")
    if loc == "enUS":
        bad = [l for l in out if GERMAN.search(l)]
        print("  German-looking lines in English output:", len(bad))
        for l in bad: print("    ", l)
    if "-v" in sys.argv:
        frames = g.FRAMES
        for k in sorted(k for k in frames.keys() if isinstance(k, str)):
            mt = frames[k]["__attr"]["macrotext"]
            if mt: print("  MACRO", k, "->", mt.replace("\n", " | "))
        for l in out: print("   ", l)
sys.exit(1 if failed else 0)
