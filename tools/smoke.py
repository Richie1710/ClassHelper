# Smoke test: loads ClassHelper (TOC order, incl. embedded Ace3) in Lua 5.1 against tools/wowstub.lua,
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
    for line in open(os.path.join(ROOT, "ClassHelper.toc"), encoding="utf-8"):
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
MH = LibStub("AceAddon-3.0"):GetAddon("ClassHelper")
function check(cond, msg) if not cond then error("CHECK FAILED: " .. msg, 2) end end
function Slash(cmd) SlashCmdList.ACECONSOLE_CH(cmd) end
'''

# Legacy settings were taken over (variant: ClassHelperLegacyDB for deDE, flat ClassHelperDB for enUS).
MIGRATION = r'''
local p, c = MH.db.profile, MH.db.char
check(ClassHelperLegacyDB == nil, "legacy table dropped")
check(ClassHelperDB.profiles ~= nil, "ClassHelperDB is an AceDB database")
check(p.combustionLB == 7 and p.x == 50 and p.iceBlockLead == 1.5, "profile settings taken over")
check(c.focusMagicTarget == "Anya" and c.focusMagicPartner == "Anya", "FM target taken over and used as partner")
check(c.moltenT9Legs == nil and c.moltenStep == nil and p.moltenT9Legs == nil, "old leg-name settings are dropped")
check(type(c.moltenSwap) == "table" and p.moltenT9 == true, "T9 swap defaults")
check(c.analyzer.bossFights[1].name == "Lord Mark'gar", "analyzer data per character")
check(MH.db:GetCurrentProfile() == "Kahuchan - Rising-Gods", "own profile per character: " .. MH.db:GetCurrentProfile())
check(SlashCmdList.ACECONSOLE_CH and SlashCmdList.ACECONSOLE_CLASSHELPER and SlashCmdList.ACECONSOLE_MH and SlashCmdList.ACECONSOLE_MAGEHELPER, "/ch, /classhelper and the old /mh, /magehelper are registered")
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
check(OPTIONS_OPENED ~= nil, "/ch config opens the options panel")
for _, n in ipairs({"ClassHelperOneButton", "ClassHelperMinimapButton", "ClassHelperBuffMinimapButton", "ClassHelperAnalyzerMinimapButton", "ClassHelperBuff_FMSet", "ClassHelperBuff_armor", "ClassHelperBuff_brilliance", "ClassHelperBuff_fmin", "ClassHelperBuff_fmout", "ClassHelperBuff_flask", "ClassHelperBuff_potion"}) do
  local f = FRAMES[n]; if f and f.__scripts.OnEnter then f.__scripts.OnEnter(f) end
end
FRAMES.ClassHelperOneButton.__scripts.OnClick(FRAMES.ClassHelperOneButton)
FRAMES.ClassHelperAnalyzerMinimapButton.__scripts.OnClick(FRAMES.ClassHelperAnalyzerMinimapButton, "RightButton")
upd()
check(MH.db.profile.combustionLB == 9, "slash commands write into the profile")
'''

# Combat log in the 3.3.5 layout (no hideCaster, no raid flags):
#   timestamp, event, sourceGUID, sourceName, sourceFlags, destGUID, destName, destFlags, <event params>
COMBATLOG = r'''
local KR = ClassHelperFrame
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
local o = LibStub("AceConfigRegistry-3.0"):GetOptionsTable("ClassHelper", "dialog", "MyLib-1.0")
check(type(o) == "table", "options table registered and valid")
local KR = ClassHelperFrame
o.args.rotation.set({ "rotation", "combustionLB" }, 8)
check(MH.db.profile.combustionLB == 8, "range option writes profile")
o.args.general.args.shown.set({ "general", "shown" }, false)
check(not KR.__shown and MH.db.profile.shown == false, "hide bar via options")
o.args.general.args.shown.set({ "general", "shown" }, true)
check(KR.__shown, "show bar via options")
o.args.rotation.args.useGloves.set({ "rotation", "useGloves" }, false)
check(not FRAMES.ClassHelperButton_fireball.__attr.macrotext:find("/use 10", 1, true), "gloves off rebuilds macros")
o.args.rotation.args.useGloves.set({ "rotation", "useGloves" }, true)
check(FRAMES.ClassHelperButton_fireball.__attr.macrotext:find("/use 10", 1, true), "gloves on rebuilds macros")
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
if FRAMES.ClassHelperFMPicker then FRAMES.ClassHelperFMPicker:Hide() end -- the main scenario may have opened it
Slash("fm")
local P = FRAMES.ClassHelperFMPicker
check(P and P.__shown, "picker opens with /ch fm")
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
setFilter("ClassHelperFMFilterHealers", true); dump("healers")
-- Bheal healer; Ehpala/Gsham unknown (shown as Healer?); Cshadow is shadow; Dresto already has FM
check(shownNames() == "Bheal,Ehpala,Gsham", "healers without FM: " .. shownNames())
setFilter("ClassHelperFMFilterHealers", false); setFilter("ClassHelperFMFilterMages", true); dump("mages")
check(shownNames() == "Anya", "only mages: " .. shownNames())
setFilter("ClassHelperFMFilterMages", false)

local C = MH.db.char
local function rowFor(name) for _, r in ipairs(P.rows) do if r.__shown and r.entryName == name then return r end end end
local function fmMacro() return FRAMES.ClassHelperBuff_fmout.__attr.macrotext end
rowFor("Anya").partnerButton.__scripts.OnClick()
check(C.focusMagicPartner == "Anya" and fmMacro():find("/targetexact Anya", 1, true), "partner Anya set and used by FM OUT")
rowFor("Bheal").targetButton.__scripts.OnClick()
check(C.focusMagicTarget == "Bheal" and C.focusMagicPartner == "Anya", "temporary target keeps partner")
check(fmMacro():find("/targetexact Bheal", 1, true), "FM OUT now targets Bheal")
OUT[#OUT + 1] = "LABEL " .. FRAMES.ClassHelperBuffBar.fmTargetText.__text
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
local B = FRAMES.ClassHelperBuff_armor
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
local KR = ClassHelperFrame
local function rgb(t) return string.format("%.2f,%.2f,%.2f", t[1], t[2], t[3]) end
check(MH.db.profile.theme == "standard" and rgb(KR.bg.__rgba) == "0.00,0.00,0.00" and KR.bg.__rgba[4] == 0.35, "standard look unchanged")
check(not KR.themeStripe.__shown, "no stripe in standard")
Slash("theme rosa")
check(MH.db.profile.theme == "pink", "/ch theme rosa")
check(rgb(KR.bg.__rgba) == "0.13,0.03,0.10" and KR.bg.__rgba[4] == 0.55, "bar background pink, more opaque")
check(KR.themeStripe.__shown and rgb(KR.themeStripe.__vc) == "1.00,0.42,0.74", "pink accent stripe")
check(rgb(FRAMES.ClassHelperBuffBar.title.__tc) == "1.00,0.62,0.86", "buff bar title pink")
check(rgb(FRAMES.ClassHelperBuff_FMSet.bg.__vc) == "0.58,0.10,0.40", "MF SET button pink")
check(rgb(FRAMES.ClassHelperAnalyzerWindow.bg.__rgba) == "0.13,0.03,0.10" and FRAMES.ClassHelperAnalyzerWindow.bg.__rgba[4] == 0.78, "analyzer window keeps its alpha")
Tick(0.15)
check(rgb(FRAMES.ClassHelperButton_pyro.text.__tc) == "1.00,0.84,0.94", "button labels use theme text color")
-- signal colors are independent of the theme
local s = FRAMES.ClassHelperBuff_flask.status.__vc
Slash("theme red"); Tick(0.15)
check(rgb(FRAMES.ClassHelperBuff_flask.status.__vc) == rgb(s), "signal color unchanged by theme")
check(rgb(KR.themeStripe.__vc) == "0.80,0.24,0.38", "red theme uses the wine accent")
local o = LibStub("AceConfigRegistry-3.0"):GetOptionsTable("ClassHelper", "dialog", "MyLib-1.0")
o.args.general.args.theme.set({ "general", "theme" }, "blue")
check(rgb(KR.bg.__rgba) == "0.02,0.06,0.16", "theme via options")
Slash("fm"); local P = FRAMES.ClassHelperFMPicker
check(rgb(P.bg.__rgba) == "0.02,0.06,0.16" and rgb(P.title.__tc) == "0.55,0.80,1.00", "picker created later gets the theme")
P:Hide()
MH.db:SetProfile("Themes"); check(rgb(KR.bg.__rgba) == "0.00,0.00,0.00", "profile switch applies its theme")
Slash("theme bogus")
OUT[#OUT + 1] = "THEMES OK"
'''

# Flask choice: auto by class/spec, fixed flask, any flask; matched by buff ID.
FLASK = r'''
local F = FRAMES.ClassHelperBuff_flask
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
local o = LibStub("AceConfigRegistry-3.0"):GetOptionsTable("ClassHelper", "dialog", "MyLib-1.0")
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
local function reco() return FRAMES.ClassHelperOneButton.currentKey end
PLAYER_TALENTS = { 57, 3, 11 }; FireEvent("PLAYER_TALENT_UPDATE")
INCOMBAT, TARGETNAME, EQUIPPED = true, "Dummy", {}
Tick(0.15); Tick(0.15)
check(reco() == "pom", "login: no T10 pieces readable yet (" .. tostring(reco()) .. ")")
EQUIPPED = { [1] = "|Hitem:51281|h[x]|h", [3] = "|Hitem:51155|h[x]|h", [5] = "|Hitem:50278|h[x]|h", [7] = "|Hitem:51282|h[x]|h" }
for i = 1, 34 do Tick(0.15) end   -- links arrive without UNIT_INVENTORY_CHANGED; past the 5 s timer
check(reco() == "mirror", "T10 recounted 5 s after login (" .. tostring(reco()) .. ")")
INCOMBAT, TARGETNAME, EQUIPPED, PLAYER_TALENTS = false, nil, {}, nil
FireEvent("UNIT_INVENTORY_CHANGED", "player"); FireEvent("PLAYER_TALENT_UPDATE"); Tick(0.15)
check(FRAMES.ClassHelperButton_lb.__shown, "back to Fire after the login check")
OUT[#OUT + 1] = "T10LOGIN OK"
'''

# Arcane rotation: auto mode by talents, button set, cooldowns, gem/Evocation, Missile Barrage,
# burn vs conserve (mana threshold and time-to-die estimate), movement, switching back to Fire.
ARCANE = r'''
local KR = ClassHelperFrame
local de = GetLocale() == "deDE"
local function upd(n) for i = 1, (n or 8) do Tick(0.15) end end   -- 1.2 s: burn/conserve is re-decided every second
local function reco() return FRAMES.ClassHelperOneButton.currentKey end
local function shown(k) return FRAMES["ClassHelperButton_" .. k].__shown end
local function macro(k) return FRAMES["ClassHelperButton_" .. k].__attr.macrotext end
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
local function btnState(k) return FRAMES["ClassHelperButton_" .. k].state end
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
check(not pcall(FRAMES.ClassHelperButton_ab.Hide, FRAMES.ClassHelperButton_ab), "stub: secure button Hide() blocked in combat")
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
check(MH.db.profile.arcaneBurnMode == "mana" and MH.db.profile.arcaneBurnMana == 35, "/ch burn mana 35")
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
check(reco() == nil and FRAMES.ClassHelperOneButton.dynamicMacroText == nil, "moving without instants: no cast recommendation (" .. tostring(reco()) .. ")")
check(btnState("evo") == "normal" and btnState("am") == "normal" and btnState("ab") == "normal", "moving without instants: no cast button lit")
check(KR.info.__text:find(de and "Bewegung" or "Moving", 1, true), "moving without instants: move hint (" .. KR.info.__text .. ")")
AURAS.player = { { S(12043), 0, nil, 12043 } }; upd()
check(reco() == "ab", "moving with Presence of Mind up: instant Arcane Blast (" .. tostring(reco()) .. ")")
AURAS.player, KNOWN[44781], COOLDOWNS[EVO] = {}, nil, 100
MOVING = false; state(20000, 0); upd()
check(reco() == "ab" and FRAMES.ClassHelperOneButton.dynamicMacroText ~= nil, "standing again: one-button back")
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
check(MH.db.profile.arcaneBurnMode == "auto" and MH.db.profile.arcaneBurnMana == 35, "/ch burn auto keeps the threshold")
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
Slash("rota arkan"); check(shown("ab") and not shown("lb"), "/ch rota arkan")
Slash("rota auto"); check(shown("ab"), "auto with Arcane talents")
PLAYER_TALENTS = { 0, 55, 16 }; FireEvent("ACTIVE_TALENT_GROUP_CHANGED"); check(shown("lb") and not shown("ab"), "spec switch to Fire")
PLAYER_TALENTS = { 0, 17, 54 }; FireEvent("PLAYER_TALENT_UPDATE"); check(shown("fbolt") and not shown("lb") and not shown("ab"), "Frost talents: Frost")
Slash("rota"); Slash("burn"); Slash("rota bogus")

-- options
local o = LibStub("AceConfigRegistry-3.0"):GetOptionsTable("ClassHelper", "dialog", "MyLib-1.0")
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
local KR = ClassHelperFrame
local de = GetLocale() == "deDE"
local function upd(n) for i = 1, (n or 2) do Tick(0.15) end end
local function reco() return FRAMES.ClassHelperOneButton.currentKey end
local function st(k) return FRAMES["ClassHelperButton_" .. k].state end
local function shown(k) return FRAMES["ClassHelperButton_" .. k].__shown end
local function info() return KR.info.__text end
local IND = FRAMES.ClassHelperStealIndicator
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
local m = FRAMES.ClassHelperButton_steal.__attr.macrotext
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
check(MH.db.profile.spellstealAll and reco() == "steal" and st("steal") == "glow", "/ch raub alle: unlisted -> steal, not urgent (" .. tostring(st("steal")) .. ")")
Slash("steal worth"); upd()
check(not MH.db.profile.spellstealAll and reco() ~= "steal", "/ch steal worth: unlisted ignored again")

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
check(not MH.db.profile.spellsteal and reco() ~= "steal" and not IND.__shown and st("steal") == "normal", "/ch raub aus: nothing")
RANGE.target = 0; upd(); check(st("steal") == "normal" and not info():find(NP, 1, true), "off: no out-of-range hint either"); RANGE.target = nil
Slash("steal on"); upd()
check(MH.db.profile.spellsteal and reco() == "steal", "/ch steal on: rescans at once")

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
local o = LibStub("AceConfigRegistry-3.0"):GetOptionsTable("ClassHelper", "dialog", "MyLib-1.0")
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
local KR = ClassHelperFrame
local de = GetLocale() == "deDE"
local function upd(n) for i = 1, (n or 3) do Tick(0.15) end end
local function reco() return FRAMES.ClassHelperOneButton.currentKey end
local function shown(k) return FRAMES["ClassHelperButton_" .. k].__shown end
local function macro(k) return FRAMES["ClassHelperButton_" .. k].__attr.macrotext end
local function btnState(k) return FRAMES["ClassHelperButton_" .. k].state end
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
check(not pcall(FRAMES.ClassHelperButton_fbolt.Hide, FRAMES.ClassHelperButton_fbolt), "stub: secure button Hide() blocked in combat")
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
Slash("rota frost"); check(MH.db.profile.rotationMode == "frost" and shown("fbolt") and not shown("lb"), "/ch rota frost")
Slash("rota arkan"); upd(); check(shown("ab") and not shown("fbolt") and (reco() == "ab" or reco() == "am"), "/ch rota arkan")
Slash("rota auto"); check(shown("fbolt"), "auto with Frost talents")
local o = LibStub("AceConfigRegistry-3.0"):GetOptionsTable("ClassHelper", "dialog", "MyLib-1.0")
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

# Potion choice: auto by the active rotation, fixed potions and none; cooldown macros of all three
# rotations, buff bar by buff ID, changes in combat only after combat.
POTION = r'''
local P = FRAMES.ClassHelperBuff_potion
local C = MH.db.char
local function upd(n) for i = 1, (n or 3) do Tick(0.15) end end
local function macro(k) return FRAMES["ClassHelperButton_" .. k].__attr.macrotext end
local function shown(k) return FRAMES["ClassHelperButton_" .. k].__shown end
local function has(k, item) return macro(k):find("/use item:" .. item, 1, true) ~= nil end
local function potionLines(k) local n = 0; for _ in macro(k):gmatch("/use item:4021[12]") do n = n + 1 end
  for _ in macro(k):gmatch("/use item:33448") do n = n + 1 end; for _ in macro(k):gmatch("/use item:40093") do n = n + 1 end; return n end
local function active() upd(1); return P.timer.__text ~= "!" and P.timer.__text ~= "" end
local function grey() upd(1); return P.timer.__text == "" and string.format("%.2f", P.status.__vc[1]) == "0.55" end
local function drink(buffId) AURAS.player = { { GetSpellInfo(buffId) or "Potion", 0, GetTime() + 15, buffId } } end
INCOMBAT, PLAYER_TALENTS, AURAS.player, EQUIPPED, KNOWN = false, nil, {}, {}, {}
Slash("rota auto"); upd()
check(C.potion == "auto", "default potion choice is auto")
check(shown("lb"), "Fire rotation")
-- Fire: Wild Magic in the cd macro, Mana Sapphire stays, Flame Cap is gone
check(has("cd", 40212) and potionLines("cd") == 1, "Fire cd macro uses Potion of Wild Magic: " .. macro("cd"))
check(has("cd", 33312), "Fire cd macro keeps the Mana Sapphire")
check(not macro("cd"):find("22788", 1, true), "Flame Cap removed")
check(macro("cd"):find("/cast " .. GetSpellInfo(55342), 1, true), "Fire cd macro casts Mirror Image")
check(tostring(P.icon.__tex):find("item40212", 1, true), "buff bar icon: Wild Magic: " .. tostring(P.icon.__tex))
check(not active(), "no potion buff: missing")
drink(53908); check(not active(), "Speed buff does not count for Fire auto")
drink(53909); check(active(), "Wild Magic buff counts (by ID)")
AURAS.player = {}
-- Arcane and Frost: Speed
Slash("rota arkan"); upd()
check(has("ap", 40211) and potionLines("ap") == 1, "Arcane AP macro uses Potion of Speed: " .. macro("ap"))
check(tostring(P.icon.__tex):find("item40211", 1, true), "buff bar icon follows the rotation: " .. tostring(P.icon.__tex))
drink(53908); check(active(), "Arcane: Speed buff counts"); AURAS.player = {}
Slash("rota frost"); upd()
check(has("fcd", 40211) and potionLines("fcd") == 1, "Frost cd macro uses Potion of Speed: " .. macro("fcd"))
check(macro("fcd"):find("/cast " .. GetSpellInfo(55342), 1, true), "Frost cd macro still casts Mirror Image")
-- fixed choices
Slash("trank wild"); check(C.potion == "wildmagic" and has("fcd", 40212) and has("ap", 40212) and has("cd", 40212), "fixed Wild Magic in all macros")
Slash("potion indestructible"); check(C.potion == "indestructible" and has("fcd", 40093) and potionLines("fcd") == 1, "fixed Indestructible")
drink(53762); check(active(), "Indestructible buff counts"); AURAS.player = {}
Slash("trank mana"); check(C.potion == "runicmana" and has("fcd", 33448) and has("ap", 33448), "fixed Runic Mana")
check(grey(), "Runic Mana: buff bar grey (no buff to check)")
check(tostring(P.icon.__tex):find("item33448", 1, true), "Runic Mana icon")
Slash("trank aus"); check(C.potion == "none" and potionLines("fcd") == 0 and potionLines("ap") == 0 and potionLines("cd") == 0, "none: no potion line")
check(has("cd", 33312), "none: Mana Sapphire stays")
check(grey(), "none: buff bar grey")
Slash("potion speed"); check(C.potion == "speed" and has("cd", 40211), "English alias speed")
Slash("trank tempo"); Slash("trank"); Slash("potion bogus")
-- in combat: no protected change, applies after combat
Slash("rota feuer"); Slash("trank auto"); upd()
INCOMBAT = true; FireEvent("PLAYER_REGEN_DISABLED"); upd()
Slash("trank unzerstoerbar")
check(C.potion == "indestructible" and has("cd", 40212) and not has("cd", 40093), "in combat the cd macro keeps Wild Magic")
check(tostring(P.icon.__tex):find("item40212", 1, true), "in combat the buff bar keeps the potion in the macro")
P.__scripts.OnEnter(P)
INCOMBAT = false; FireEvent("PLAYER_REGEN_ENABLED"); upd()
check(has("cd", 40093) and not has("cd", 40212), "after combat the cd macro uses the new potion")
check(tostring(P.icon.__tex):find("item40093", 1, true), "after combat the buff bar follows")
P.__scripts.OnEnter(P)
-- options
local o = LibStub("AceConfigRegistry-3.0"):GetOptionsTable("ClassHelper", "dialog", "MyLib-1.0")
local v = o.args.general.args.potion.values()
check(v.auto and v.none and v.speed and v.wildmagic and v.runicmana and v.indestructible, "options list the potions")
OUT[#OUT + 1] = "POTION AUTO " .. v.auto .. " / " .. v.none
o.args.general.args.potion.set({ "general", "potion" }, "speed")
check(C.potion == "speed" and has("cd", 40211), "potion via options")
C.potion = "bogus"
check(o.args.general.args.potion.get() == "auto", "invalid potion value shows as auto")
C.potion = "auto"; Slash("trank auto")
check(has("cd", 40212), "back to auto: Wild Magic for Fire")
AURAS.player = {}
OUT[#OUT + 1] = "POTION OK"
'''

# Professor Putricide Tear Gas (normal only): Invisibility just above 80%/35% (cfg.putricideInvisLead),
# hold while invisible, cancel after the gas lands, re-engage countdown (yells, drinks), threat check
# -> Ice Block or stop casting, ends on 71615 removed / 71620 / timeout / combat end; cast start is a
# late fallback (combat log in the 3.3.5 layout or UnitCastingInfo); heroic and other casters ignored.
TEARGAS = r"""
local KR = ClassHelperFrame
local de = GetLocale() == "deDE"
local function upd(n) for i = 1, (n or 2) do Tick(0.15) end end
local function reco() return FRAMES.ClassHelperOneButton.currentKey end
local function st(k) return FRAMES["ClassHelperButton_" .. k].state end
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
check(FRAMES.ClassHelperButton_invis.__attr.macrotext:find("/cancelaura " .. INVIS, 1, true), "invis macro cancels the aura first")
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
check(MH.db.profile.putricideInvisLead == 3 and OUT[before + 1]:find("3.0", 1, true), "/ch tränengas 3 sets the lead: " .. tostring(OUT[before + 1]))
hp(83.2); check(reco() ~= "invis" and st("invis") == "prep", "lead 3: 83.2% only pre-warning")
hp(82.9); check(reco() == "invis", "lead 3: 82.9% urgent")
Slash("traenengas 9"); check(MH.db.profile.putricideInvisLead == 5, "lead clamped to 5")
local o = LibStub("AceConfigRegistry-3.0"):GetOptionsTable("ClassHelper", "dialog", "MyLib-1.0")
local b = o.args.bosses.args
check(b.putricideInvisLead.min == 0.5 and b.putricideInvisLead.max == 5, "options: lead slider 0.5-5")
o.args.bosses.set({ "bosses", "putricideInvisLead" }, 0.5); fight()
check(MH.db.profile.putricideInvisLead == 0.5, "options: lead 0.5")
hp(80.6); check(reco() ~= "invis", "lead 0.5: 80.6% not yet")
hp(80.4); check(reco() == "invis", "lead 0.5: 80.4% urgent")
b.putricideInvis.set({ "bosses", "putricideInvis" }, false); upd()
check(MH.db.profile.putricideInvis == false and reco() ~= "invis" and st("invis") == "normal", "options: off -> nothing")
Slash("teargas on"); Slash("teargas 1"); upd(); check(reco() == "invis", "/ch teargas on")
Slash("teargas off"); upd(); check(reco() ~= "invis", "/ch teargas off -> nothing")
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
gasCast(); upd()
check(reco() ~= "invis" and reco() ~= nil and st("invis") == "prep" and has(info(), "Tränengas wird gewirkt - Unsichtbarkeit vermutlich zu spät", "Tear Gas is being cast - Invisibility probably too late"),
  "cast start fallback: not urgent, blue button + hint, rotation goes on (" .. tostring(reco()) .. ") " .. info())
show("FALLBACK")
upd(22); check(reco() ~= "invis" and st("invis") ~= "prep", "3 s after the cast: too late, nothing")
DEBUFFS.player = { { GAS, 0, GetTime() + 18, 71615 } }; upd(); check(reco() ~= "invis" and reco() ~= nil, "stunned anyway: no Tear Gas recommendation")
DEBUFFS.player = {}; fight()
CASTING.boss1 = { GAS, GetTime() * 1000, GetTime() * 1000 + 2500 }; upd()
check(reco() ~= "invis" and st("invis") == "prep", "UnitCastingInfo fallback (name from GetSpellInfo): blue hint")
CASTING.boss1 = nil
COOLDOWNS[INVIS] = 100; fight(); gasCast(); upd(); check(reco() ~= "invis" and st("invis") == "normal" and not has(info(), "zu spät", "too late"), "Invisibility on cooldown: no fallback")
upd(300); check(not has(info(), "Seuchenmord", "Putricide"), "timeout ends the transition")
COOLDOWNS = {}; hp(80.9); invisible(true); upd(); check(reco() == nil, "invisible in the window: wait")
INCOMBAT = false; FireEvent("PLAYER_REGEN_ENABLED"); invisible(false); hp(70)
check(reco() ~= nil, "combat end: back to the rotation")

local function iceBlock(on) AURAS.player = on and { { ICE, 0, GetTime() + 10, 45438 } } or {} end
local function press(spell) FireEvent("UNIT_SPELLCAST_SENT", "player", spell, "", "") end
local HYPO = { S(41425), 0, GetTime() + 600, 41425 }
local function concoction() CL("SPELL_CAST_START", PG, PN, 0xa48, "", nil, 0x80000000, 71621, "Create Concoction", 8) end

-- Ice Block from the threat check: no "cancel Ice Block" until it ends, then "stop casting" while the threat stays high
INCOMBAT = true; FireEvent("PLAYER_REGEN_DISABLED"); COOLDOWNS = {}; MH.db.profile.iceCancelHelper = true; hp(80.2)
gasCast(); upd(18); BOSSES.boss1.hp = 79.5
concoction(); upd(); upd(52) -- 1.7 s before the re-engage: threat window
THREAT.boss1 = { true, 3, 100, 100 }; upd()
check(reco() == "ice" and st("ice") == "urgent", "threat window: Ice Block (" .. tostring(reco()) .. ")")
press(ICE); iceBlock(true); COOLDOWNS[ICE] = 300; upd()
check(reco() == nil and st("ice") ~= "urgent", "Ice Block from the threat check: wait, no cancel (" .. tostring(reco()) .. ") " .. info())
CL("SPELL_CAST_SUCCESS", PG, PN, 0xa48, "", nil, 0x80000000, 71620, GAS, 8); upd(30)
check(reco() == nil and st("ice") ~= "urgent" and not has(info(), "EISBLOCK ABBRECHEN", "CANCEL ICE BLOCK"), "re-engaged 4.5 s ago, still in Ice Block: no cancel hint (" .. tostring(reco()) .. ") " .. info())
iceBlock(false); DEBUFFS.player = { HYPO }; upd()
check(reco() == nil and has(info(), "Bedrohung: Stop casten", "Threat: stop casting"), "Ice Block over, threat still high: stop casting: " .. info())
show("ICEEND")
upd(22); check(not has(info(), "Seuchenmord", "Putricide") and not has(info(), "Bedrohung: Stop", "Threat: stop"), "3 s after Ice Block: Tear Gas helper done: " .. info())

-- Hypothermia: no Ice Block from an existing boss skip ...
THREAT.boss1 = nil; COOLDOWNS = {}
DEBUFFS.player = { { "Boiling Blood", 0, GetTime() + 20, 72385 } }; upd()
check(reco() == "ice", "Boiling Blood: Ice Block skip (" .. tostring(reco()) .. ")")
DEBUFFS.player[2] = HYPO; upd()
check(reco() ~= "ice" and has(info(), "Eisblock CD", "Ice Block on CD"), "Boiling Blood with Hypothermia: no Ice Block: " .. info())
-- ... nor from the Tear Gas threat check
DEBUFFS.player = {}; fight(); hp(80.2); gasCast(); upd(18); BOSSES.boss1.hp = 79.5; concoction(); upd(); upd(52)
DEBUFFS.player = { HYPO }; THREAT.boss1 = { true, 3, 100, 100 }; upd()
check(reco() ~= "ice" and has(info(), "Bedrohung hoch", "High threat"), "Tear Gas threat check with Hypothermia: stop casting, no Ice Block: " .. info())
DEBUFFS.player = {}; THREAT.boss1 = nil

-- invisible before the gas, outside the lead window: wait, and the analyzer does not ask to cancel
fight(); COOLDOWNS = {}; hp(81.8); invisible(true); COOLDOWNS[INVIS] = 180; upd()
check(reco() == nil and has(info(), "Unsichtbar: warten auf Tränengas", "Invisible: wait for Tear Gas"), "invisible at 81.8% (above the 1% lead): wait: " .. info())
check(ClassHelperAnalyzer_GetPriorityOverride() == nil, "analyzer override quiet at 81.8% before the gas")
hp(79.6)
check(reco() == nil and has(info(), "Unsichtbar: warten auf Tränengas", "Invisible: wait for Tear Gas"), "invisible at 79.6% before the cast: wait: " .. info())
check(ClassHelperAnalyzer_GetPriorityOverride() == nil, "analyzer override quiet at 79.6% before the gas")
gasCast(); upd(18)
check(reco() == "invis" and ClassHelperAnalyzer_GetPriorityOverride() ~= nil, "gas landed: cancel Invisibility (helper and analyzer)")
fight(); hp(70); upd()
check(reco() == "invis" and ClassHelperAnalyzer_GetPriorityOverride() ~= nil, "invisible at 70% (no gas coming): analyzer cancel hint as before")
invisible(false); COOLDOWNS = {}

-- trigger from the measured health loss: fast -> earlier than the % lead, slow -> the % lead
local function drain(to, perSec) while BOSSES.boss1.hp > to do BOSSES.boss1.hp = BOSSES.boss1.hp - perSec * 0.15; Tick(0.15) end end
fight(); BOSSES.boss1.hp = 92
drain(85.2, 1.6)
check(reco() ~= "invis" and st("invis") == "prep" and has(info(), "84.0%", "84.0%"), "fast loss 1.6 %/s: pre-warning names the trigger 84.0% (80 + 1.6 * 2.5): " .. info())
show("RATE")
drain(83.95, 1.6)
check(reco() == "invis" and st("invis") == "urgent", "fast loss: urgent Invisibility at " .. BOSSES.boss1.hp .. "% (1% lead alone: 81%)")
fight(); BOSSES.boss1.hp = 83
drain(81.2, 0.2)
check(reco() ~= "invis" and st("invis") == "prep" and has(info(), "81.0%", "81.0%"), "slow loss 0.2 %/s: the 1% lead counts, trigger 81.0%: " .. info())
drain(80.95, 0.2)
check(reco() == "invis", "slow loss: urgent below 81%")

-- double press: no cancel within 1.2 s after the press
fight(); COOLDOWNS = {}; hp(70)
press(ICE); iceBlock(true); COOLDOWNS[ICE] = 300; upd()
check(reco() ~= "ice" and st("ice") ~= "urgent", "Ice Block just pressed: no 'cancel Ice Block' (" .. tostring(reco()) .. ")")
upd(7)
check(reco() == "ice" and has(info(), "EISBLOCK ABBRECHEN", "CANCEL ICE BLOCK"), "1.2 s later the generic cancel hint is back: " .. info())
iceBlock(false); COOLDOWNS = {}
FireEvent("UNIT_SPELLCAST_SUCCEEDED", "player", INVIS, "", ""); AURAS.player = { { INVIS, 0, GetTime() + 3, 66 } }; COOLDOWNS[INVIS] = 180; upd()
check(reco() ~= "invis" and ClassHelperAnalyzer_GetPriorityOverride() == nil, "Invisibility just cast (fading): no 'cancel Invisibility' (" .. tostring(reco()) .. ")")
upd(7); check(reco() == "invis", "away from the gas the analyzer's cancel hint comes back after 1.2 s")
invisible(false); COOLDOWNS = {}
fight(); hp(80.9); check(reco() == "invis", "Tear Gas trigger")
press(INVIS); upd()
check(reco() == nil and st("invis") ~= "urgent", "Invisibility sent, no aura yet: wait, no second urgent press")
AURAS.player = { { INVIS, 0, GetTime() + 3, 66 } }; COOLDOWNS[INVIS] = 180; upd(10)
check(reco() == nil, "fading: wait")
invisible(false); COOLDOWNS = {}

-- Putricide as focus
fight(); local savedBosses = BOSSES; BOSSES = {}; TARGETGUID = "GUID-x"; FOCUS = { name = PN, guid = PG, hp = 80.9 }; upd()
check(reco() == "invis" and st("invis") == "urgent", "Putricide as focus: trigger (" .. tostring(reco()) .. ")")
FOCUS = nil; BOSSES = savedBosses; TARGETGUID = PG

-- Invisibility drops combat mid-fight (some cores): transition and analyzer run survive
fight(); COOLDOWNS = {}; upd(40)
local fights = MH.db.char.analyzer.bossFights
local first = fights[1]
hp(80.9); invisible(true); COOLDOWNS[INVIS] = 180; gasCast(); upd(18)
BOSSES.boss1.combat = true; INCOMBAT = false; FireEvent("PLAYER_REGEN_ENABLED"); upd()
check(MH.db.char.analyzer.bossFights[1] == first and reco() == "invis" and has(info(), "greift in", "re-engages in"), "out of combat while invisible, Putricide fighting: run and transition kept: " .. info())
INCOMBAT = true; FireEvent("PLAYER_REGEN_DISABLED"); invisible(false); upd()
check(has(info(), "greift in", "re-engages in"), "back in combat: same transition: " .. info())
INCOMBAT = false; FireEvent("PLAYER_REGEN_ENABLED")
check(MH.db.char.analyzer.bossFights[1] ~= first, "real fight end saves the run")
first = MH.db.char.analyzer.bossFights[1]
INCOMBAT = true; FireEvent("PLAYER_REGEN_DISABLED"); upd(40); invisible(true)
INCOMBAT = false; FireEvent("PLAYER_REGEN_ENABLED"); upd()
check(MH.db.char.analyzer.bossFights[1] == first, "held while invisible and Putricide in combat")
BOSSES.boss1.combat = false; upd()
check(MH.db.char.analyzer.bossFights[1] ~= first, "Putricide out of combat: the held fight end runs")
BOSSES.boss1.combat = nil; invisible(false); COOLDOWNS = {}

check(#ERRORS == errors, "no Lua errors (protected frames untouched in combat)")
INCOMBAT = false; FireEvent("PLAYER_REGEN_ENABLED")
BOSSES, TARGETNAME, TARGETGUID, INSTANCE, THREAT, CASTING, AURAS.player, DEBUFFS.player, COOLDOWNS, PET = {}, nil, nil, nil, {}, {}, {}, {}, {}, false
Slash("rota auto")
OUT[#OUT + 1] = "TEARGAS OK"
"""

# ---------------------------------------------------------------------------------------------
# Other classes: each runs in its own Lua state with its own login (the class is fixed at login).
# ---------------------------------------------------------------------------------------------
CLASSCOMMON = r'''
M = ADDONTABLE.M
function upd(n) for i = 1, (n or 3) do Tick(0.15) end end
function shown(k) local b = FRAMES["ClassHelperButton_" .. k]; return b ~= nil and b.__shown end
function buffShown(k) local b = FRAMES["ClassHelperBuff_" .. k]; return b ~= nil and b.__shown end
function macro(k) return FRAMES["ClassHelperButton_" .. k].__attr.macrotext or "" end
function S(id) return GetSpellInfo(id) end
function isRed(b) local c = b.status.__vc; return c and c[1] > 0.9 and c[2] < 0.1 end
function isGreen(b) local c = b.status.__vc; return c and c[2] > 0.9 and c[1] < 0.2 end
function isYellow(b) local c = b.status.__vc; return c and c[1] > 0.9 and c[2] > 0.7 and c[3] < 0.1 end
function isGrey(b) local c = b.status.__vc; return c and c[1] > 0.5 and c[1] < 0.6 and math.abs(c[1] - c[2]) < 0.01 end
function opts() return LibStub("AceConfigRegistry-3.0"):GetOptionsTable("ClassHelper", "dialog", "MyLib-1.0") end
MAGE_FRAMES = { "ClassHelperButton_lb", "ClassHelperButton_fireball", "ClassHelperButton_ab", "ClassHelperButton_fbolt",
  "ClassHelperButton_steal", "ClassHelperButton_ice", "ClassHelperButton_invis", "ClassHelperButton_stop",
  "ClassHelperBuff_armor", "ClassHelperBuff_brilliance", "ClassHelperBuff_fmin", "ClassHelperBuff_fmout",
  "ClassHelperBuff_FMSet", "ClassHelperBuff_potion", "ClassHelperBuff_speed", "ClassHelperBuff_hero",
  "ClassHelperStealIndicator", "ClassHelperFMPicker" }
MAGE_GROUPS = { "rotation", "arcane", "spellsteal", "bosses", "focusMagic", "molten" }
function checkNoMage(who)
  for _, n in ipairs(MAGE_FRAMES) do check(FRAMES[n] == nil, who .. ": no mage frame " .. n) end
  local o = opts()
  check(type(o) == "table", who .. ": options table valid")
  for _, g in ipairs(MAGE_GROUPS) do check(o.args[g].hidden() == true, who .. ": mage option group hidden: " .. g) end
  check(o.args.general.args.potion.hidden() == true, who .. ": potion option hidden")
  local before = #OUT
  Slash("fm"); Slash("t9"); Slash("tränengas an"); Slash("raub an")
  check(FRAMES.ClassHelperFMPicker == nil, who .. ": /ch fm opens nothing")
  check(#OUT == before + 4 and OUT[#OUT]:find(GetLocale() == "deDE" and "Nur für Magier" or "Mage only", 1, true), who .. ": mage commands refused: " .. tostring(OUT[#OUT]))
end
'''

PROT_SET = '{ "hor", "rd", "dprot", "loh", "dshield", "rf", "seal", "sealaoe", "hs", "judge", "hotr", "cons", "sor", "how", "avs", "plea" }'
RET_SET = '{ "seal", "sealaoe", "aw", "judge", "cs", "dstorm", "cons", "how", "exo", "hwrath", "plea" }'

# Paladin logged in with Protection talents: buttons, buff bar, options, recommendation hook,
# spec switches (also in combat), Holy, judgement option, slash commands.
PALADIN_LOGIN = r'''
upd()
check(M.CLASS == "PALADIN" and M.activeRota == "prot", "Prot paladin at login: " .. tostring(M.activeRota))
checkNoMage("paladin")
local o = opts()
check(o.args.paladin.hidden() == false, "paladin option group shown")
check(o.args.paladin.args.palUsePallyPower.disabled() == true, "PallyPower option greyed without PallyPower")
check(MH.db.profile.palUsePallyPower == true and MH.db.profile.palJudgement == "wisdom", "paladin defaults")
check(ClassHelperFrame.__shown, "rotation bar shown")
for _, k in ipairs(''' + PROT_SET + r''') do check(shown(k), "Prot button shown: " .. k) end
for _, k in ipairs({ "aw", "cs", "dstorm", "exo", "hwrath" }) do check(not shown(k), "Ret-only button hidden: " .. k) end
-- fixed macros, names from GetSpellInfo
check(macro("rd"):find("/cast [@targettarget,help,nodead] " .. S(31789), 1, true), "Righteous Defense on the boss's target: " .. macro("rd"))
check(macro("loh"):find("[@player] " .. S(48788), 1, true), "Lay on Hands on myself")
check(macro("seal"):find("/cast " .. S(31801), 1, true), "default seal (Alliance): Seal of Vengeance: " .. macro("seal"))
check(macro("sealaoe"):find("/cast " .. S(20375), 1, true), "AoE seal: Seal of Command")
check(macro("judge"):find("/cast " .. S(53408), 1, true), "default judgement: Wisdom")
check(not macro("hs"):find("/use 10", 1, true), "no mage gloves line in paladin macros")
-- buff bar: seal, aura, RF, Holy Shield, Divine Plea, flask, food, own default blessings Kings + Sanctuary
for _, k in ipairs({ "pal_seal", "pal_aura", "pal_rf", "pal_hs", "pal_plea", "flask", "food", "pal_bless1", "pal_bless2" }) do check(buffShown(k), "Prot buff entry shown: " .. k) end
check(not buffShown("pal_bless3") and not buffShown("pal_bless4"), "only two blessing slots in use")
local B = function(k) return FRAMES["ClassHelperBuff_" .. k] end
check(B("pal_seal").__attr.spell == S(31801) and B("pal_aura").__attr.spell == S(465), "seal/aura buttons cast Vengeance / Devotion")
check(B("pal_rf").__attr.macrotext == "/cast " .. S(25780), "RF wanted in Prot: button casts it")
check(B("flask").flaskKey == "stoneblood", "Prot flask: Stoneblood")
check(isRed(B("pal_seal")) and isRed(B("pal_rf")) and isRed(B("pal_bless1")), "nothing up: red")
AURAS.player = { { S(31801), 0, 0, 31801 }, { S(25780), 0, 0, 25780 }, { S(25898), 0, GetTime() + 1800, 25898 },
                 { S(48942), 0, 0, 48942 }, { S(48952), 0, GetTime() + 8, 48952 } }
upd()
check(isGreen(B("pal_seal")) and isGreen(B("pal_rf")) and isGreen(B("pal_aura")), "seal, RF, Devotion (max rank by name) green")
check(isGreen(B("pal_bless1")) and isRed(B("pal_bless2")), "greater Kings counts, Sanctuary missing")
check(isYellow(B("pal_hs")), "Holy Shield running out: yellow")
check(tostring(B("pal_bless1").icon.__tex):find("spell20217", 1, true), "own default blessing shows the single icon")
AURAS.player = { { S(21084), 0, 0, 21084 } }; upd()
check(isYellow(B("pal_seal")) and B("pal_seal").timer.__text == "?", "another seal active: yellow '?'")
FRAMES.ClassHelperBuff_pal_seal.__scripts.OnEnter(FRAMES.ClassHelperBuff_pal_seal)
FRAMES.ClassHelperBuff_pal_bless1.__scripts.OnEnter(FRAMES.ClassHelperBuff_pal_bless1)
FRAMES.ClassHelperBuff_pal_rf.__scripts.OnEnter(FRAMES.ClassHelperBuff_pal_rf)
FRAMES.ClassHelperBuff_pal_hs.__scripts.OnEnter(FRAMES.ClassHelperBuff_pal_hs)
-- aura: only my own counts (stance bar active flag, else an aura buff cast by me)
local DE = GetLocale() == "deDE"
local function tipText(k) local before = #OUT; FRAMES["ClassHelperBuff_" .. k].__scripts.OnEnter(FRAMES["ClassHelperBuff_" .. k]); return table.concat(OUT, "\n", before + 1) end
AURAS.player = {}; upd()
check(isRed(B("pal_aura")), "no aura: red")
local tip = tipText("pal_aura")
check(tip:find(DE and "Keine Aura aktiv" or "No aura active", 1, true) and not tip:find(DE and "Andere Aura" or "Another aura", 1, true), "tooltip: no aura active (not 'another'): " .. tip)
check(tip:find(DE and "Eigene Vorgabe" or "Own default", 1, true), "tooltip names the source (own default): " .. tip)
AURAS.player = { { S(48942), 0, 0, 48942, "raid2" } }; upd()
check(isRed(B("pal_aura")), "another paladin's Devotion Aura on me: not mine, red")
PLAYER_FORM = 465; AURAS.player = {}; upd()
check(isGreen(B("pal_aura")), "stance bar: my Devotion Aura active: green")
PLAYER_FORM = 7294; upd()
check(isYellow(B("pal_aura")) and tipText("pal_aura"):find(DE and "Andere Aura aktiv" or "Another aura is active", 1, true), "my Retribution Aura instead of Devotion: yellow, 'another aura'")
PLAYER_FORM = nil
-- Drums of Forgotten Kings count as Kings
AURAS.player = { { S(72586), 0, GetTime() + 1800, 72586 } }; upd()
check(isGreen(B("pal_bless1")), "Blessing of Forgotten Kings (drums) counts as Kings")
-- one aura scan per update, however many entries ask
local scans = M.palAuraScans; upd(5)
check(M.palAuraScans - scans <= 5, "at most one player aura scan per update: " .. (M.palAuraScans - scans))
AURAS.player = {}; upd()
-- buff bar layout skipped in combat (/reload in combat): done after combat
FRAMES.ClassHelperBuff_pal_hs:Hide()
INCOMBAT = true; M.Pal.LayoutBuffs(M.activeRota)
check(M.palLayoutPending and not buffShown("pal_hs"), "layout in combat: pending, nothing touched")
INCOMBAT = false; FireEvent("PLAYER_REGEN_ENABLED"); upd()
check(not M.palLayoutPending and buffShown("pal_hs"), "layout done after combat")
-- the AoE seal entry: Righteousness when Seal of Command is unknown
KNOWN[20375] = false; Slash("aoe an"); upd()
check(B("pal_seal").__attr.spell == S(21084), "Seal of Command unknown: AoE mode wants Righteousness")
Slash("aoe aus"); KNOWN[20375] = nil; upd()
-- option names follow /ch lang (functions, not fixed at file load)
Slash("lang en"); check(o.args.paladin.args.palAoe.name() == "AoE mode (Seal of Command, AoE priorities)" and o.args.paladin.name() == "Paladin", "options in English after /ch lang en")
check(o.args.paladinProtTaunt.name() == "Protection: taunt" and o.args.palret.args.palRetWait.name() == "Retribution: wait tolerance (s)", "Prot/Ret options in English too")
Slash("lang auto"); check(o.args.paladin.args.palAoe.name():find(DE and "AoE-Modus" or "AoE mode", 1, true), "options follow the client language again")
-- empty recommendation: nothing glows, one-button idle
local orig = M.PalProtReco
M.PalProtReco = function() return nil end; upd()
for _, b in pairs(M.buttons) do check(b.state ~= "glow" and b.state ~= "urgent", "no glow without a rotation") end
check(FRAMES.ClassHelperOneButton.currentKey == nil, "one-button idle")
-- the rotation hook drives the glow
local seen
M.PalProtReco = function(St) seen = St; return "hs", true, "Test" end
upd()
check(M.buttons.hs.state == "urgent" and FRAMES.ClassHelperOneButton.currentKey == "hs", "PalProtReco key glows (urgent) and drives the one-button")
check(seen and seen.rota == "prot" and seen.sealWantedId == 31801 and seen.judgementId == 53408 and seen.rfWanted == true, "state snapshot for the rotation")
check(ClassHelperFrame.info.__text:find("Test", 1, true), "note in the info line: " .. ClassHelperFrame.info.__text)
M.PalProtReco = orig; upd()
-- judgement option (refused in combat), AoE mode
Slash("richturteil licht"); check(macro("judge"):find(S(20271), 1, true), "Judgement of Light by option")
INCOMBAT = true; o.args.paladin.args.palJudgement.set({ "paladin", "palJudgement" }, "wisdom")
check(MH.db.profile.palJudgement == "light", "judgement option refused in combat")
INCOMBAT = false; Slash("richturteil weisheit"); check(macro("judge"):find(S(53408), 1, true), "back to Wisdom")
Slash("aoe an"); upd(); check(B("pal_seal").__attr.spell == S(20375), "AoE mode: the seal entry wants Command")
check(macro("seal"):find(S(31801), 1, true), "the seal button keeps the single-target seal")
Slash("aoe aus"); upd()
-- spec switch to Ret
AURAS.player = {}
PLAYER_TALENTS = { 5, 11, 55 }; FireEvent("PLAYER_TALENT_UPDATE"); upd()
check(M.activeRota == "ret", "talents: Ret")
for _, k in ipairs(''' + RET_SET + r''') do check(shown(k), "Ret button shown: " .. k) end
for _, k in ipairs({ "hor", "rd", "dprot", "loh", "dshield", "rf", "hs", "hotr", "sor", "avs" }) do check(not shown(k), "Prot-only button hidden: " .. k) end
check(not buffShown("pal_hs") and not buffShown("pal_plea") and buffShown("pal_rf"), "Ret buff bar: no Holy Shield / Plea, RF warning entry")
check(B("pal_aura").__attr.spell == S(7294) and B("flask").flaskKey == "endlessrage", "Ret: Retribution Aura, Endless Rage")
check(isGrey(B("pal_rf")) and B("pal_rf").__attr.macrotext == "/cancelaura " .. S(25780), "RF not wanted: grey, click cancels")
AURAS.player = { { S(25780), 0, nil, 25780 } }; upd()
check(isRed(B("pal_rf")), "RF active in Ret: red warning")
check(ClassHelperFrame.info.__text:find(GetLocale() == "deDE" and "nicht gewünscht" or "not wanted", 1, true), "RF warning in the info line")
AURAS.player = {}
local function blessIcon(i) return tostring(B("pal_bless" .. i).icon.__tex) end
upd(5)
check(blessIcon(1):find("spell20217", 1, true) and blessIcon(2):find("spell19740", 1, true), "Ret default blessings: Kings, Might")
-- switch in combat waits for the end of combat
INCOMBAT = true; PLAYER_TALENTS = { 5, 51, 15 }; FireEvent("PLAYER_TALENT_UPDATE"); upd()
check(M.activeRota == "ret" and shown("cs"), "no button change in combat")
INCOMBAT = false; FireEvent("PLAYER_REGEN_ENABLED"); upd()
check(M.activeRota == "prot" and shown("hs") and not shown("cs"), "switch applied after combat")
-- Holy: buff bar only
PLAYER_TALENTS = { 51, 5, 15 }; FireEvent("PLAYER_TALENT_UPDATE"); upd()
check(M.activeRota == "holy" and not ClassHelperFrame.__shown, "Holy: rotation bar hidden")
check(FRAMES.ClassHelperBuffBar.__shown and buffShown("pal_seal") and not buffShown("pal_hs"), "Holy: buff bar shown")
check(B("pal_seal").__attr.spell == S(20166) and B("pal_aura").__attr.spell == S(19746), "Holy defaults: Seal of Wisdom, Concentration Aura")
-- /ch show, the option and the minimap button never show an empty bar
Slash("show"); check(not ClassHelperFrame.__shown and MH.db.profile.shown, "Holy: /ch show keeps the empty bar hidden")
o.args.general.args.shown.set({ "general", "shown" }, true); check(not ClassHelperFrame.__shown, "Holy: option keeps the empty bar hidden")
FRAMES.ClassHelperMinimapButton.__scripts.OnClick(); FRAMES.ClassHelperMinimapButton.__scripts.OnClick()
check(not ClassHelperFrame.__shown and MH.db.profile.shown, "Holy: minimap click keeps the empty bar hidden")
-- fixed mode by slash command and options
Slash("rota vergeltung"); check(M.activeRota == "ret" and ClassHelperFrame.__shown and MH.db.profile.palRotationMode == "ret", "/ch rota ret")
o.args.paladin.args.palRotationMode.set({ "paladin", "palRotationMode" }, "prot"); check(M.activeRota == "prot", "mode via options")
check(type(o.args.paladin.args.palRotationMode.values().auto) == "string" and type(o.args.paladin.args.status.name()) == "string", "options texts")
Slash("rota auto"); check(M.activeRota == "holy", "back to auto (Holy talents)")
PLAYER_TALENTS = { 5, 51, 15 }; FireEvent("PLAYER_TALENT_UPDATE"); upd()
check(M.activeRota == "prot" and ClassHelperFrame.__shown, "Prot again, bar back")
for _, cmd in ipairs({ "help", "", "pal", "rota", "richturteil", "aoe", "report", "debug on", "debug off", "flask", "analyse start", "analyse stop" }) do Slash(cmd) end
Slash("aoe aus")
-- a short fight: nothing breaks, protected frames untouched in combat
INCOMBAT = true; FireEvent("PLAYER_REGEN_DISABLED"); upd(10)
FireEvent("COMBAT_LOG_EVENT_UNFILTERED", 0, "SPELL_CAST_SUCCESS", "GUID-player", "Kahuchan", 0x511, "GUID-target", "Dummy", 0xa48, 53595, S(53595), 1)
FireEvent("UNIT_SPELLCAST_SUCCEEDED", "player", S(53595)); upd(5)
INCOMBAT = false; FireEvent("PLAYER_REGEN_ENABLED"); upd()
check(#ERRORS == 0, "no Lua errors")
OUT[#OUT + 1] = "PALADIN_LOGIN OK"
'''

# PallyPower present (stubbed globals) -> seal, aura, RF and blessings taken over; option off or
# PallyPower gone -> own defaults; its tables are never written.
PALLYPOWER = r'''
local B = function(k) return FRAMES["ClassHelperBuff_" .. k] end
local function dump(t, seen)
  if type(t) ~= "table" then return tostring(t) end
  local keys = {}
  for k in pairs(t) do keys[#keys + 1] = tostring(k) end
  table.sort(keys)
  local s = {}
  for _, k in ipairs(keys) do s[#s + 1] = k .. "=" .. dump(t[k] ~= nil and t[k] or t[tonumber(k)]) end
  return "{" .. table.concat(s, ",") .. "}"
end
PallyPower = { opt = { seal = 4, rf = false, sets = { primary = {}, secondary = {} } } }
PallyPower_AuraAssignments = { Kahuchan = 3, Bpala = 1 }
PallyPower_Assignments = { Kahuchan = { [5] = 3, [1] = 2 }, Bpala = { [5] = 2 }, Gone = { [5] = 1 } }
PallyPower_NormalAssignments = { Bpala = { [5] = { Kahuchan = 4 } } }
AllPallys = { Kahuchan = {}, Bpala = {} }
local snapshot = dump({ PallyPower, PallyPower_AuraAssignments, PallyPower_Assignments, PallyPower_NormalAssignments })
check(M.activeRota == "prot", "starts in Prot")
upd(5)
local o = opts()
check(o.args.paladin.args.palUsePallyPower.disabled() == false, "PallyPower option enabled when loaded")
check(macro("seal"):find("/cast " .. S(21084), 1, true), "seal from PallyPower (Righteousness): " .. macro("seal"))
check(B("pal_seal").__attr.spell == S(21084) and B("pal_aura").__attr.spell == S(19746), "buff bar: PallyPower seal and aura (Concentration): " .. tostring(B("pal_seal").__attr.spell) .. " " .. tostring(B("pal_aura").__attr.spell) .. " shown=" .. tostring(FRAMES.ClassHelperBuffBar.__shown))
check(B("pal_rf").__attr.macrotext == "/cast " .. S(25780), "PallyPower rf=false: RF still wanted in Prot (owner's decision)")
local tb = #OUT; FRAMES.ClassHelperBuff_pal_aura.__scripts.OnEnter(FRAMES.ClassHelperBuff_pal_aura)
check(table.concat(OUT, "\n", tb + 1):find(GetLocale() == "deDE" and "aus PallyPower" or "from PallyPower", 1, true), "aura tooltip names PallyPower as the source")
Slash("rota ret"); upd()
check(B("pal_rf").__attr.macrotext == "/cancelaura " .. S(25780), "PallyPower rf=false in Ret: RF not wanted")
PallyPower.opt.rf = true; upd(); check(B("pal_rf").__attr.macrotext == "/cast " .. S(25780), "PallyPower rf=true in Ret: RF wanted")
PallyPower.opt.rf = false; Slash("rota auto"); upd()
check(M.activeRota == "prot", "back to Prot")
local function blessIcon(i) return tostring(B("pal_bless" .. i).icon.__tex) end
check(buffShown("pal_bless1") and buffShown("pal_bless2") and not buffShown("pal_bless3"), "two blessings assigned to me (paladin 'Gone' skipped)")
check(blessIcon(1):find("spell25898", 1, true), "my greater Kings: " .. blessIcon(1))
check(blessIcon(2):find("spell20911", 1, true), "Bpala's single Sanctuary for me wins over its greater Might: " .. blessIcon(2))
AURAS.player = { { S(20217), 0, 0, 20217 }, { S(25899), 0, 0, 25899 } }; upd()
check(isGreen(B("pal_bless1")) and isGreen(B("pal_bless2")), "single Kings and greater Sanctuary both count")
FRAMES.ClassHelperBuff_pal_bless2.__scripts.OnEnter(FRAMES.ClassHelperBuff_pal_bless2)
check(OUT[#OUT]:find("Bpala", 1, true) or OUT[#OUT - 1]:find("Bpala", 1, true), "blessing tooltip names the paladin")
PallyPower.opt.rf = true; upd(); check(B("pal_rf").__attr.macrotext == "/cast " .. S(25780), "PallyPower rf=true: RF wanted")
-- seal changes in combat apply after combat
INCOMBAT = true; PallyPower.opt.seal = 6; upd()
check(macro("seal"):find(S(21084), 1, true) and B("pal_seal").__attr.spell == S(21084), "no secure change in combat")
INCOMBAT = false; FireEvent("PLAYER_REGEN_ENABLED"); upd()
check(macro("seal"):find(S(31801), 1, true) and B("pal_seal").__attr.spell == S(31801), "seal change applied after combat")
PallyPower.opt.seal = 0; upd(); check(macro("seal"):find(S(31801), 1, true), "PallyPower seal 0: own default")
PallyPower.opt.seal = 4; upd()
local before = #OUT
Slash("pal")
check(table.concat(OUT, "\n", before + 1):find(S(21084), 1, true), "/ch pal shows the PallyPower seal")
-- option off: own defaults
Slash("pallypower aus"); upd(5)
check(MH.db.profile.palUsePallyPower == false, "option off")
check(macro("seal"):find(S(31801), 1, true) and B("pal_aura").__attr.spell == S(465) and B("pal_rf").__attr.macrotext == "/cast " .. S(25780), "option off: own defaults")
check(blessIcon(1):find("spell20217", 1, true) and blessIcon(2):find("spell20911", 1, true), "option off: own blessings Kings/Sanctuary")
Slash("pallypower an"); upd(5)
check(macro("seal"):find(S(21084), 1, true), "option on again")
-- Horde default seal (PallyPower without a seal)
FACTION = "Horde"; PallyPower.opt.seal = 0; upd(); check(macro("seal"):find(S(53736), 1, true), "Horde default: Seal of Corruption")
FACTION = nil; PallyPower.opt.seal = 4; upd()
PallyPower.opt.rf = false -- the test's own change back
check(dump({ PallyPower, PallyPower_AuraAssignments, PallyPower_Assignments, PallyPower_NormalAssignments }) == snapshot, "PallyPower tables unchanged")
-- PallyPower gone (not loaded): own defaults, option greyed
PallyPower, PallyPower_AuraAssignments, PallyPower_Assignments, PallyPower_NormalAssignments, AllPallys = nil, nil, nil, nil, nil
upd(5)
check(o.args.paladin.args.palUsePallyPower.disabled() == true, "option greyed again")
check(macro("seal"):find(S(31801), 1, true) and B("pal_aura").__attr.spell == S(465) and B("pal_rf").__attr.macrotext == "/cast " .. S(25780), "without PallyPower: own defaults")
check(blessIcon(1):find("spell20217", 1, true) and blessIcon(2):find("spell20911", 1, true), "without PallyPower: own blessings")
AURAS.player = {}
check(#ERRORS == 0, "no Lua errors")
OUT[#OUT + 1] = "PALLYPOWER OK"
'''

# Paladin logged in with Retribution talents.
RETLOGIN = r'''
upd()
check(M.CLASS == "PALADIN" and M.activeRota == "ret", "Ret paladin at login: " .. tostring(M.activeRota))
checkNoMage("ret paladin")
for _, k in ipairs(''' + RET_SET + r''') do check(shown(k), "Ret button shown at login: " .. k) end
check(not shown("hor") and not shown("hs"), "Prot buttons hidden at login")
check(FRAMES.ClassHelperBuff_pal_aura.__attr.spell == GetSpellInfo(7294), "Retribution Aura at login")
check(#ERRORS == 0, "no Lua errors")
OUT[#OUT + 1] = "RETLOGIN OK"
'''

# Retribution priority (M.PalRetReco): seal, Avenging Wrath (+ trinkets, marker/Forbearance), the
# SimC order, Consecration TTD, Hammer of Wrath, Art of War, wait tolerance, range, AoE, RF warning.
RET_ROTA = r'''
local function reco() return M.palReco end
local function state(k) return M.buttons[k].state end
local function info() return ClassHelperFrame.info.__text end
local DE = GetLocale() == "deDE"
local AW, JOW, CS, DS, CONS, HOW, EXO, HW, PLEA = 31884, 53408, 35395, 53385, 48819, 48806, 48801, 48817, 54428
local SOV = { S(31801), 0, 0, 31801 }
local function auras(...) AURAS.player = { SOV, ... } end
local function cds(t) COOLDOWNS, COOLDOWN_DURATION = {}, {}; for id, left in pairs(t) do COOLDOWNS[S(id)] = left end end
local guidN = 0
local function newTarget(hp) guidN = guidN + 1; TARGETGUID = "GUID-ret" .. guidN; TARGET_HP = hp or 100; FireEvent("PLAYER_TARGET_CHANGED") end
check(M.activeRota == "ret", "Ret mode")
-- options
local o = opts()
check(o.args.palret and o.args.palret.hidden() == false and o.args.palret.args.palRetWait.max == 1, "Ret options group with the wait tolerance")
check(MH.db.profile.palRetWait == 0.4, "wait tolerance default 0.4 s")
check(type(o.args.palret.args.trinkets.name()) == "string", "trinket note")
-- 1) seal
INCOMBAT = false; AURAS.player = {}; cds({}); newTarget(); upd()
check(reco() == "seal" and state("seal") == "urgent", "no seal: seal, urgent: " .. tostring(reco()))
check(info():find(DE and "Kein Siegel" or "No seal", 1, true), "no-seal note: " .. info())
AURAS.player = { { S(21084), 0, 0, 21084 } }; upd()
check(reco() == "seal" and state("seal") == "glow", "another seal: wanted seal, not urgent")
-- an unknown seal (e.g. below level 64) falls back to Seal of Righteousness
KNOWN[31801] = false; upd()
check(M.PalSealId() == 21084 and macro("seal"):find("/cast " .. S(21084), 1, true), "Seal of Vengeance unknown: Righteousness: " .. macro("seal"))
check(reco() ~= "seal", "Righteousness active and wanted: no seal recommendation: " .. tostring(reco()))
KNOWN[20375] = false; Slash("aoe an"); upd()
check(M.PalSealId() == 21084 and reco() ~= "sealaoe", "Seal of Command untalented: AoE mode wants Righteousness: " .. tostring(reco()))
check(macro("sealaoe"):find("/cast " .. S(21084), 1, true), "AoE seal button casts Righteousness then: " .. macro("sealaoe"))
Slash("aoe aus"); KNOWN[31801], KNOWN[20375] = nil, nil; upd()
check(macro("seal"):find("/cast " .. S(31801), 1, true), "Vengeance known again: back")
-- 2) out of combat with a target: no Avenging Wrath, Judgement opens
auras(); upd()
check(reco() == "judge", "out of combat: Judgement first, no AW: " .. tostring(reco()))
NOTARGET = true; upd(); check(reco() == nil, "no target: nothing"); NOTARGET = nil
-- Avenging Wrath in combat
INCOMBAT = true; FireEvent("PLAYER_REGEN_DISABLED"); upd()
check(reco() == "aw" and state("aw") == "urgent", "in combat: Avenging Wrath, urgent: " .. tostring(reco()))
check(macro("aw"):find("/cast " .. S(AW), 1, true) and not macro("aw"):find("/use 1", 1, true), "AW macro without on-use trinkets: " .. macro("aw"))
-- Avenging Wrath blocked: fresh Forbearance (no AW Forbearance since 3.0.4), its hidden marker as buff or debuff
DEBUFFS.player = { { S(25771), 0, GetTime() + 110, 25771 } }; upd()
check(reco() == "judge", "Forbearance < 30 s old blocks AW: " .. tostring(reco()))
DEBUFFS.player = { { S(25771), 0, GetTime() + 60, 25771 } }; upd()
check(reco() == "aw", "older Forbearance: AW allowed")
DEBUFFS.player = {}; upd()
DEBUFFS.player = { { S(25771), 0, 0, 25771 } }; upd()
check(reco() == "judge", "Forbearance without expiry, just appeared: blocks AW: " .. tostring(reco()))
SetNow(GetTime() + 31); upd(); check(reco() == "aw", "Forbearance without expiry, seen for 31 s: AW allowed: " .. tostring(reco()))
DEBUFFS.player = { { "Avenging Wrath Marker", 0, GetTime() + 20, 61987 } }; upd()
check(reco() == "judge", "AW marker (debuff) blocks AW")
DEBUFFS.player = {}; auras({ "x", 0, GetTime() + 20, 61987 }); upd()
check(reco() == "judge", "AW marker (buff) blocks AW")
auras(); DEBUFFS.player = { { S(25771), 0, GetTime() + 110, 25771 } }; upd()
check(reco() == "aw", "marker seen this session: Forbearance alone no longer blocks: " .. tostring(reco()))
DEBUFFS.player = {}
auras(); USABLE[S(AW)] = false; upd(); check(reco() == "judge", "AW not usable: skipped"); USABLE[S(AW)] = nil
-- 3) order Judgement > CS > DS > Consecration > HoW > Exorcism (AoW) > Plea
cds({ [AW] = 100 }); upd(); check(reco() == "judge", "AW on cooldown: Judgement")
cds({ [AW] = 100, [JOW] = 5 }); upd(); check(reco() == "cs", "Judgement on cd: Crusader Strike: " .. tostring(reco()))
cds({ [AW] = 100, [JOW] = 5, [CS] = 3 }); upd(); check(reco() == "dstorm", "then Divine Storm")
cds({ [AW] = 100, [JOW] = 5, [CS] = 3, [DS] = 6 }); upd(); check(reco() == "cons", "then Consecration (TTD unknown)")
cds({ [AW] = 100, [JOW] = 5, [CS] = 3, [DS] = 6, [CONS] = 6 }); upd(); check(reco() == "plea", "HoW above 20 %, no AoW: Divine Plea: " .. tostring(reco()))
auras({ S(PLEA), 0, GetTime() + 10, PLEA }); upd(); check(reco() == nil, "Divine Plea active: nothing")
auras({ S(59578), 0, GetTime() + 10, 59578 }); upd(); check(reco() == "exo", "The Art of War: Exorcism: " .. tostring(reco()))
check(info():find(S(59578), 1, true), "AoW note: " .. info())
auras({ S(53489), 0, GetTime() + 10, 53489 }); upd(); check(reco() == "exo", "Art of War rank 1: Exorcism")
auras(); cds({ [AW] = 100, [JOW] = 5, [CS] = 3, [DS] = 6, [CONS] = 6, [PLEA] = 50 }); upd()
check(reco() == nil, "everything on cooldown: nothing")
-- Hammer of Wrath only at 20 % (3.3: Avenging Wrath does not enable it, that came in Cataclysm)
TARGET_HP = 20; upd(); check(reco() == "how", "target at 20 %: Hammer of Wrath: " .. tostring(reco()))
USABLE[S(HOW)] = false; upd(); check(reco() == nil, "HoW not usable: skipped"); USABLE[S(HOW)] = nil
TARGET_HP = 50; auras({ S(AW), 0, GetTime() + 15, AW }); upd(); check(reco() == nil, "Avenging Wrath up, 50 %: no Hammer of Wrath: " .. tostring(reco()))
auras(); upd(); check(reco() == nil, "no AW, 50 %: no HoW")
-- Consecration needs time to die >= 6 s
cds({ [AW] = 100, [JOW] = 5, [CS] = 3, [DS] = 6, [HOW] = 6, [PLEA] = 50 })
newTarget(40)
for i = 1, 36 do TARGET_HP = math.max(1, 40 - i * 1); Tick(0.15) end
check(reco() == nil, "target dies in < 6 s: no Consecration: " .. tostring(reco()))
newTarget(90)
for i = 1, 36 do TARGET_HP = 90 - i * 0.05; Tick(0.15) end
check(reco() == "cons", "target lives long: Consecration: " .. tostring(reco()))
-- 4) wait tolerance: a higher ability ready within 0.4 s keeps the glow
newTarget(); cds({ [AW] = 100 }); COOLDOWNS[S(JOW)], COOLDOWN_DURATION[S(JOW)] = 0.3, 8; upd()
check(reco() == "judge" and state("judge") == "prep", "Judgement ready in 0.3 s: stays (blue): " .. tostring(reco()) .. " " .. tostring(state("judge")))
COOLDOWNS[S(JOW)] = 0.6; upd(); check(reco() == "cs", "Judgement 0.6 s away: Crusader Strike")
MH.db.profile.palRetWait = 0; COOLDOWNS[S(JOW)] = 0.3; upd(); check(reco() == "cs", "tolerance 0: Crusader Strike")
MH.db.profile.palRetWait = 1; COOLDOWNS[S(JOW)] = 0.9; upd(); check(reco() == "judge", "tolerance 1 s: Judgement")
o.args.palret.set({ "palret", "palRetWait" }, 0.4); check(MH.db.profile.palRetWait == 0.4, "set via options")
cds({ [AW] = 100, [JOW] = 1.2 }); upd(); check(reco() == "judge", "only the GCD running: counts as ready")
FireEvent("UNIT_SPELLCAST_SUCCEEDED", "player", S(JOW)); upd(1)
check(reco() == "cs", "right after the cast (client shows only the GCD): not Judgement again: " .. tostring(reco()))
Tick(2); cds({ [AW] = 100 })
-- 5) melee range
RANGE.target = 0; cds({ [AW] = 100, [PLEA] = 50 }); upd()
check(reco() == nil and info():find(DE and "Nahkampfreichweite" or "melee range", 1, true), "out of range: nothing, note: " .. info())
cds({ [AW] = 100, [PLEA] = 50, [JOW] = 5, [CS] = 3, [DS] = 6, [CONS] = 6 }); upd()
check(reco() == nil and not info():find(DE and "Nahkampfreichweite" or "melee range", 1, true), "out of range, melee abilities on cooldown anyway: no range note: " .. info())
RANGE.target = nil; cds({ [AW] = 100, [PLEA] = 50 }); upd(); check(reco() == "judge", "back in range")
-- 6) trinkets ride on the AW button
INCOMBAT = false; FireEvent("PLAYER_REGEN_ENABLED")
EQUIPPED[13] = "|Hitem:50343|h[x]|h"; EQUIPPED[14] = "|Hitem:50355|h[x]|h"; ITEM_USE[50343] = "Use"
FireEvent("UNIT_INVENTORY_CHANGED", "player"); upd()
check(macro("aw"):find("/use 13", 1, true) and not macro("aw"):find("/use 14", 1, true), "AW macro uses the on-use trinket only: " .. macro("aw"))
INCOMBAT = true; FireEvent("PLAYER_REGEN_DISABLED"); upd()
check(reco() == "aw" and state("aw") == "urgent", "AW on cooldown but trinket ready: AW button: " .. tostring(reco()))
check(info():find(DE and "Schmuckst" or "Trinket ready", 1, true), "trinket note: " .. info())
SLOT_COOLDOWNS[13] = 60; upd(); check(reco() == "judge", "trinket on cooldown too: Judgement")
ITEM_USE[50355] = "Use"; upd() -- slot 14 turns on-use in combat (swap): the macro can't follow until after combat
check(reco() == "judge" and not macro("aw"):find("/use 14", 1, true), "trinket not in the AW macro: no AW glow for it: " .. tostring(reco()))
ITEM_USE[50355] = nil
-- 7) AoE mode: DS > Consecration > Holy Wrath (undead/demon) > CS > HoW > Judgement > Exorcism
Slash("aoe an"); cds({ [AW] = 100 }); upd()
check(reco() == "sealaoe" and state("sealaoe") == "glow", "AoE mode with Seal of Vengeance: Seal of Command, not urgent: " .. tostring(reco()))
AURAS.player = { { S(20375), 0, 0, 20375 } }; upd(); check(reco() == "dstorm", "AoE: Divine Storm first: " .. tostring(reco()))
cds({ [AW] = 100, [DS] = 6 }); upd(); check(reco() == "cons", "AoE: then Consecration")
cds({ [AW] = 100, [DS] = 6, [CONS] = 6 }); upd(); check(reco() == "cs", "AoE vs humanoid: no Holy Wrath, Crusader Strike")
TARGET_TYPE = { "Untoter", "Undead" }; upd(); check(reco() == "hwrath", "AoE vs undead: Holy Wrath: " .. tostring(reco()))
TARGET_TYPE = { "D\195\164mon", "Demon" }; upd(); check(reco() == "hwrath", "AoE vs demon: Holy Wrath")
TARGET_TYPE = { "Wildtier", "Beast" }; upd(); check(reco() == "cs", "AoE vs beast: no Holy Wrath")
TARGET_TYPE = { "Untoter", "Undead" }; Slash("aoe aus"); auras(); cds({ [AW] = 100, [JOW] = 5, [CS] = 3, [DS] = 6, [CONS] = 6 }); upd()
check(reco() == "hwrath", "single target vs undead: Holy Wrath before Divine Plea: " .. tostring(reco()))
auras({ S(59578), 0, GetTime() + 10, 59578 }); upd(); check(reco() == "exo", "single target: Exorcism (AoW) before Holy Wrath: " .. tostring(reco()))
auras(); cds({ [AW] = 100, [JOW] = 5, [CS] = 3, [DS] = 6, [CONS] = 6, [HW] = 20 }); upd()
check(reco() == "plea", "Holy Wrath on cooldown: Divine Plea: " .. tostring(reco()))
TARGET_TYPE = { "Humanoid", "Humanoid" }; cds({ [AW] = 100, [JOW] = 5, [CS] = 3, [DS] = 6, [CONS] = 6 }); upd()
check(reco() == "plea", "single target vs humanoid: no Holy Wrath: " .. tostring(reco()))
TARGET_TYPE = nil
cds({ [AW] = 100, [DS] = 6, [CONS] = 6, [CS] = 3 }); Slash("aoe an"); AURAS.player = { { S(20375), 0, 0, 20375 } }; upd()
check(reco() == "judge", "AoE: Judgement after CS and HoW: " .. tostring(reco()))
Slash("aoe aus"); auras()
-- 8) Righteous Fury in Ret: warning, unless PallyPower wants it
auras({ S(25780), 0, nil, 25780 }); upd()
check(info():find(DE and "nicht gewünscht" or "not wanted", 1, true), "RF active in Ret: warning")
PallyPower = { opt = { seal = 0, rf = true } }; upd()
check(not info():find(DE and "nicht gewünscht" or "not wanted", 1, true), "PallyPower rf = true: no warning")
PallyPower = nil; auras(); upd()
INCOMBAT = false; FireEvent("PLAYER_REGEN_ENABLED"); EQUIPPED = {}; SLOT_COOLDOWNS = {}; ITEM_USE = {}; cds({}); AURAS.player = {}; upd()
check(#ERRORS == 0, "no Lua errors")
OUT[#OUT + 1] = "RET_ROTA OK"
'''

# A class without a module (Warrior): loads, shared parts only, nothing mage.
OTHERCLASS = r'''
upd()
check(M.CLASS == "WARRIOR" and M.classMod == nil and M.activeRota == "none", "warrior: no class module")
checkNoMage("warrior")
check(not ClassHelperFrame.__shown, "no rotation bar")
local o = opts()
check(o.args.paladin.hidden() == true, "paladin options hidden")
check(FRAMES.ClassHelperBuffBar.__shown and buffShown("flask") and buffShown("food"), "buff bar with flask and food")
check(FRAMES.ClassHelperBuff_pal_seal == nil and FRAMES.ClassHelperButton_seal == nil, "no paladin frames")
for _, cmd in ipairs({ "help", "", "rota", "report", "debug on", "debug off", "flask", "analyse start", "analyse stop", "show", "hide", "config" }) do Slash(cmd) end
Slash("show"); check(not ClassHelperFrame.__shown, "warrior: /ch show keeps the empty bar hidden")
-- old MageHelper folder still installed: warning in chat (any class)
ADDONS_INSTALLED.MageHelper = { enabled = true }
local before = #OUT
check(M.WarnOldMageHelper() and #OUT == before + 1 and OUT[#OUT]:find("MageHelper", 1, true) and OUT[#OUT]:find("README", 1, true), "old MageHelper enabled: warning: " .. tostring(OUT[#OUT]))
ADDONS_INSTALLED.MageHelper = { enabled = false, loaded = true }; check(M.WarnOldMageHelper(), "old MageHelper loaded: warning")
ADDONS_INSTALLED.MageHelper = { enabled = false }; check(not M.WarnOldMageHelper(), "old MageHelper disabled: no warning")
ADDONS_INSTALLED.MageHelper = nil; check(not M.WarnOldMageHelper(), "no MageHelper: no warning")
INCOMBAT = true; FireEvent("PLAYER_REGEN_DISABLED"); upd(10); INCOMBAT = false; FireEvent("PLAYER_REGEN_ENABLED"); upd()
check(#ERRORS == 0, "no Lua errors")
OUT[#OUT + 1] = "OTHERCLASS OK"
'''

# Protection rotation, taunt and defensive slots (own Lua state). Helpers are globals so every part sees them.
PROTCOMMON = r'''
function npcGuid(id) return string.format("0xF1300%05X000001", id) end
ME = { name = "Kahuchan", class = "PALADIN" }
TANKY = { name = "Tanky", class = "WARRIOR" }
function protBase()
  INCOMBAT = true
  AURAS.player = { { S(25780), 0, 0, 25780 }, { S(31801), 0, 0, 31801 }, { S(48952), 8, GetTime() + 9, 48952 }, { S(54428), 0, GetTime() + 15, 54428 } }
  DEBUFFS, THREAT = { player = {} }, {}
  COOLDOWNS, RANGE, USABLE, BOSSES = {}, {}, {}, {}
  COOLDOWN_DURATION, SPELL_RANGE = {}, {}
  for id, d in pairs({ [53408] = 8, [20271] = 8, [53595] = 6, [48819] = 8, [61411] = 6, [48952] = 8, [48827] = 30, [62124] = 8,
                       [31789] = 8, [498] = 180, [48788] = 1200, [642] = 300, [54428] = 60, [48806] = 6 }) do COOLDOWN_DURATION[S(id)] = d end
  TARGET_HP, PLAYER_HP, NOTARGET, INSTANCE = 100, nil, nil, nil
  TARGETNAME, TARGETGUID, TARGETTARGET = "Training Dummy", nil, nil
  RAID = { ME, TANKY }
  M.lastCastAt = M.lastCastAt or {}
  for k in pairs(M.lastCastAt) do M.lastCastAt[k] = nil end
end
function reco() upd(2); OUT[#OUT + 1] = "PROTNOTE " .. tostring(M.palReco) .. " " .. tostring(M.palNote); return M.palReco, M.palNote end
function st(k) return M.buttons[k] and M.buttons[k].state end
function cl(ev, dstGUID, dstName, spell, amount)
  FireEvent("COMBAT_LOG_EVENT_UNFILTERED", 0, ev, TARGETGUID or "GUID-boss", "Boss", 0xa48, dstGUID, dstName, 0x514, spell, S(spell) or "?", 1, "DEBUFF", amount)
end
function boss(npc, name, target) TARGETGUID, TARGETNAME, TARGETTARGET = npcGuid(npc), name, target end
function endCombat() INCOMBAT = false; FireEvent("PLAYER_REGEN_ENABLED"); upd() end
'''

# 969 priority, look-ahead, GCD, just-cast guard, AoE mode, seal/RF, pull, Hammer of Wrath, Plea.
PROT = r'''
upd()
check(M.activeRota == "prot", "Prot at login")
protBase(); INCOMBAT = false
AURAS.player = {}
local k, n = reco()
check(k == "rf" and st("rf") == "glow", "out of combat, nothing up: Righteous Fury first (not urgent): " .. tostring(k))
AURAS.player = { { S(25780), 0, 0, 25780 } }
k, n = reco(); check(k == "seal", "RF up, no seal: seal: " .. tostring(k))
AURAS.player = { { S(25780), 0, 0, 25780 }, { S(21084), 0, 0, 21084 } }
k, n = reco(); check(k == "seal" and n:find(S(21084), 1, true), "wrong seal (Righteousness): seal, named: " .. tostring(n))
Slash("aoe an"); k = reco(); check(k == "sealaoe", "AoE mode: Seal of Command button: " .. tostring(k)); Slash("aoe aus")
AURAS.player = { { S(25780), 0, 0, 25780 }, { S(31801), 0, 0, 31801 } }
k = reco(); check(k == "avs", "out of combat with a target: Avenger's Shield on the pull: " .. tostring(k))
INCOMBAT = true; FireEvent("PLAYER_REGEN_DISABLED")
k = reco(); check(k == "hs", "in combat, Holy Shield missing: " .. tostring(k))
protBase()
k = reco(); check(k == "judge" and st("judge") == "glow", "969: Judgement first: " .. tostring(k))
COOLDOWNS[S(53408)] = 5; k = reco(); check(k == "hotr", "Judgement on CD: Hammer of the Righteous: " .. tostring(k))
COOLDOWNS[S(53595)] = 3; k = reco(); check(k == "cons", "then Consecration: " .. tostring(k))
COOLDOWNS[S(48819)] = 4; k = reco(); check(k == "sor", "then Shield of Righteousness: " .. tostring(k))
-- look-ahead: a higher one ready within 0.3 s keeps the glow (blue until clickable)
COOLDOWNS[S(53408)] = 0.2; k = reco(); check(k == "judge" and st("judge") == "prep", "Judgement in 0.2 s: still Judgement, blue: " .. tostring(k) .. " " .. tostring(st("judge")))
COOLDOWNS[S(53408)] = 0.5; k = reco(); check(k == "sor", "Judgement in 0.5 s: next ready one (SoR): " .. tostring(k))
-- the GCD alone doesn't count as a cooldown
COOLDOWNS, COOLDOWN_DURATION = { [S(53408)] = 1.5, [S(53595)] = 1.5 }, {}; k = reco(); check(k == "judge", "GCD ignored: " .. tostring(k))
-- right after its cast the spell isn't recommended again (client shows only the GCD for a moment)
FireEvent("UNIT_SPELLCAST_SUCCEEDED", "player", S(53408)); k = reco(); check(k == "hotr", "just cast Judgement: Hammer next: " .. tostring(k))
protBase()
-- judgement of Light by option
INCOMBAT = false; Slash("richturteil licht"); INCOMBAT = true
k, n = reco(); check(k == "judge" and n:find(S(20271), 1, true), "Judgement of Light in the note: " .. tostring(n))
INCOMBAT = false; Slash("richturteil weisheit"); INCOMBAT = true
-- everything of the 969 on cooldown: Hammer of Wrath <= 20 %, Avenger's Shield, Divine Plea, then the next one
COOLDOWNS = { [S(53408)] = 5, [S(53595)] = 3, [S(48819)] = 6, [S(61411)] = 2.5 }
TARGET_HP = 15; k = reco(); check(k == "how", "target at 15 %: Hammer of Wrath: " .. tostring(k))
TARGET_HP = 100; k = reco(); check(k == "avs", "Avenger's Shield when ready: " .. tostring(k))
COOLDOWNS[S(48827)] = 10; AURAS.player[4] = nil; k = reco(); check(k == "plea", "Divine Plea missing: " .. tostring(k))
COOLDOWNS[S(54428)] = 50; k, n = reco(); check(k == "sor" and st("sor") == "prep", "nothing ready: the next one (SoR 2.5 s), blue: " .. tostring(k) .. " " .. tostring(st("sor")))
-- not usable (e.g. mana) / out of range is skipped
protBase(); USABLE[S(53408)] = false; k = reco(); check(k == "hotr", "Judgement not usable: skipped: " .. tostring(k))
protBase(); RANGE.target = 0; COOLDOWNS[S(48827)] = 10; k = reco(); check(k ~= "hotr" and k ~= "sor" and k ~= "cons", "out of melee: no melee abilities: " .. tostring(k))
protBase(); for _, id in ipairs({ 53408, 53595, 61411 }) do SPELL_RANGE[S(id)] = 0 end; k = reco(); check(k == "avs", "out of melee in combat: Avenger's Shield (pull): " .. tostring(k))
-- AoE mode: Hammer and Consecration first
protBase(); AURAS.player[2] = { S(20375), 0, 0, 20375 }
Slash("aoe an"); k, n = reco(); check(k == "hotr", "AoE: Hammer first: " .. tostring(k))
COOLDOWNS[S(53595)] = 4; k = reco(); check(k == "cons", "AoE: then Consecration: " .. tostring(k))
Slash("aoe aus")
-- no target: only buffs
protBase(); NOTARGET = true; k = reco(); check(k == nil, "no target, buffs up: nothing: " .. tostring(k)); NOTARGET = nil
endCombat()
-- /ch hide|show in combat: the bar parents secure buttons, so the change waits for the end of combat
check(ClassHelperFrame.__shown, "bar shown before the combat test")
INCOMBAT = true; FireEvent("PLAYER_REGEN_DISABLED")
local before = #OUT
Slash("hide"); check(ClassHelperFrame.__shown and M.barShownPending and #OUT == before + 1, "/ch hide in combat: deferred, with a note: " .. tostring(OUT[#OUT]))
Slash("show"); Slash("hide"); check(#OUT == before + 1, "in-combat note only once")
FRAMES.ClassHelperMinimapButton.__scripts.OnClick(FRAMES.ClassHelperMinimapButton); check(ClassHelperFrame.__shown, "minimap click in combat: deferred")
FRAMES.ClassHelperMinimapButton.__scripts.OnClick(FRAMES.ClassHelperMinimapButton)
endCombat(); check(not ClassHelperFrame.__shown and not M.barShownPending, "hidden after combat")
opts().args.general.args.shown.set(nil, true); check(ClassHelperFrame.__shown, "option shows the bar out of combat")
check(#ERRORS == 0, "no Lua errors")
OUT[#OUT + 1] = "PROT OK"
'''

# Taunt rules: Festergut stacks, me as the boss's target, HoR on cooldown -> RD, boss not targeted,
# Saurfang Rune of Blood, Gormok heroic threshold, reset on combat end, options.
TAUNT = r'''
protBase(); FireEvent("PLAYER_REGEN_DISABLED")
INSTANCE = { type = "raid", difficulty = 2, dynamic = 0 }
local GB, MP = 72553, 72451
-- swap-debuff stacks on a unit (read by UnitDebuff, not from the combat log)
local function stacks(unit, id, n, exp) DEBUFFS[unit] = n > 0 and { { S(id), n, exp or (GetTime() + 90), id } } or {} end
boss(36626, "Fauldarm", TANKY); upd(4)
stacks("targettarget", GB, 5)
check(M.PalUnitStacks("targettarget", M.PAL_RULE_BY_NPC[36626]) == 5, "Gastric Bloat stacks read from the other tank's auras")
local k, n = reco(); check(k ~= "hor" and k ~= "rd", "5 stacks: no taunt yet: " .. tostring(k))
stacks("targettarget", GB, 6)
k, n = reco(); check(k == "hor" and st("hor") == "urgent", "6 stacks on the other tank: Hand of Reckoning urgent: " .. tostring(k) .. " " .. tostring(st("hor")))
check(n:find("Tanky", 1, true) and n:find("6", 1, true), "note names the tank and stacks: " .. tostring(n))
check(n:find(" | ", 1, true) and n:find(S(53408), 1, true), "taunt note carries the rotation note: " .. tostring(n))
-- the auras decide: a stale/odd combat log event changes nothing, no event at all is fine too
cl("SPELL_AURA_REMOVED", "GUID-Tanky", "Tanky", GB); k = reco(); check(k == "hor", "combat log REMOVED without the aura gone: still taunt")
-- my own stacks still up: no taunt (a new stack on top would add up towards 10 = explosion)
DEBUFFS.player = { { S(GB), 3, GetTime() + 60, GB } }
k, n = reco(); check(k ~= "hor" and k ~= "rd", "own Gastric Bloat still up: no taunt: " .. tostring(k))
DEBUFFS.player = { { S(GB), 3, GetTime() + 1, GB } }
k, n = reco(); check(k == "hor" and st("hor") == "prep", "own stacks about to fall off: blue only, not red: " .. tostring(k) .. " " .. tostring(st("hor")))
check(n:find("3", 1, true), "note shows my own stacks: " .. tostring(n))
local OB = FRAMES.ClassHelperOneButton
check(OB.currentKey == "hor" and OB.state == "prep" and OB.label:GetText() == M.L("GLEICH"), "one-button: prep taunt shown 'not yet', not as click-now: " .. tostring(OB.state) .. " " .. tostring(OB.label:GetText()))
DEBUFFS.player = {}
k = reco(); check(k == "hor" and st("hor") == "urgent", "own stacks gone: red: " .. tostring(st("hor")))
check(OB.currentKey == "hor" and OB.state == "urgent" and OB.label:GetText() == M.L("JETZT"), "one-button: urgent taunt is click-now: " .. tostring(OB.state))
-- Festergut safety: the other tank one below the explosion (9): red even while my own stacks are up
check(M.PAL_FESTER_EMERGENCY == 9 and M.PAL_RULE_BY_NPC[36626].emergency == 9, "Festergut emergency threshold 9")
DEBUFFS.player = { { S(GB), 3, GetTime() + 60, GB } }; stacks("targettarget", GB, 8)
k = reco(); check(k ~= "hor" and k ~= "rd", "8 stacks on the other tank, mine up: no taunt: " .. tostring(k))
stacks("targettarget", GB, 9)
k, n = reco(); check(k == "hor" and st("hor") == "urgent", "EMERGENCY: 9 stacks on the other tank: red although mine are up: " .. tostring(k) .. " " .. tostring(st("hor")))
check(n:find(GetLocale() == "deDE" and "Notfall" or "Emergency", 1, true) and n:find("Tanky", 1, true) and n:find("9", 1, true), "emergency note: " .. tostring(n))
THREAT.target = { true, 3, 100, 100 }; k = reco(); check(k ~= "hor" and k ~= "rd", "emergency, but I tank (threat): no taunt: " .. tostring(k)); THREAT.target = nil
DEBUFFS.player = {}; stacks("targettarget", GB, 6); reco()
-- I tank the boss (threat API): never taunt
THREAT.target = { true, 3, 100, 100 }; k = reco(); check(k ~= "hor" and k ~= "rd", "tanking by threat: no taunt: " .. tostring(k))
THREAT.target = nil
-- I am the boss's target: never taunt
TARGETTARGET = ME; k = reco(); check(k ~= "hor" and k ~= "rd", "boss targets me: no taunt: " .. tostring(k))
-- the boss's target just changed (a target flip during a cast): no taunt until it is stable 0.5 s
TARGETTARGET = TANKY; k = reco(); check(k ~= "hor" and k ~= "rd", "boss target changed 0.3 s ago: no taunt yet: " .. tostring(k))
reco(); k = reco(); check(k == "hor", "boss target stable: taunt: " .. tostring(k))
-- Hand of Reckoning on cooldown: Righteous Defense on the boss's target
COOLDOWNS[S(62124)] = 5; k, n = reco(); check(k == "rd" and st("rd") == "urgent", "HoR on cooldown: Righteous Defense: " .. tostring(k))
check(n:find(S(62124), 1, true), "RD note says HoR is not ready: " .. tostring(n))
COOLDOWNS[S(31789)] = 6; k = reco(); check(k ~= "hor" and k ~= "rd", "both on longer cooldown: rotation: " .. tostring(k))
COOLDOWNS[S(62124)] = 1.8; k = reco(); check(k == "hor" and st("hor") == "prep", "HoR in 1.8 s: shown blue: " .. tostring(k) .. " " .. tostring(st("hor")))
COOLDOWNS = {}
-- a taunt just cast: wait for the boss to turn
FireEvent("UNIT_SPELLCAST_SUCCEEDED", "player", S(62124)); k = reco(); check(k ~= "hor" and k ~= "rd", "taunt just cast: no second one: " .. tostring(k))
for p in pairs(M.lastCastAt) do M.lastCastAt[p] = nil end
-- the boss isn't my target (boss1 only): no taunt button (the macros act on my target), hint in the note
TARGETGUID, TARGETNAME, TARGETTARGET = npcGuid(37000), "Gasspore", nil
BOSSES.boss1 = { name = "Fauldarm", guid = npcGuid(36626), target = TANKY }; DEBUFFS.boss1target = DEBUFFS.targettarget
k, n = reco(); check(k ~= "hor" and k ~= "rd", "boss not targeted: no taunt button: " .. tostring(k))
check(n and n:find(GetLocale() == "deDE" and "Boss ins Ziel" or "target the boss", 1, true) and n:find("Tanky", 1, true), "hint to target the boss, with the reason: " .. tostring(n))
BOSSES = {}; boss(36626, "Fauldarm", TANKY)
-- option: threshold 7
MH.db.profile.palT_festerN = 7; k = reco(); check(k ~= "hor", "threshold 7: 6 stacks no taunt: " .. tostring(k))
MH.db.profile.palT_festerN = 6; MH.db.profile.palT_fester = false; k = reco(); check(k ~= "hor", "rule off: no taunt")
MH.db.profile.palT_fester = true; MH.db.profile.palTaunt = false; k = reco(); check(k ~= "hor", "taunt off: no taunt")
MH.db.profile.palTaunt = true
-- the other tank's stacks gone (aura removed): no taunt
stacks("targettarget", GB, 0); k = reco(); check(k ~= "hor", "other tank's aura gone: no taunt: " .. tostring(k))
endCombat()
-- Saurfang: Rune of Blood on the other tank -> taunt at once
protBase(); FireEvent("PLAYER_REGEN_DISABLED")
boss(37813, "Todesbringer Saurfang", TANKY); upd(4)
k = reco(); check(k ~= "hor", "Saurfang without rune: no taunt: " .. tostring(k))
-- a swing whose damage equals the rune's spell ID is no rune (only SPELL_* events carry spell IDs)
FireEvent("COMBAT_LOG_EVENT_UNFILTERED", 0, "SWING_DAMAGE", TARGETGUID, "Boss", 0xa48, "GUID-Tanky", "Tanky", 0x514, 72410, 0, 1)
k = reco(); check(k ~= "hor", "SWING_DAMAGE of 72410: no rune: " .. tostring(k))
cl("SPELL_CAST_SUCCESS", "GUID-Tanky", "Tanky", 72410)
k, n = reco(); check(k == "hor" and st("hor") == "urgent", "SAURFANG: Rune of Blood on the other tank: taunt: " .. tostring(k))
-- my death mid-fight: UnitAffectingCombat is false while dead, the rune mark must stay
PLAYER_IS_DEAD = true; INCOMBAT = false; upd(2)
check((M.palProt.marks["GUID-Tanky"] or {}).saurfang ~= nil and M.palProt.inCombat, "dead (out of combat by the API): tracking kept")
PLAYER_IS_DEAD = nil; INCOMBAT = true; k = reco(); check(k == "hor", "battle res, back in combat: rune still counts: " .. tostring(k))
TARGETTARGET = ME; k = reco(); check(k ~= "hor", "SAURFANG: boss on me: no taunt")
TARGETTARGET = TANKY; upd(4); SetNow(GetTime() + 21); k = reco(); check(k ~= "hor", "SAURFANG: rune too old: no taunt: " .. tostring(k))
-- boss change resets: Saurfang's marks don't carry over
cl("SPELL_CAST_SUCCESS", "GUID-Tanky", "Tanky", 72410)
boss(34796, "Gormok der Pfähler", TANKY); reco()
check(not (M.palProt.marks["GUID-Tanky"] or {}).saurfang, "boss change: other rules reset")
-- Gormok: 3 stacks normal, 2 heroic (also ICC-style dynamic heroic flag)
INSTANCE = { type = "raid", difficulty = 2, dynamic = 0, isDynamic = false }
stacks("targettarget", 66331, 2)
k = reco(); check(k ~= "hor", "Gormok normal: 2 stacks no taunt: " .. tostring(k))
INSTANCE.difficulty = 4; check(M.PalHeroic(), "difficulty 4 = heroic")
k = reco(); check(k == "hor", "Gormok heroic: 2 stacks taunt: " .. tostring(k))
INSTANCE = { type = "raid", difficulty = 2, dynamic = 1 }; check(M.PalHeroic(), "dynamic heroic flag (ICC) = heroic")
INSTANCE = { type = "raid", difficulty = 2, dynamic = 0 }; check(not M.PalHeroic(), "25 normal")
-- Lich King Soul Reaper: off by default, heroic only
boss(36597, "Der Lichkönig", TANKY)
cl("SPELL_CAST_SUCCESS", "GUID-Tanky", "Tanky", 69409)
k = reco(); check(k ~= "hor", "Soul Reaper rule off by default: " .. tostring(k))
MH.db.profile.palT_lk = true; k = reco(); check(k ~= "hor", "Soul Reaper rule: not on normal")
INSTANCE.dynamic = 1; k = reco(); check(k == "hor", "Soul Reaper rule on, heroic: taunt: " .. tostring(k))
MH.db.profile.palT_lk = false
-- Putricide's Mutated Plague: never left to fall off, the tanks alternate A2/B2/A3/B3 ("leapfrog")
boss(36678, "Professor Seuchenmord", TANKY); DEBUFFS.player = {}
stacks("targettarget", MP, 1); k = reco(); check(k ~= "hor", "PUTRI: 1 stack: no taunt: " .. tostring(k))
stacks("targettarget", MP, 2); k = reco(); check(k == "hor", "PUTRI: other 2, mine 0: taunt: " .. tostring(k))
DEBUFFS.player = { { S(MP), 2, GetTime() + 40, MP } }; stacks("targettarget", MP, 2, GetTime() + 50)
k = reco(); check(k == "hor" and st("hor") == "urgent", "PUTRI: 2 vs 2, theirs newer: taunt although mine are up: " .. tostring(k))
stacks("targettarget", MP, 2, GetTime() + 30); k = reco(); check(k ~= "hor", "PUTRI: 2 vs 2, mine newer (just taunted): no taunt back: " .. tostring(k))
stacks("targettarget", MP, 3, GetTime() + 55); k = reco(); check(k == "hor", "PUTRI: they 3, me 2: taunt: " .. tostring(k))
DEBUFFS.player = { { S(MP), 4, GetTime() + 40, MP } }; k = reco(); check(k ~= "hor", "PUTRI: I have more: no taunt: " .. tostring(k))
DEBUFFS.player = {}
endCombat()
-- options: groups shown for paladins, valid, all texts translated
local o = opts()
local function txt(v) if type(v) == "function" then return v() end return v end
check(o.args.paladinProtTaunt.hidden() == false and o.args.paladinProtDef.hidden() == false, "Prot option groups shown")
check(MH.db.profile.palD_stomp == false, "Gormok Stomp defensive off by default")
for _, g in ipairs({ "paladinProtTaunt", "paladinProtDef" }) do
  OUT[#OUT + 1] = "PROTOPT " .. txt(o.args[g].name)
  for key, a in pairs(o.args[g].args) do
    local nm = txt(a.name)
    check(type(nm) == "string" and nm ~= "", "option name: " .. key)
    OUT[#OUT + 1] = "PROTOPT " .. nm .. " | " .. tostring(txt(a.desc) or "")
    if a.disabled then a.disabled() end
  end
end
o.args.paladinProtTaunt.set({ "paladinProtTaunt", "palT_dwN" }, 4); check(MH.db.profile.palT_dwN == 4, "threshold option sets")
check(#ERRORS == 0, "no Lua errors")
OUT[#OUT + 1] = "TAUNT OK"
'''

# Defensive slot: boss moments and health thresholds, Forbearance, cooldowns.
DEFENSIVE = r'''
protBase(); FireEvent("PLAYER_REGEN_DISABLED")
boss(36597, "Der Lichkönig", ME)
cl("SPELL_CAST_SUCCESS", "GUID-player", "Kahuchan", 69409)
local k, n = reco(); check(k == "dprot" and st("dprot") == "urgent", "DEFENSIVE: Soul Reaper on me: Divine Protection: " .. tostring(k))
check(n:find(S(69409), 1, true), "note names Soul Reaper: " .. tostring(n))
DEBUFFS.player = { { S(25771), 0, GetTime() + 60, 25771 } }
k = reco(); check(k ~= "dprot", "Forbearance: no Divine Protection: " .. tostring(k))
DEBUFFS.player = {}; COOLDOWNS[S(498)] = 60; k = reco(); check(k ~= "dprot", "DP on cooldown: none: " .. tostring(k))
COOLDOWNS = {}; AURAS.player[#AURAS.player + 1] = { S(498), 0, GetTime() + 10, 498 }
k = reco(); check(k ~= "dprot", "DP already up: none: " .. tostring(k))
protBase(); SetNow(GetTime() + 7); k = reco(); check(k ~= "dprot", "Soul Reaper moment over: " .. tostring(k))
MH.db.profile.palD_reaper = false; cl("SPELL_CAST_SUCCESS", "GUID-player", "Kahuchan", 69409); k = reco()
check(k ~= "dprot", "Soul Reaper toggle off"); MH.db.profile.palD_reaper = true
SetNow(GetTime() + 7); cl("SPELL_CAST_SUCCESS", "GUID-Tanky", "Tanky", 69409); k = reco(); check(k ~= "dprot", "Soul Reaper on the other tank: no DP for me")
endCombat()
-- Saurfang Frenzy while he attacks me
protBase(); boss(37813, "Todesbringer Saurfang", ME); THREAT.target = { true, 3, 100, 100 }
cl("SPELL_AURA_APPLIED", TARGETGUID, "Saurfang", 72737)
k = reco(); check(k == "dprot", "Saurfang Frenzy, I tank him (threat): DP: " .. tostring(k))
TARGETTARGET = TANKY; THREAT.target = nil; k = reco(); check(k ~= "dprot", "Frenzy while the other tank tanks: no DP: " .. tostring(k))
TARGETTARGET = ME; k = reco(); check(k ~= "dprot", "Frenzy, boss targets me but the threat API says not tanking (cast flip): no DP: " .. tostring(k))
TARGETNAME, TARGETGUID, THREAT.target = "Training Dummy", nil, { true, 3, 100, 100 }
k = reco(); check(k ~= "dprot", "Frenzy without the boss found: no DP: " .. tostring(k))
endCombat()
-- Ardent Defender's lockout is a debuff: shown in the health note
protBase(); PLAYER_HP = 30; DEBUFFS.player = { { S(66233), 0, GetTime() + 100, 66233 } }
k, n = reco(); check(k == "dprot" and n:find(S(66233), 1, true), "Ardent Defender (debuff) named in the note: " .. tostring(n))
PLAYER_HP = nil; endCombat()
-- Festergut: Pungent Blight cast, and expected after the 3rd inhale
protBase(); boss(36626, "Fauldarm", ME)
cl("SPELL_CAST_START", nil, nil, 69195)
k = reco(); check(k == "dprot", "Pungent Blight cast: DP: " .. tostring(k))
SetNow(GetTime() + 5); k = reco(); check(k ~= "dprot", "Pungent moment over")
cl("SPELL_AURA_APPLIED_DOSE", TARGETGUID, "Fauldarm", 69166, 3)
k = reco(); check(k ~= "dprot", "3rd inhale: not yet")
PLAYER_IS_DEAD = true; INCOMBAT = false; upd(2); check(M.palProt.pungentAt ~= nil, "dead: expected Pungent Blight kept")
PLAYER_IS_DEAD = nil; INCOMBAT = true
SetNow(GetTime() + 32); k = reco(); check(k == "dprot", "about 33 s after the 3rd inhale: DP: " .. tostring(k))
endCombat()
-- Gormok Staggering Stomp, Sindragosa buffet stacks on me
protBase(); boss(34796, "Gormok der Pfähler", ME)
cl("SPELL_CAST_START", nil, nil, 66330); k = reco(); check(k ~= "dprot", "Gormok Stomp: off by default: " .. tostring(k))
MH.db.profile.palD_stomp = true
cl("SPELL_CAST_START", nil, nil, 66330); k = reco(); check(k == "dprot", "Gormok Stomp switched on: DP: " .. tostring(k))
MH.db.profile.palD_stomp = false
endCombat()
protBase(); boss(36853, "Sindragosa", ME)
DEBUFFS.player = { { S(70127), 4, GetTime() + 8, 70127 } }; k = reco(); check(k ~= "dprot", "buffet 4 on me: no DP")
DEBUFFS.player = { { S(70127), 5, GetTime() + 8, 70127 } }; k = reco(); check(k == "dprot", "buffet 5 on me: DP: " .. tostring(k))
endCombat()
-- health thresholds
protBase()
PLAYER_HP = 50; k = reco(); check(k ~= "dprot" and k ~= "loh", "50 % health: nothing defensive")
PLAYER_HP = 30; k, n = reco(); check(k == "dprot" and st("dprot") == "urgent", "HP threshold 35 %: DP: " .. tostring(k))
PLAYER_HP = 10; k = reco(); check(k == "loh" and st("loh") == "urgent", "HP 10 %: Lay on Hands: " .. tostring(k))
COOLDOWNS[S(48788)] = 600; k = reco(); check(k == "dprot", "LoH on cooldown: DP: " .. tostring(k))
MH.db.profile.palDefDS = true; PLAYER_HP = 8; k = reco(); check(k == "dshield", "Divine Shield option on, 8 %: bubble: " .. tostring(k))
MH.db.profile.palDefDS = false
DEBUFFS.player = { { S(25771), 0, GetTime() + 60, 25771 } }; k = reco(); check(k ~= "dprot" and k ~= "loh" and k ~= "dshield", "Forbearance: no DP/LoH/bubble: " .. tostring(k))
DEBUFFS.player = {}; MH.db.profile.palDefHp = false; PLAYER_HP = 10; COOLDOWNS = {}; k = reco(); check(k ~= "loh" and k ~= "dprot", "thresholds off: nothing")
MH.db.profile.palDefHp = true; INCOMBAT = false; k = reco(); check(k ~= "loh", "out of combat: no defensives")
PLAYER_HP = nil
endCombat()
check(#ERRORS == 0, "no Lua errors")
OUT[#OUT + 1] = "DEFENSIVE OK"
'''

CLASS_RUNS = (
    ("PALADIN", "{ 5, 51, 15 }", (("paladin_login", PALADIN_LOGIN), ("pallypower", PALLYPOWER))),
    ("PALADIN", "{ 5, 51, 15 }", (("prot", PROTCOMMON + PROT), ("taunt", PROTCOMMON + TAUNT), ("defensive", PROTCOMMON + DEFENSIVE))),
    ("PALADIN", "{ 5, 11, 55 }", (("retlogin", RETLOGIN), ("ret_rota", RET_ROTA))),
    ("WARRIOR", "{ 5, 51, 15 }", (("otherclass", OTHERCLASS),)),
)

GERMAN = re.compile(r"[äöüßÄÖÜ]|\b(Klick|Linksklick|Rechtsklick|gesetzt|gespeichert|Befehle|Ziel|Hose|Eisblock|Feuerball|Kampf|Lauf|keine?|nach|anzeigen|AUS|AN)\b")

version, files = toc_files()
failed = False
PREFIXES = ("T10LOGIN", "ROWS", "LABEL", "STATUS", "PICKER", "MIGRATION", "COMBATLOG", "OPTIONS", "T9", "THEMES", "FLASK", "ARCANE", "STEAL", "SPELLSTEAL", "FROST", "POTION", "TEARGAS",
            "PALADIN_LOGIN", "PALLYPOWER", "PROT OK", "TAUNT OK", "DEFENSIVE OK", "RETLOGIN", "RET_ROTA", "OTHERCLASS", "|cffff7d0aClassHelper v")
MAGE_PARTS = (("t10login", T10LOGIN), ("migration", MIGRATION), ("main", SCRIPT), ("combatlog", COMBATLOG), ("options", OPTIONS), ("picker", PICKER), ("t9", T9), ("themes", THEMES), ("flask", FLASK), ("arcane", ARCANE), ("spellsteal", SPELLSTEAL), ("frost", FROST), ("potion", POTION), ("teargas", TEARGAS))


def run(loc, label, parts, player_class=None, talents=None, common=""):
    """One login in a fresh Lua state: load the files in TOC order, fire the login events, run the parts."""
    global failed
    lua = lua51.LuaRuntime(unpack_returned_tuples=True)
    g = lua.globals()
    g.LOCALE, g.ADDON_VERSION = loc, version
    lua.execute(STUB)
    if player_class:
        # the class is read once at login: set it (and the talents) before ADDON_LOADED
        lua.execute(f'PLAYER_CLASS, PLAYER_TALENTS = "{player_class}", {talents}')
    else:
        # SavedVariables as the client provides them before ADDON_LOADED
        legacy = lua.execute(LEGACY)
        if loc == "deDE": g.ClassHelperLegacyDB = legacy
        else: g.ClassHelperDB = legacy  # variant: per-character file was not renamed
    for f in files:
        g.LoadAddonFile(open(f, encoding="utf-8-sig").read(), os.path.relpath(f, ROOT), "ClassHelper")
    g.FireEvent("ADDON_LOADED", "ClassHelper")
    g.LOGGEDIN = True
    g.FireEvent("PLAYER_LOGIN")
    g.FireEvent("PLAYER_ENTERING_WORLD")
    try:
        for name, part in parts:
            lua.execute(COMMON + common + part)
    except Exception as e:
        failed = True
        print(f"!!!!! {loc} {label} scenario '{name}' failed: {e}")
    out = list(g.OUT.values())
    for l in out:
        if l.startswith(PREFIXES): print("  " + l)
    errors = list(g.ERRORS.values())
    for e in errors: print("  LUA ERROR:", e)
    failed = failed or bool(errors)
    print(f"===== {loc} {label}: {len(files)} files, {len(out)} output lines, {len(errors)} Lua errors, unknown globals: {sorted(g.MISSING.keys())}")
    if loc == "enUS":
        bad = [l for l in out if GERMAN.search(l)]
        print("  German-looking lines in English output:", len(bad))
        for l in bad: print("    ", l)
    if "-v" in sys.argv:
        frames = g.FRAMES
        for k in sorted(k for k in frames.keys() if isinstance(k, str)):
            mt = frames[k]["__attr"]["macrotext"]
            if mt: print("  MACRO", k, "->", mt.replace(chr(10), " | "))
        for l in out: print("   ", l)


for loc in ("deDE", "enUS"):
    run(loc, "MAGE", MAGE_PARTS)
    for cls, talents, parts in CLASS_RUNS:
        run(loc, cls + " " + talents, parts, cls, talents, CLASSCOMMON)
sys.exit(1 if failed else 0)
