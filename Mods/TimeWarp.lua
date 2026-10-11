-- Time Warp: native Unreal world-speed control with presets, hotkeys, and persistent settings.
-- Drop into the Mods folder to install; delete to remove.
local function clamp(value)
    local n = tonumber(value)
    if not n or n ~= n or n == math.huge or n == -math.huge then return 1 end
    return math.floor(math.max(0.05, math.min(4, n)) * 100 + 0.5) / 100
end

local mod = {
    name = 'Time Warp',
    version = '2.3.0',
    author = 'Wood',
    description = 'Slow down tricky sections, practice at your own pace, and return to normal speed.',
}

local speed, enabled, restore_on_travel
local applied = 1
local api_ref  -- captured on first onWorldReady, used by hotkeys

local function gameplay() return StaticFindObject('/Script/Engine.Default__GameplayStatics') end
local function valid(o) return o and o:IsValid() end

local function save(api)
    api.set('speed', speed)
    api.set('enabled', enabled)
    api.set('restore_on_travel', restore_on_travel)
end

local function apply(api)
    local pc = api.playerController
    if not valid(pc) then return end
    gameplay():SetGlobalTimeDilation(pc, enabled and speed or 1)
    applied = gameplay():GetGlobalTimeDilation(pc)
    print(string.format('[Wood/TimeWarp] requested %.2fx, engine reports %.2fx\n', speed, applied))
end

local function set_speed(api, value)
    speed = clamp(value)
    apply(api)
    save(api)
    api.refreshSettings()
end

function mod.onWorldReady(api)
    api_ref = api
    speed = clamp(api.get('speed', 1))
    enabled = api.get('enabled', true)
    restore_on_travel = api.get('restore_on_travel', true)
    apply(api)
end

function mod.onTick(api)
    local pc = api.playerController
    if valid(pc) then applied = gameplay():GetGlobalTimeDilation(pc) end
end

function mod.buildSettings(api, panel)
    speed = clamp(api.get('speed', speed or 1))
    enabled = api.get('enabled', enabled ~= nil and enabled or true)
    restore_on_travel = api.get('restore_on_travel', restore_on_travel ~= nil and restore_on_travel or true)

    local speed_card = api.section(panel, 'SELECTED SPEED', nil)
    api.label(speed_card, string.format('%.2fx', speed), 30)
    api.label(speed_card,
        enabled and string.format('Applied to the world: %.2fx', applied)
               or 'Disabled  /  world running at normal speed', 13)
    api.slider(speed_card, 'Speed', 0.05, 4, 0.05, speed,
        function(v) set_speed(api, v) end,
        function(v) return string.format('%.2fx', v) end)

    local presets_card = api.section(panel, 'PRESETS', nil)
    for _, target in ipairs({0.1, 0.25, 0.5, 1, 2, 4}) do
        api.button(presets_card, string.format('%gx', target), function() set_speed(api, target) end)
    end

    local pref_card = api.section(panel, 'PREFERENCES', nil)
    api.toggle(pref_card, 'Time Warp enabled', enabled, function(v)
        enabled = v; apply(api); save(api); api.refreshSettings()
    end)
    api.toggle(pref_card, 'Reset speed on world change', restore_on_travel, function(v)
        restore_on_travel = v; save(api)
    end)

    api.label(panel, 'F6  Slower     F7  Normal     F8  Faster', 13)
    api.label(panel, 'Changes save automatically.', 12)
end

RegisterKeyBind(Key.F6, function()
    ExecuteInGameThread(function()
        if api_ref and enabled then set_speed(api_ref, speed / 2) end
    end)
end)
RegisterKeyBind(Key.F7, function()
    ExecuteInGameThread(function()
        if api_ref then set_speed(api_ref, 1) end
    end)
end)
RegisterKeyBind(Key.F8, function()
    ExecuteInGameThread(function()
        if api_ref and enabled then set_speed(api_ref, speed * 2) end
    end)
end)

return mod
