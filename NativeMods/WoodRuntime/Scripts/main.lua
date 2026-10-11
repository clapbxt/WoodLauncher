-- Wood: native Unreal UMG mod menu and an engine-backed time warp.
-- UObject operations are confined to the game thread. No process-memory writes.
local directory = debug.getinfo(1, 'S').source:sub(2):match('^(.*)[/\\]')
local root = dofile(directory .. '/paths.lua')
local data = root .. '/.wood/'
local function read_ini(path)
    local result = {}
    local file = io.open(path, 'r')
    if file then
        for line in file:lines() do
            local key, value = line:match('^([%w_]+)=(.*)$')
            if key then result[key] = value end
        end
        file:close()
    end
    return result
end
local settings = read_ini(data .. 'settings.ini')
local function clamp(value)
    local number = tonumber(value)
    if not number or number ~= number or number == math.huge or number == -math.huge then return 1 end
    return math.floor(math.max(0.05, math.min(4, number)) * 100 + 0.5) / 100
end
local speed = clamp(settings.speed or 1)
local enabled = settings.enabled ~= 'false'
local restore_on_travel = settings.restore_on_travel ~= 'false'
local last_command = ''
do -- Existing commands belong to previous sessions and must never be replayed.
    local file = io.open(data .. 'commands.log', 'r')
    if file then
        for line in file:lines() do last_command = line:match('^(%d+)|') or last_command end
        file:close()
    end
end
local error_message = ''
local pc, world_name, ui
local entry, entry_button
local ready = false
local applied = 1
local ticks = 0
local pending_tick = false
local pending_click
local selftest_result = ''
local extensions = {}
-- Local Lua mods register a settings page in the same native menu. Loading
-- failures are isolated so one extension cannot prevent Time Warp from loading.
for _, item in ipairs(dofile(directory .. '/extensions.lua')) do
    local ok, definition = true, {}
    if item.enabled ~= false then ok, definition = pcall(dofile, item.path) end
    if ok and type(definition) == 'table' then
        definition.id = item.id
        definition.name = definition.name or item.name
        definition.version = definition.version or item.version
        definition.description = definition.description or item.description
        definition.author = definition.author or item.author
        definition.enabled = item.enabled ~= false
        table.insert(extensions, definition)
    else
        table.insert(extensions, {id=item.id,name=item.name,version=item.version,author=item.author,
            description=item.description,enabled=false,error=tostring(definition)})
        print('[Wood] Could not load ' .. item.id .. ': ' .. tostring(definition) .. '\n')
    end
end

local function valid(object) return object and object:IsValid() end
local function save()
    local file = assert(io.open(data .. 'settings.ini', 'w'))
    file:write(string.format('speed=%.2f\nenabled=%s\nrestore_on_travel=%s\n',
        speed, tostring(enabled), tostring(restore_on_travel)))
    file:close()
end
local function gameplay() return StaticFindObject('/Script/Engine.Default__GameplayStatics') end
local function widget_library() return StaticFindObject('/Script/UMG.Default__WidgetBlueprintLibrary') end
local function set_speed(value)
    speed = clamp(value)
    if valid(pc) then
        gameplay():SetGlobalTimeDilation(pc, enabled and speed or 1)
        applied = gameplay():GetGlobalTimeDilation(pc)
        print(string.format('[Wood] Time Warp requested %.2fx, engine reports %.2fx\n', speed, applied))
    end
    save()
    if ui then ui:refresh_timewarp() end
end
local function extension_api(definition)
    local path = data .. definition.id .. '.settings.ini'
    return {
        playerController = pc,
        label = function(parent, label, size) return ui:label(parent, label, size) end,
        button = function(parent, label, callback)
            return ui:add_button(parent, label, callback)
        end,
        section = function(parent, title, description)
            local panel=ui:card(parent)
            ui:label(panel,title,20)
            if description then ui:label(panel,description,13) end
            return panel
        end,
        toggle = function(parent, label, value, callback)
            return ui:add_toggle(parent,label,value,callback)
        end,
        slider = function(parent, label, low, high, step, value, callback, format)
            return ui:add_slider(parent,label,low,high,step,value,callback,format)
        end,
        refreshSettings = function()
            if ui.visible and ui.selected==definition.id then ui:render_details() end
        end,
        get = function(key, default)
            local value = read_ini(path)[key]
            if value == nil then return default end
            if type(default) == 'boolean' then return value == 'true' end
            if type(default) == 'number' then return tonumber(value) or default end
            return value
        end,
        set = function(key, value)
            assert(tostring(key):match('^[%w_]+$'), 'Invalid settings key')
            assert(not tostring(value):find('[\r\n]'), 'Settings must be single-line values')
            local values = read_ini(path); values[key] = tostring(value)
            local file = assert(io.open(path, 'w'))
            for setting, saved in pairs(values) do file:write(setting .. '=' .. saved .. '\n') end
            file:close()
        end,
        log = function(message) print('[Wood/' .. definition.id .. '] ' .. tostring(message) .. '\n') end
    }
end
ui = dofile(directory .. '/menu.lua')({
    version='2.2.2', extensions=extensions, extension_api=extension_api,
    state=function() return {speed=speed,applied=applied,enabled=enabled,restore_on_travel=restore_on_travel} end,
    set_speed=set_speed,
    set_enabled=function(value) enabled=value; set_speed(speed) end,
    set_travel=function(value) restore_on_travel=value; save(); ui:refresh_timewarp() end
})
local function toggle_menu()
    if ui.visible then ui:hide() else ui:show(pc) end
    error_message=''
end
local function safe(callback)
    local ok, err = pcall(callback)
    if not ok then
        local message = tostring(err)
        if message ~= error_message then print('[Wood] ' .. message .. '\n') end
        error_message = message
    end
end
local function queue(callback) ExecuteInGameThread(function() safe(callback) end) end
RegisterKeyBind(Key.F10, function() queue(toggle_menu) end)
RegisterKeyBind(Key.ESCAPE, function() if ui.visible then queue(function() ui:escape() end) end end)
-- Native Slate widgets resolve hover and focus. Removed pages have no callbacks.
RegisterKeyBind(Key.LEFT_MOUSE_BUTTON, function()
    queue(function()
        -- Slate updates hover after input. Resolve the hit after it has processed
        -- the pointer move, so a fast click cannot activate the previous control.
        pending_click={due=ticks+2,visible=ui.visible,page=ui.selected}
    end)
end)
RegisterKeyBind(Key.RETURN, function() if ui.visible then queue(function() ui:key('return') end) end end)
RegisterKeyBind(Key.SPACE, function() if ui.visible then queue(function() ui:key('space') end) end end)
RegisterKeyBind(Key.F6, function() queue(function() if enabled and not ui:typing() then set_speed(speed / 2) end end) end)
RegisterKeyBind(Key.F7, function() queue(function() if not ui:typing() then set_speed(1) end end) end)
RegisterKeyBind(Key.F8, function() queue(function() if enabled and not ui:typing() then set_speed(speed * 2) end end) end)

local function apply_command(cmd)
    error_message = ''
    if cmd.action == 'speed' then set_speed(cmd.value)
    elseif cmd.action == 'reset' then set_speed(1)
    elseif cmd.action == 'enabled' then enabled = cmd.value == 'true'; set_speed(speed)
    elseif cmd.action == 'restore_on_travel' then restore_on_travel = cmd.value == 'true'; save()
    elseif cmd.action == 'menu' then toggle_menu()
    elseif cmd.action == 'selftest' then
        local original = gameplay():GetGlobalTimeDilation(pc)
        local pass = true
        for _, value in ipairs({0.05, 0.25, 0.5, 1, 2, 4}) do
            gameplay():SetGlobalTimeDilation(pc, value)
            local actual = gameplay():GetGlobalTimeDilation(pc)
            print(string.format('[Wood] SELFTEST %.2f -> %.2f\n', value, actual))
            if math.abs(actual - value) > 0.001 then pass = false end
        end
        gameplay():SetGlobalTimeDilation(pc, original)
        selftest_result = pass and 'passed' or 'failed'
    end
end
local function command()
    local file = io.open(data .. 'commands.log', 'r')
    if not file then return end
    for line in file:lines() do
        local id, action, value = line:match('^(%d+)|([%w_]+)|([^\r\n]*)$')
        if id and id > last_command then
            last_command = id
            safe(function() apply_command({id=id, action=action, value=value}) end)
        end
    end
    file:close()
end
local function quoted(value)
    return '"' .. tostring(value):gsub('\\', '\\\\'):gsub('"', '\\"'):gsub('[\r\n]', ' ') .. '"'
end
local function status()
    local file = io.open(data .. 'status.json', 'w')
    if not file then return end
    file:write(string.format('{"ready":%s,"speed":%.2f,"applied":%.4f,"enabled":%s,"restore_on_travel":%s,"menu":%s,"ack":%s,"error":%s,"selftest":%s}',
        tostring(ready), speed, applied, tostring(enabled), tostring(restore_on_travel), tostring(ui.visible), quoted(last_command),
        quoted(error_message), quoted(selftest_result)))
    file:close()
end
LoopAsync(16, function()
    if pending_tick then return false end
    pending_tick = true
    ExecuteInGameThread(function()
        safe(function()
            local current = FindFirstOf('PlayerController')
            ready = valid(current)
            if not ready then status(); return end
            local name = current:GetFullName()
            if name ~= world_name then
                pending_click=nil
                ui:invalidate()
                if valid(entry) then entry:RemoveFromParent() end
                local traveling = world_name ~= nil
                pc = current; world_name = name
                if traveling and restore_on_travel then speed = 1; save() end
                gameplay():SetGlobalTimeDilation(pc, enabled and speed or 1)
                entry, entry_button = ui:make_entry(pc)
                for _, definition in ipairs(extensions) do
                    if definition.enabled and type(definition.onWorldReady) == 'function' then
                        local ok, err = pcall(definition.onWorldReady, extension_api(definition))
                        if not ok then print('[Wood] ' .. definition.id .. ': ' .. tostring(err) .. '\n') end
                    end
                end
                print('[Wood] Attached to ' .. name .. '\n')
            end
            if pending_click and ticks>=pending_click.due then
                local click=pending_click; pending_click=nil
                if click.visible==ui.visible and click.page==ui.selected then
                    if ui.visible then ui:click()
                    elseif pc.bShowMouseCursor and valid(entry_button) and entry_button:IsHovered() then
                        ui:show(pc); error_message=''
                    end
                end
            end
            if ticks % 6 == 0 then command() end
            if ticks % 30 == 0 then
                for _, definition in ipairs(extensions) do
                    if definition.enabled and type(definition.onTick)=='function' then
                        local ok,err=pcall(definition.onTick,extension_api(definition))
                        if not ok and definition.tick_error~=tostring(err) then
                            definition.tick_error=tostring(err)
                            print('[Wood] '..definition.id..': '..tostring(err)..'\n')
                        elseif ok then definition.tick_error=nil end
                    end
                end
            end
            applied = gameplay():GetGlobalTimeDilation(pc)
            if valid(entry) then
                entry:SetVisibility(not ui.visible and pc.bShowMouseCursor and 0 or 2)
                if ticks % 30 == 0 then
                    local size = StaticFindObject('/Script/UMG.Default__WidgetLayoutLibrary'):GetViewportSize(pc)
                    entry:SetPositionInViewport({X=26,Y=size.Y-74}, true)
                    if ui.visible then ui:resize() end
                end
            end
            ui:tick()
        end)
        ticks = ticks + 1
        if ticks % 30 == 0 then safe(status) end
        pending_tick = false
    end)
    return false
end)
print('[Wood] Time Warp 2.2.2 loaded. F10 mods; F6 slower; F7 reset; F8 faster.\n')
