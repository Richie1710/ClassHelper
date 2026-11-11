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
FireEvent("COMBAT_LOG_EVENT_UNFILTERED", 0, "SPELL_CAST_SUCCESS", nil, "GUID-player", "Kahuchan", 0, 0, "GUID-target", "Dummy", 0, 0, 42833, GetSpellInfo(42833), 4)
FireEvent("COMBAT_LOG_EVENT_UNFILTERED", 0, "SPELL_DAMAGE", nil, "GUID-target", "Dummy", 0, 0, "GUID-player", "Kahuchan", 0, 0, 1, "Hit", 1, 500, 0)
FireEvent("COMBAT_LOG_EVENT_UNFILTERED", 0, "SWING_DAMAGE", nil, "GUID-target", "Dummy", 0, 0, "GUID-player", "Kahuchan", 0, 0, 300, 0)
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
local function drain(hpPerSec, seconds) for i = 1, seconds / 0.15 do TARGET_HP = TARGET_HP - hpPerSec * 0.15; Tick(0.15) end end
local function debug() return KR.debugInfo.__text end

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
INCOMBAT = true; FireEvent("PLAYER_REGEN_DISABLED"); state(30000, 0); upd()
check(reco() == "pom", "Presence of Mind first: " .. tostring(reco()))
COOLDOWNS[POM] = 100; upd(); check(reco() == "ap", "then Arcane Power")
COOLDOWNS[AP] = 100; upd(); check(reco() == "ap", "AP on CD, Icy Veins ready: AP button (macro casts both)")
COOLDOWNS[IV] = 100; upd(); check(reco() == "mirror", "then Mirror Image")
COOLDOWNS[POM], COOLDOWNS[AP] = nil, nil
EQUIPPED = { [1] = "|Hitem:51281|h[x]|h", [3] = "|Hitem:51155|h[x]|h", [5] = "|Hitem:50278|h[x]|h", [7] = "|Hitem:51282|h[x]|h" }
upd(); check(reco() == "mirror", "T10 4-piece: Mirror Image before PoM/AP")
EQUIPPED = {}
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

-- Mana Gem only when the missing mana >= its yield; Evocation below 30% without stacks
ITEM_COOLDOWNS[33312] = nil
state(27000, 0); upd(); check(reco() == "ab", "3000 missing: no gem yet")
state(26000, 0); upd(); check(reco() == "gem", "4000 missing: Mana Gem")
ITEM_COOLDOWNS[33312] = 60; COOLDOWNS[EVO] = nil
state(6000, 2); upd(); check(reco() == "abarr", "20% with stacks: drop them with Arcane Barrage first")
state(6000, 0); upd(); check(reco() == "evo", "20% without stacks: Evocation")
COOLDOWNS[EVO] = 100

-- moving
MOVING = true; state(20000, 0); upd(); check(reco() == "abarr", "moving: Arcane Barrage")
COOLDOWNS[BARR] = 2; upd(); check(reco() == "fb_move", "moving, Barrage on CD: Fire Blast")
MOVING, COOLDOWNS[BARR] = false, nil
OUT[#OUT + 1] = "ARCANE INFO " .. KR.info.__text

-- burn auto: time to die vs time to OOM (18000 mana, gem and Evocation on CD: about 25 s of burning)
Slash("burn auto"); Slash("debug on")
check(MH.db.profile.arcaneBurnMode == "auto" and MH.db.profile.arcaneBurnMana == 35, "/mh burn auto keeps the threshold")
TARGETNAME, TARGET_HP = "Fast boss", 60; state(18000, 3); upd(4)
check(reco() == "ab", "new target, estimate unreliable: mana threshold (60%) -> burn")
check(debug():find(de and "unsicher" or "unreliable", 1, true), "debug line says why: " .. debug())
drain(5, 6)   -- 5%/s: dies in ~6 s, the mana lasts longer
check(reco() == "ab" and debug():find("TTD", 1, true), "fast kill: burn (" .. debug() .. ")")
OUT[#OUT + 1] = "ARCANE DEBUG " .. debug()
TARGETNAME, TARGET_HP = "Slow boss", 60; upd(2)
check(reco() == "ab", "target change resets the samples: fallback burn")
drain(0.5, 8) -- 0.5%/s: ~110 s left, the mana lasts ~25 s
check(reco() == "am", "slow kill: conserve, 3 stacks -> Arcane Missiles (" .. debug() .. ")")
OUT[#OUT + 1] = "ARCANE DEBUG " .. debug()
drain(0, 5)   -- health stops dropping (immune phase): unreliable, back to the mana threshold
check(reco() == "ab" and debug():find(de and "unsicher" or "unreliable", 1, true), "stalled health: fallback burn (" .. debug() .. ")")
Slash("burn mana"); drain(0.5, 2)
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
PLAYER_TALENTS = { 0, 17, 54 }; FireEvent("PLAYER_TALENT_UPDATE"); check(shown("lb"), "Frost uses Fire")
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
        for name, part in (("migration", MIGRATION), ("main", SCRIPT), ("options", OPTIONS), ("picker", PICKER), ("t9", T9), ("themes", THEMES), ("flask", FLASK), ("arcane", ARCANE)):
            lua.execute(COMMON + part)
    except Exception as e:
        failed = True
        print(f"!!!!! {loc} scenario '{name}' failed: {e}")
    out = list(g.OUT.values())
    for l in out:
        if l.startswith(("ROWS", "LABEL", "STATUS", "PICKER", "MIGRATION", "OPTIONS", "T9", "THEMES", "FLASK", "ARCANE", "|cffff7d0aMageHelper v")): print("  " + l)
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
