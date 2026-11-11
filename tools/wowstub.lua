-- Minimal WoW 3.3.5 API stub for smoke-testing MageHelper (incl. its embedded Ace3) outside the game.
-- Globals provided by the Python driver: LOCALE ("deDE"/"enUS"), ADDON_VERSION; it then calls
-- LoadAddonFile() for every file in TOC order and FireEvent("ADDON_LOADED"/"PLAYER_LOGIN").
OUT = {}
MISSING = {}
local now = 1000
function SetNow(t) now = t end

local SPELLS = {
  [44457]={"Lebende Bombe","Living Bomb"}, [42891]={"Pyroschlag","Pyroblast"},
  [42833]={"Feuerball","Fireball"}, [42832]={"Feuerball","Fireball"}, [133]={"Feuerball","Fireball"},
  [55360]={"Lebende Bombe","Living Bomb"}, [55362]={"Lebende Bombe","Living Bomb"}, [42873]={"Feuerschlag","Fire Blast"},
  [11129]={"Ein\195\164schern","Combustion"}, [55342]={"Spiegelbild","Mirror Image"},
  [45438]={"Eisblock","Ice Block"}, [2139]={"Gegenzauber","Counterspell"},
  [66]={"Unsichtbarkeit","Invisibility"}, [43046]={"Gl\195\188hende R\195\188stung","Molten Armor"},
  [43002]={"Arkane Brillanz","Arcane Brilliance"}, [54646]={"Fokusmagie","Focus Magic"},
  [69195]={"Stechende Seuche","Pungent Blight"}, [32182]={"Heldentum","Heroism"},
  [57399]={"Gut gen\195\164hrt","Well Fed"}, [54758]={"Hypergeschwindigkeitsbeschleunigung","Hyperspeed Acceleration"},
  [48263]={"Frostpr\195\164senz","Frost Presence"}, [9634]={"Terrorb\195\164rengestalt","Dire Bear Form"}, [5487]={"B\195\164rengestalt","Bear Form"},
  -- Arcane; cost/cast as GetSpellInfo returns them in 3.3.5 (4th and 7th value)
  [42897]={"Arkanschlag","Arcane Blast", cost=229, cast=2500}, [36032]={"Arkanschlag","Arcane Blast"},
  [42846]={"Arkane Geschosse","Arcane Missiles"}, [44781]={"Arkanbeschuss","Arcane Barrage"},
  [12042]={"Arkane Macht","Arcane Power"}, [12043]={"Geistesgegenwart","Presence of Mind"},
  [12472]={"Eisige Adern","Icy Veins"}, [12051]={"Hervorrufung","Evocation"}, [44401]={"Geschosssalve","Missile Barrage"},
  [30449]={"Zauberraub","Spellsteal"},
  -- Frost
  [42842]={"Frostblitz","Frostbolt"}, [42914]={"Eislanze","Ice Lance"}, [44572]={"Tiefk\195\188hlen","Deep Freeze"},
  [47610]={"Frostfeuerblitz","Frostfire Bolt"}, [11958]={"K\195\164lteeinbruch","Cold Snap"},
  [31687]={"Wasserelementar beschw\195\182ren","Summon Water Elemental"}, [74396]={"Eisige Finger","Fingers of Frost"},
  [44544]={"Eisige Finger","Fingers of Frost"}, [57761]={"Feuerball!","Fireball!"}, [42917]={"Frostnova","Frost Nova"},
  [33395]={"Einfrieren","Freeze"},
  -- Potion use spells (buffs, Runic Mana has none)
  [53908]={"Geschwindigkeit","Speed"}, [53909]={"Wilde Magie","Wild Magic"},
  [53762]={"Unzerst\195\182rbar","Indestructible"}, [43186]={"Mana wiederherstellen","Restore Mana"},
  -- Professor Putricide: Tear Gas cast and stun
  [71617]={"Tr95tnengas","Tear Gas"}, [71615]={"Tr95tnengas","Tear Gas"},
  [41425]={"Unterk\195\188hlung","Hypothermia"},
}
function GetLocale() return LOCALE end
function GetSpellInfo(x)
  if type(x) == "number" then
    local s = SPELLS[x]; if not s then return nil end
    return (LOCALE == "deDE") and s[1] or s[2], nil, "Interface\\Icons\\spell" .. x, s.cost or 0, false, 0, s.cast or 0
  end
  return x, nil, "Interface\\Icons\\byname"
end
function GetItemInfo() return nil end           -- items not cached
function GetItemIcon(id) return "Interface\\Icons\\item" .. id end
function GetTime() return now end
-- COOLDOWNS[spell name] / ITEM_COOLDOWNS[item ID] = seconds left (set by the test; GetTime() moves on)
COOLDOWNS, ITEM_COOLDOWNS = {}, {}
local function cd(left) if left and left > 0 then return now, left, 1 end return 0, 0, 1 end
function GetSpellCooldown(name) return cd(COOLDOWNS[name]) end
function GetItemCooldown(id) return cd(ITEM_COOLDOWNS[id]) end
-- KNOWN[spellId] = false makes a spell unknown (default: every spell is known)
KNOWN = {}
function IsSpellKnown(id) return KNOWN[id] ~= false end
-- SLOT_COOLDOWNS[slot] = seconds left on an equipped item; ITEM_USE[itemId] = name of its use effect
SLOT_COOLDOWNS, ITEM_USE = {}, {}
function GetInventoryItemCooldown(unit, slot) return cd(SLOT_COOLDOWNS[slot]) end
function GetItemSpell(id) return ITEM_USE[id] end
function GetManaRegen() return 0, 0 end      -- base, in combat (mana per second)
function GetAddOnMetadata(a, k) if k == "Version" then return ADDON_VERSION end end
function print(...)
  local t = {}
  for i = 1, select("#", ...) do t[#t+1] = tostring((select(i, ...))) end
  OUT[#OUT+1] = table.concat(t, " ")
end
function wipe(t) for k in pairs(t) do t[k] = nil end return t end
function date() return "12:00:00" end

-- WoW's Lua globals / helpers used by Ace3
format, strfind, strlower, strupper, strsub, strlen, strrep, gsub, strmatch, strbyte, strchar =
  string.format, string.find, string.lower, string.upper, string.sub, string.len, string.rep, string.gsub, string.match, string.byte, string.char
tremove, tconcat, sort = table.remove, table.concat, table.sort
floor, ceil, min, max, abs, mod = math.floor, math.ceil, math.min, math.max, math.abs, math.fmod
function strtrim(s) return (tostring(s):gsub("^%s+", ""):gsub("%s+$", "")) end
function strsplit(sep, s, limit)
  local out, pos = {}, 1
  while true do
    if limit and #out == limit - 1 then out[#out+1] = s:sub(pos); break end
    local a, b = s:find(sep, pos, true)
    if not a then out[#out+1] = s:sub(pos); break end
    out[#out+1] = s:sub(pos, a - 1); pos = b + 1
  end
  return unpack(out)
end
function strjoin(sep, ...) return table.concat({ ... }, sep) end
function tostringall(...) local t = { ... }; for i = 1, select("#", ...) do t[i] = tostring(t[i]) end; return unpack(t, 1, select("#", ...)) end
-- Ace calls addon code through xpcall(..., geterrorhandler()); collect those errors for the test.
ERRORS = {}
local errorhandler = function(e) ERRORS[#ERRORS+1] = tostring(e) .. "\n" .. debug.traceback("", 2); return e end
function geterrorhandler() return errorhandler end
function seterrorhandler(f) errorhandler = f end
function hooksecurefunc(a, b, c)
  local t, name, hook = _G, a, b
  if type(a) == "table" then t, name, hook = a, b, c end
  local orig = t[name]
  t[name] = function(...) local r = { orig(...) }; hook(...); return unpack(r) end
end
function securecall(f, ...) if type(f) == "string" then f = _G[f] end return f(...) end
function issecurevariable() return false end
function debugstack() return "" end
LOGGEDIN = false
function IsLoggedIn() return LOGGEDIN end
function GetRealmName() return "Rising-Gods" end
function UnitRace() return "Gnom", "Gnome" end
function UnitFactionGroup() return "Alliance", "Allianz" end
function GetScreenWidth() return 1920 end
function GetScreenHeight() return 1080 end
function GetCursorPosition() return 0, 0 end
function PlaySound() end
function GetCVar() return nil end
function InterfaceOptions_AddCategory(f) OPTIONS_CATEGORIES = (OPTIONS_CATEGORIES or 0) + 1 end
function InterfaceOptionsFrame_OpenToCategory(f) OPTIONS_OPENED = f end
DEFAULT_CHAT_FRAME = { AddMessage = function(self, m) OUT[#OUT+1] = tostring(m) end }
ChatFrame1 = DEFAULT_CHAT_FRAME

-- Raid roster for tests: RAID[i] = {name=, class=, talents={a,b,c}, online=, dead=, range=}.
-- RAID[1] should be the player ("Kahuchan"). Empty = solo.
RAID = {}
local function raidEntry(u)
  if u == "player" then return { name = "Kahuchan", class = PLAYER_CLASS or "MAGE" } end
  local i = type(u) == "string" and tonumber(u:match("^raid(%d+)$"))
  if i then return RAID[i] end
end

AURAS = { player = {} }   -- AURAS[unit] = { {name, count, expires, spellId, casterUnit}, ... }
function UnitBuff(unit, i)
  local a = AURAS[unit] and AURAS[unit][i]
  if not a then return nil end
  return a[1], nil, "icon", a[2] or 0, nil, 10, a[3] or (now + 10), a[5] or "player", nil, nil, a[4]
end
DEBUFFS = { player = {} } -- same format as AURAS
function UnitDebuff(unit, i)
  local a = DEBUFFS[unit] and DEBUFFS[unit][i]
  if not a then return nil end
  return a[1], nil, "icon", a[2] or 0, nil, 10, a[3] or (now + 10), a[5] or "player", nil, nil, a[4]
end
-- UnitAura(unit, i, "HELPFUL"/"HARMFUL") reads AURAS/DEBUFFS; the 6th field is isStealable, returned
-- as the 9th value like 3.3.5 does (1 or nil). The icon is "aura<spellId>".
AURA_CALLS = 0
function UnitAura(unit, i, filter)
  AURA_CALLS = AURA_CALLS + 1
  local src = (filter and filter:find("HARMFUL", 1, true)) and DEBUFFS or AURAS
  local a = src[unit] and src[unit][i]
  if not a then return nil end
  return a[1], nil, "aura" .. tostring(a[4]), a[2] or 0, "Magic", 10, a[3] or (now + 10), a[5] or "player", a[6], nil, a[4]
end
-- RANGE[unit] = 0 makes IsSpellInRange report out of range (default 1 for an existing unit)
RANGE, USABLE = {}, {}
function IsSpellInRange(spell, unit) if not UnitExists(unit) then return nil end return RANGE[unit] or 1 end
function IsUsableSpell(spell) if USABLE[spell] == false then return nil, 1 end return 1, nil end
-- mana and target health for the Arcane rotation
PLAYER_MANA, PLAYER_MANA_MAX, TARGET_HP = 30000, 30000, 100
function UnitPower(u) if u == "player" then return PLAYER_MANA end return 0 end
function UnitPowerMax(u) if u == "player" then return PLAYER_MANA_MAX end return 0 end
-- boss frames: BOSSES.boss1 = { name=, hp=, attackable= }; a target named like a boss is that boss
BOSSES = {}
function UnitHealth(u)
  if u == "target" then return TARGET_HP end
  if BOSSES[u] then return BOSSES[u].hp or 100 end
  if u == "focus" and FOCUS then return FOCUS.hp or 100 end
  return 100
end
function UnitHealthMax() return 100 end
-- focus: FOCUS = { name=, hostile=, dead=, guid=, hp= } or nil (no focus); PET = true while the player's pet (Water Elemental) is out
PET = false
function UnitExists(u) return (u == "target" and not NOTARGET) or (u == "focus" and FOCUS ~= nil) or (u == "pet" and PET == true) or raidEntry(u) ~= nil or BOSSES[u] ~= nil end
function UnitIsDead(u)
  if u == "focus" then return FOCUS ~= nil and FOCUS.dead or false end
  if u == "target" then return TARGET_DEAD == true end
  return BOSSES[u] ~= nil and BOSSES[u].dead or false
end
function UnitIsDeadOrGhost(u) local e = raidEntry(u); return e and e.dead or false end
function UnitCanAttack(a, b)
  if BOSSES[b] then return BOSSES[b].attackable ~= false end
  if b == "focus" then return FOCUS ~= nil and FOCUS.hostile ~= false end
  return b == "target" and not NOTARGET and not TARGET_FRIENDLY
end
function UnitIsFriend(a, b) return raidEntry(b) ~= nil end
function UnitIsPlayer(u) return raidEntry(u) ~= nil end
function UnitName(u)
  if u == "target" then return TARGETNAME or "Training Dummy" end
  if u == "focus" then return FOCUS and FOCUS.name end
  if BOSSES[u] then return BOSSES[u].name end
  local e = raidEntry(u); return e and e.name
end
function UnitIsUnit(a, b) return a == b or (UnitName(a) ~= nil and UnitName(a) == UnitName(b)) end
function UnitGUID(u)
  if u == "target" then return TARGETGUID or ("GUID-" .. (TARGETNAME or "target")) end
  if BOSSES[u] then return BOSSES[u].guid or ("GUID-" .. BOSSES[u].name) end
  if u == "focus" and FOCUS and FOCUS.guid then return FOCUS.guid end
  local e = raidEntry(u)
  if e and e.name == "Kahuchan" then return "GUID-player" end
  return e and ("GUID-" .. e.name) or ("GUID-" .. u)
end
function UnitClass(u) local e = raidEntry(u); if e then return e.class, e.class end end
function UnitIsConnected(u) local e = raidEntry(u); return e ~= nil and e.online ~= false end
-- BOSSES[u].combat = true/false overrides INCOMBAT for that boss (player out of combat, boss still fighting)
function UnitAffectingCombat(u)
  if BOSSES[u] and BOSSES[u].combat ~= nil then return BOSSES[u].combat end
  return INCOMBAT
end
-- CASTING[unit] = { name, startMS, endMS } (3.3.5: name, subText, text, icon, startTime, endTime, ...; no spell ID)
CASTING = {}
function UnitCastingInfo(u)
  local c = CASTING[u]
  if c then return c[1], nil, c[1], "icon", c[2], c[3], false, 1, false end
end
function UnitChannelInfo(u) if u == "player" then return CHANNEL end end
-- THREAT[unit] = { isTanking, status, scaledPercent, rawPercent } on that mob (default: low threat)
THREAT = {}
function UnitDetailedThreatSituation(u, mob)
  local t = THREAT[mob]
  if t then return t[1], t[2], t[3], t[4] end
  return false, 0, 10, 10
end
-- instance: INSTANCE = { type = "raid", difficulty = 1-4, dynamic = 0/1, isDynamic = true } (default: outside)
INSTANCE = nil
function GetInstanceInfo()
  local i = INSTANCE
  if not i then return "World", "none", 1, "", 5, 0, false end
  return "Icecrown Citadel", i.type or "raid", i.difficulty, "", i.difficulty == 2 and 25 or 10, i.dynamic or 0, i.isDynamic ~= false
end
function GetInstanceDifficulty() return INSTANCE and INSTANCE.difficulty or 1 end
function GetUnitSpeed() return MOVING and 7 or 0 end
function InCombatLockdown() return INCOMBAT and true or false end
function GetNumRaidMembers() return #RAID end
function GetNumPartyMembers() return 0 end

-- inspection: NotifyInspect remembers the unit; the test fires INSPECT_TALENT_READY itself
INSPECT_PENDING = false
INSPECT_COUNT = 0
function CanInspect(u) return raidEntry(u) ~= nil end
function CheckInteractDistance(u) local e = raidEntry(u); return e ~= nil and e.range ~= false end
function NotifyInspect(u) INSPECTED = raidEntry(u); INSPECT_PENDING = true; INSPECT_COUNT = INSPECT_COUNT + 1 end
function GetActiveTalentGroup() return 1 end
function GetTalentTabInfo(tab, inspect)
  local t = (inspect and INSPECTED and INSPECTED.talents) or (not inspect and PLAYER_TALENTS) or { 0, 0, 0 }
  return "Tab" .. tab, "icon", t[tab] or 0
end

-- equipment and bags: EQUIPPED[slot] = item link, BAGS[bag][i] = item link
EQUIPPED, BAGS = {}, { [0] = {} }
function time() return math.floor(now) end
function GetInventoryItemLink(unit, slot) if unit == "player" then return EQUIPPED[slot] end end
function GetContainerNumSlots(bag) return BAGS[bag] and 16 or 0 end
function GetContainerItemLink(bag, i) return BAGS[bag] and BAGS[bag][i] end
local function itemId(link) return link and tonumber(tostring(link):match("item:(%d+)")) end
-- like the client: the item from the bags goes into the slot, the worn item takes its bag place
function EquipItemByName(item, slot)
  if INCOMBAT then error("EquipItemByName: armor can't be swapped in combat") end
  local want = itemId(item)
  for bag, items in pairs(BAGS) do
    for i = 1, 16 do
      if items[i] and itemId(items[i]) == want then
        items[i], EQUIPPED[slot] = EQUIPPED[slot], items[i]
        EQUIP_COUNT = (EQUIP_COUNT or 0) + 1
        return
      end
    end
  end
end

-- shapeshift form (death knight presence, druid form): PLAYER_FORM = spell ID of the active form
function GetShapeshiftForm() return PLAYER_FORM and 1 or 0 end
function GetShapeshiftFormInfo(i) if i == 1 and PLAYER_FORM then return "icon", GetSpellInfo(PLAYER_FORM), true, true end end
-- ITEM_CHARGES[id] = charges reported with includeCharges (3rd argument), e.g. the Mana Sapphire's 3
ITEM_CHARGES = {}
function GetItemCount(id, includeBank, includeCharges)
  if includeCharges and ITEM_CHARGES[id] then return ITEM_CHARGES[id] end
  local n = 0
  for _, items in pairs(BAGS) do for i = 1, 16 do if items[i] and itemId(items[i]) == id then n = n + 1 end end end
  return n
end

-- FrameXML helpers used by the picker
function FauxScrollFrame_Update(f, total) f.__total = total end
function FauxScrollFrame_GetOffset(f) return f.__offset or 0 end
function FauxScrollFrame_SetOffset(f, o) f.__offset = o end
function FauxScrollFrame_OnVerticalScroll(f, value, h, fn) f.__offset = math.floor(value / h + 0.5); fn() end
RAID_CLASS_COLORS = setmetatable({}, { __index = function() return { r = 1, g = 1, b = 1 } end })
UISpecialFrames = {}
tinsert = table.insert
function RunMacroText(m) OUT[#OUT+1] = "RUNMACRO " .. m end
function CastSpellByName() end
SlashCmdList = {}

-- frames
local function newObj(kind, name)
  local o = { __kind = kind, __scripts = {}, __attr = {}, __shown = true, __text = "", __points = {}, __events = {} }
  return setmetatable(o, { __index = function(t, k)
    local f = rawget(_G, "FRAME_" .. k)
    if f then return f end
    if type(k) == "string" and k:match("^%u") then return function() end end
    return nil
  end })
end
-- Like the client: protected frames (SecureActionButtonTemplate and every frame that holds one,
-- e.g. the main bar MageHelperFrame) can't be shown, hidden, moved, resized, scaled, reparented or
-- get attributes in combat.
local function guard(self, what)
  if self.__protected and INCOMBAT then
    error("ADDON_ACTION_BLOCKED: " .. tostring(self.__name or self.__kind) .. ":" .. what .. "() in combat", 3)
  end
end
-- A frame becomes protected when a protected frame is parented to it (and so do its parents) or
-- anchored to it.
local function protect(f)
  while type(f) == "table" and f ~= UIParent do f.__protected = true; f = f.__parent end
end
function FRAME_SetScript(self, k, f) self.__scripts[k] = f end
function FRAME_GetScript(self, k) return self.__scripts[k] end
function FRAME_HookScript(self, k, f) self.__scripts[k] = f end
function FRAME_Show(self)
  guard(self, "Show")
  if self.__shown then return end
  self.__shown = true
  if self.__scripts.OnShow then self.__scripts.OnShow(self) end
end
function FRAME_Hide(self)
  guard(self, "Hide")
  if not self.__shown then return end
  self.__shown = false
  if self.__scripts.OnHide then self.__scripts.OnHide(self) end
end
function FRAME_SetChecked(self, v) self.__checked = v end
function FRAME_GetChecked(self) return self.__checked end
function FRAME_Enable(self) self.__enabled = true end
function FRAME_Disable(self) self.__enabled = false end
function FRAME_IsShown(self) return self.__shown end
function FRAME_SetText(self, t) self.__text = t end
function FRAME_GetText(self) return self.__text end
function FRAME_SetTexture(self, t, g, b, a) self.__tex = t; if g then self.__rgba = { t, g, b, a } end end
function FRAME_SetVertexColor(self, r, g, b, a) self.__vc = { r, g, b, a } end
function FRAME_SetTextColor(self, r, g, b, a) self.__tc = { r, g, b, a } end
function FRAME_GetTexture(self) return self.__tex end
function FRAME_SetAttribute(self, k, v) guard(self, "SetAttribute"); self.__attr[k] = v end
function FRAME_SetPoint(self, point, rel, ...)
  guard(self, "SetPoint")
  if type(rel) == "string" then rel = rawget(_G, rel) end
  if self.__protected and type(rel) == "table" then protect(rel) end
end
function FRAME_SetAllPoints(self, rel)
  guard(self, "SetAllPoints")
  if type(rel) == "string" then rel = rawget(_G, rel) end
  if self.__protected and type(rel) == "table" then protect(rel) end
end
function FRAME_ClearAllPoints(self) guard(self, "ClearAllPoints") end
function FRAME_GetAttribute(self, k) return self.__attr[k] end
function FRAME_GetPoint(self) return "CENTER", nil, "CENTER", 0, 0 end
function FRAME_CreateTexture(self) return newObj("Texture") end
function FRAME_CreateFontString(self) return newObj("FontString") end
function FRAME_AddLine(self, t) OUT[#OUT+1] = "TIP " .. tostring(t) end
function FRAME_RegisterEvent(self, e) self.__events[e] = true end
function FRAME_UnregisterEvent(self, e) self.__events[e] = nil end
function FRAME_UnregisterAllEvents(self) self.__events = {} end
function FRAME_IsEventRegistered(self, e) return self.__events[e] and 1 or nil end
function FRAME_IsVisible(self) return self.__shown end
function FRAME_SetWidth(self, w) guard(self, "SetWidth"); self.__w = w end
function FRAME_SetHeight(self, h) guard(self, "SetHeight"); self.__h = h end
function FRAME_SetScale(self, s) guard(self, "SetScale"); self.__scale = s end
function FRAME_GetScale(self) return self.__scale or 1 end
function FRAME_GetWidth(self) return self.__w or 100 end
function FRAME_GetHeight(self) return self.__h or 20 end
function FRAME_GetName(self) return self.__name end
function FRAME_GetObjectType(self) return self.__kind end
function FRAME_SetParent(self, p)
  guard(self, "SetParent")
  if type(p) == "string" then p = rawget(_G, p) end
  self.__parent = p
  if self.__protected then protect(p) end
end
function FRAME_GetParent(self) return self.__parent end
function FRAME_GetFrameLevel(self) return 1 end
function FRAME_GetStringWidth(self) return #tostring(self.__text or "") * 6 end
FRAMES = {}
function CreateFrame(kind, name, parent, template)
  local f = newObj(kind, name)
  f.__name = name; f.__parent = parent
  if template and tostring(template):find("SecureActionButtonTemplate", 1, true) then protect(f) end
  if name then _G[name] = f; FRAMES[name] = f end
  if template == "UICheckButtonTemplate" and name then _G[name .. "Text"] = newObj("FontString") end
  FRAMES[#FRAMES+1] = f
  return f
end
-- Dispatch an event to every frame that registered it (AceEvent, AceAddon, ...).
function FireEvent(e, ...)
  local list = {}
  for i = 1, #FRAMES do list[i] = FRAMES[i] end
  for _, f in ipairs(list) do
    if f.__events[e] and f.__scripts.OnEvent then f.__scripts.OnEvent(f, e, ...) end
  end
end
-- Advance time and run OnUpdate of all shown frames (AceTimer, glow pulse, FM picker).
function Tick(dt)
  SetNow(GetTime() + dt)
  local list = {}
  for i = 1, #FRAMES do list[i] = FRAMES[i] end
  for _, f in ipairs(list) do
    if f.__shown and f.__scripts.OnUpdate then f.__scripts.OnUpdate(f, dt) end
  end
end
UIParent = newObj("Frame", "UIParent")
Minimap = newObj("Frame", "Minimap")
GameTooltip = newObj("GameTooltip", "GameTooltip")
function GameTooltip.SetText(self, t) OUT[#OUT+1] = "TIP " .. tostring(t) end

-- Unknown globals: record and return nil (catches typos / APIs the stub lacks)
setmetatable(_G, { __index = function(t, k)
  if type(k) == "string" and not k:match("^MageHelper") and not k:match("^SLASH_") and not k:match("^FRAME_") then
    MISSING[k] = true
  end
  return nil
end })

local addonTable = {}
function LoadAddonFile(code, name, addonName)
  local fn, err = loadstring(code, "@" .. name)
  if not fn then error("SYNTAX: " .. err) end
  fn(addonName, addonTable)
end
