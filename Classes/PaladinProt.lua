-- ClassHelper: Protection Paladin rotation (phase 2 fills this in; see the spec's "Protection" part).
--
-- Contract (called by M.Pal.Update every 0.1 s while the Prot bar is shown):
--   M.PalProtReco(S) -> key, urgent, note
--     S     = M.PalState(): now, rota, aoe, usingPP, targetOK, targetHpPct, hpPct, manaPct, moving,
--             inCombat, sealWantedId, sealId, sealRemain, sealOK, rfWanted, rfActive, judgementId,
--             forbearance (add own fields as needed)
--     key   = a button key of M.ROTA_SETS.prot (hor, rd, dprot, loh, dshield, rf, seal, sealaoe, hs,
--             judge, hotr, cons, sor, how, avs, plea) or nil (no glow, one-button idle)
--     urgent = red glow instead of green; note = text for the info line (German key through M.L)
--   M.PalProtCombatLog(...) gets every combat log event (3.3.5 layout) while in Prot mode.
-- Buttons are secure with fixed macros; a new button needs an entry in M.PAL_BUTTONS and its key
-- in M.ROTA_SETS.prot (Paladin.lua). Settings: M.DEFAULTS.profile.<key> plus an option in
-- M.CLASS_OPTIONS (new group, hidden unless M.CLASS == "PALADIN"); texts: M.L_EN[german] = english.
local M = select(2, ...).M
if not M then return end

-- Reserved top slot 1: defensive cooldowns (Divine Protection / Lay on Hands / Divine Shield;
-- respect S.forbearance). Returns key, urgent, note or nil.
function M.PalProtDefensiveReco(S) return nil end

-- Reserved top slot 2: taunt (Hand of Reckoning "hor", Righteous Defense "rd" on the boss's target).
function M.PalProtTauntReco(S) return nil end

function M.PalProtCombatLog(...) end

function M.PalProtReco(S)
    local key, urgent, note = M.PalProtDefensiveReco(S)
    if key then return key, urgent, note end
    key, urgent, note = M.PalProtTauntReco(S)
    if key then return key, urgent, note end
    -- 969 rotation follows here (Righteous Fury, seal, Holy Shield, Judgement > HotR > Consecration > SoR, ...)
    return nil
end
