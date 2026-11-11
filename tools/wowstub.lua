-- Minimal WoW 3.3.5 API stub for smoke-testing MageHelper (incl. its embedded Ace3) outside the game.
-- Globals provided by the Python driver: LOCALE ("deDE"/"enUS"), ADDON_VERSION; it then calls
-- LoadAddonFile() for every file in TOC order and FireEvent("ADDON_LOADED"/"PLAYER_LOGIN").
OUT = {}
MISSING = {}
local now = 1000
function SetNow(t) now = t end

local SPELLS = {
  [44457]={"Lebende Bombe","Living Bomb"}, [42891]={"Pyroschlag","Pyroblast"},
  [42833]={"Feuerball","Fireball"}, [42873]={"Feuerschlag","Fire Blast"},
  [11129]={"Ein\195\164schern","Combustion"}, [55342]={"Spiegelbild","Mirror Image"},
  [45438]={"Eisblock","Ice Block"}, [2139]={"Gegenzauber","Counterspell"},
  [66]={"Unsichtbarkeit","Invisibility"}, [43046]={"Gl\195\188hende R\195\188stung","Molten Armor"},
  [43002]={"Arkane Brillanz","Arcane Brilliance"}, [54646]={"Fokusmagie","Focus Magic"},
  [69195]={"Stechende Seuche","Pungent Blight"}, [32182]={"Heldentum","Heroism"},
  [57399]={"Gut gen\195\164hrt","Well Fed"}, [54758]={"Hypergeschwindigkeitsbeschleunigung","Hyperspeed Acceleration"},
}
function GetLocale() return LOCALE end
function GetSpellInfo(x)
  if type(x) == "number" then
    local s = SPELLS[x]; if not s then return nil end
    return (LOCALE == "deDE") and s[1] or s[2], nil, "Interface\\Icons\\spell" .. x
  end
  return x, nil, "Interface\\Icons\\byname"
end
function GetItemInfo() return nil end           -- items not cached
function GetItemIcon(id) return "Interface\\Icons\\item" .. id end
function GetTime() return now end
function GetSpellCooldown() return 0, 0, 1 end
function GetInventoryItemCooldown() return 0, 0, 1 end
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
  if u == "player" then return { name = "Kahuchan", class = "MAGE" } end
  local i = type(u) == "string" and tonumber(u:match("^raid(%d+)$"))
  if i then return RAID[i] end
end

AURAS = { player = {} }   -- AURAS[unit] = { {name, count, expires, spellId, casterUnit}, ... }
function UnitBuff(unit, i)
  local a = AURAS[unit] and AURAS[unit][i]
  if not a then return nil end
  return a[1], nil, "icon", a[2] or 0, nil, 10, a[3] or (now + 10), a[5] or "player", nil, nil, a[4]
end
function UnitDebuff() return nil end
function UnitExists(u) return u == "target" or raidEntry(u) ~= nil end
function UnitIsDead() return false end
function UnitIsDeadOrGhost(u) local e = raidEntry(u); return e and e.dead or false end
function UnitCanAttack(a, b) return b == "target" end
function UnitIsFriend(a, b) return raidEntry(b) ~= nil end
function UnitIsPlayer(u) return raidEntry(u) ~= nil end
function UnitName(u)
  if u == "target" then return TARGETNAME or "Training Dummy" end
  local e = raidEntry(u); return e and e.name
end
function UnitIsUnit(a, b) return a == b or (UnitName(a) ~= nil and UnitName(a) == UnitName(b)) end
function UnitGUID(u)
  local e = raidEntry(u)
  if e and e.name == "Kahuchan" then return "GUID-player" end
  return e and ("GUID-" .. e.name) or ("GUID-" .. u)
end
function UnitClass(u) local e = raidEntry(u); if e then return e.class, e.class end end
function UnitIsConnected(u) local e = raidEntry(u); return e ~= nil and e.online ~= false end
function UnitAffectingCombat() return INCOMBAT end
function UnitCastingInfo() return nil end
function UnitChannelInfo() return nil end
function UnitDetailedThreatSituation() return false, 0, 10, 10 end
function GetUnitSpeed() return 0 end
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
  local t = inspect and INSPECTED and INSPECTED.talents or { 0, 0, 0 }
  return "Tab" .. tab, "icon", t[tab] or 0
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
function FRAME_SetScript(self, k, f) self.__scripts[k] = f end
function FRAME_GetScript(self, k) return self.__scripts[k] end
function FRAME_HookScript(self, k, f) self.__scripts[k] = f end
function FRAME_Show(self)
  if self.__shown then return end
  self.__shown = true
  if self.__scripts.OnShow then self.__scripts.OnShow(self) end
end
function FRAME_Hide(self)
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
function FRAME_SetTexture(self, t) self.__tex = t end
function FRAME_GetTexture(self) return self.__tex end
function FRAME_SetAttribute(self, k, v) self.__attr[k] = v end
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
function FRAME_SetWidth(self, w) self.__w = w end
function FRAME_SetHeight(self, h) self.__h = h end
function FRAME_GetWidth(self) return self.__w or 100 end
function FRAME_GetHeight(self) return self.__h or 20 end
function FRAME_GetName(self) return self.__name end
function FRAME_GetObjectType(self) return self.__kind end
function FRAME_SetParent(self, p) self.__parent = p end
function FRAME_GetParent(self) return self.__parent end
function FRAME_GetFrameLevel(self) return 1 end
function FRAME_GetStringWidth(self) return #tostring(self.__text or "") * 6 end
FRAMES = {}
function CreateFrame(kind, name, parent, template)
  local f = newObj(kind, name)
  f.__name = name; f.__parent = parent
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
