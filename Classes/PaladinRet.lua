-- ClassHelper: Retribution Paladin rotation (phase 2 fills this in; see the spec's "Retribution" part).
--
-- Contract (called by M.Pal.Update every 0.1 s while the Ret bar is shown):
--   M.PalRetReco(S) -> key, urgent, note
--     S     = M.PalState() (fields listed in PaladinProt.lua)
--     key   = a button key of M.ROTA_SETS.ret (seal, sealaoe, aw, judge, cs, dstorm, cons, how, exo,
--             hwrath, plea) or nil (no glow, one-button idle)
--     urgent = red glow instead of green; note = text for the info line (German key through M.L)
--   M.PalRetCombatLog(...) gets every combat log event (3.3.5 layout) while in Ret mode.
-- Righteous Fury active while not wanted is already shown (buff bar entry red, info line warning).
local M = select(2, ...).M
if not M then return end

function M.PalRetCombatLog(...) end

function M.PalRetReco(S)
    -- SimC 3.3 priority follows here (seal, Avenging Wrath, Judgement > CS > DS > Consecration > HoW > Exorcism (AoW) > Plea)
    return nil
end
