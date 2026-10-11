-- Wood: native Unreal UMG mod loader and in-game menu host.
-- UObject operations are confined to the game thread. No process-memory writes.
local directory = debug.getinfo(1, 'S').source:sub(2):match('^(.*)[/\\]')
local root = dofile(directory .. '/paths.lua')
local data = root .. '/.wood/'
local package_reader = dofile(directory .. '/mod_package.lua')
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
local error_message = ''
local pc, world_name, ui
local entry, entry_button
local ready = false
local ticks = 0
local pending_tick = false
local pending_click
local mods = {}
-- Scan the Mods folder at boot. Each .lua or .tungmod file is a self-contained mod.
-- Failures are isolated so one bad mod cannot prevent the menu from loading.
local function scan_mods()
    local mods_dir = root .. '/Mods'
    local disabled_file = io.open(data .. 'mods_disabled.txt', 'r')
    local disabled = {}
    if disabled_file then
        for line in disabled_file:lines() do disabled[line:match('^%s*(.-)%s*$')] = true end
        disabled_file:close()
    end
    local handle = io.popen('dir /b /a-d "' .. mods_dir:gsub('/', '\\') .. '" 2>nul')
    if not handle then
        print('[Wood] Could not scan Mods folder: ' .. mods_dir .. '\n')
        return
    end
    local files, packaged_stems, loaded_ids = {}, {}, {}
    for filename in handle:lines() do
        files[#files+1] = filename
        local stem, extension = filename:match('^(.+)%.([%w]+)$')
        if extension and extension:lower() == 'tungmod' then packaged_stems[stem:lower()] = true end
    end
    handle:close()
    table.sort(files, function(a, b)
        local ap, bp = a:lower():match('%.tungmod$') ~= nil, b:lower():match('%.tungmod$') ~= nil
        if ap ~= bp then return ap end
        return a:lower() < b:lower()
    end)
    for _, filename in ipairs(files) do
        local file_id, extension = filename:match('^(.+)%.([%w]+)$')
        extension = extension and extension:lower()
        if file_id and (extension == 'lua' or extension == 'tungmod') and not file_id:match('^_')
            and not (extension == 'lua' and packaged_stems[file_id:lower()]) then
            local path = mods_dir .. '/' .. filename
            local mod_id = file_id
            local metadata, source, icon_path
            local ok, definition = pcall(function()
                if extension == 'tungmod' then
                    metadata, source, icon_path = package_reader.read(path, data .. 'mod_', loaded_ids)
                    mod_id = metadata.id
                    if loaded_ids[mod_id] then error('Duplicate mod ID: ' .. mod_id) end
                    if disabled[mod_id] then return {} end
                    local chunk, err = load(source, '@' .. path)
                    if not chunk then error(err) end
                    local result = chunk()
                    if type(result) ~= 'table' then error('Mod source must return a table.') end
                    result.id = metadata.id
                    result.name = metadata.name
                    result.version = metadata.version
                    result.author = metadata.author
                    result.description = metadata.description
                    result.iconPath = icon_path
                    return result
                end
                if disabled[mod_id] then return {} end
                local result = dofile(path)
                if type(result) ~= 'table' then error('Mod source must return a table.') end
                return result
            end)
            local enabled = not disabled[mod_id]
            if ok and type(definition) == 'table' then
                definition.id = metadata and metadata.id or definition.id or mod_id
                definition.name = metadata and metadata.name or definition.name or mod_id
                definition.version = metadata and metadata.version or definition.version or '1.0'
                definition.author = metadata and metadata.author or definition.author or 'Unknown'
                definition.description = metadata and metadata.description or definition.description or ''
                definition.iconPath = icon_path or definition.iconPath
                definition.enabled = enabled
                if not loaded_ids[definition.id] then
                    loaded_ids[definition.id] = true
                    table.insert(mods, definition)
                    print('[Wood] Loaded ' .. filename .. ' as ' .. definition.id .. '\n')
                else
                    print('[Wood] Skipped duplicate mod ID in ' .. filename .. '\n')
                end
            else
                if not loaded_ids[mod_id] then
                    table.insert(mods, {id=mod_id, name=mod_id, version='1.0', author='Unknown',
                        description='', enabled=false, error=tostring(definition)})
                end
                print('[Wood] Could not load ' .. mod_id .. ': ' .. tostring(definition) .. '\n')
            end
        end
    end
end
scan_mods()

local function valid(object) return object and object:IsValid() end
local function mod_api(definition)
    local path = data .. definition.id .. '.settings.ini'
    return {
        playerController = pc,
        label = function(parent, label, size) return ui:label(parent, label, size) end,
        button = function(parent, label, callback) return ui:add_button(parent, label, callback) end,
        input = function(parent, hint, initial) return ui:input(parent, hint, initial, 'details') end,
        section = function(parent, title, description)
            local panel = ui:card(parent)
            ui:label(panel, title, 20)
            if description then ui:label(panel, description, 13) end
            return panel
        end,
        toggle = function(parent, label, value, callback) return ui:add_toggle(parent, label, value, callback) end,
        slider = function(parent, label, low, high, step, value, callback, format)
            return ui:add_slider(parent, label, low, high, step, value, callback, format)
        end,
        refreshSettings = function()
            if ui.visible and ui.selected == definition.id then ui:render_details() end
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
    version='2.3.2', mods=mods, mod_api=mod_api, logoPath=data .. 'wood-logo.png',
    loadIcon=function(path)
        local rendering = StaticFindObject('/Script/Engine.Default__KismetRenderingLibrary')
        return rendering:ImportFileAsTexture2D(pc, path)
    end,
})
local function toggle_menu()
    if ui.visible then ui:hide() else ui:show(pc) end
    error_message = ''
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
RegisterKeyBind(Key.LEFT_MOUSE_BUTTON, function()
    queue(function()
        pending_click = {due=ticks+2, visible=ui.visible, page=ui.selected}
    end)
end)
RegisterKeyBind(Key.RETURN, function() if ui.visible then queue(function() ui:key('return') end) end end)
RegisterKeyBind(Key.SPACE, function() if ui.visible then queue(function() ui:key('space') end) end end)

LoopAsync(16, function()
    if pending_tick then return false end
    pending_tick = true
    ExecuteInGameThread(function()
        safe(function()
            local current = FindFirstOf('PlayerController')
            ready = valid(current)
            if not ready then return end
            local name = current:GetFullName()
            if name ~= world_name then
                pending_click = nil
                ui:invalidate()
                if valid(entry) then entry:RemoveFromParent() end
                local traveling = world_name ~= nil
                pc = current; world_name = name
                entry, entry_button = ui:make_entry(pc)
                for _, definition in ipairs(mods) do
                    if definition.enabled and type(definition.onWorldReady) == 'function' then
                        local ok, err = pcall(definition.onWorldReady, mod_api(definition))
                        if not ok then print('[Wood] ' .. definition.id .. ': ' .. tostring(err) .. '\n') end
                    end
                end
                print('[Wood] Attached to ' .. name .. '\n')
            end
            if pending_click and ticks >= pending_click.due then
                local click = pending_click; pending_click = nil
                if click.visible == ui.visible and click.page == ui.selected then
                    if ui.visible then ui:click()
                    elseif pc.bShowMouseCursor and valid(entry_button) and entry_button:IsHovered() then
                        ui:show(pc); error_message = ''
                    end
                end
            end
            for _, definition in ipairs(mods) do
                local interval = tonumber(definition.tickInterval) or 30
                interval = math.max(1, math.floor(interval))
                if definition.enabled and type(definition.onTick) == 'function' and ticks % interval == 0 then
                    local ok, err = pcall(definition.onTick, mod_api(definition))
                    if not ok and definition.tick_error ~= tostring(err) then
                        definition.tick_error = tostring(err)
                        print('[Wood] ' .. definition.id .. ': ' .. tostring(err) .. '\n')
                    elseif ok then definition.tick_error = nil end
                end
            end
            if valid(entry) then
                entry:SetVisibility(not ui.visible and pc.bShowMouseCursor and 0 or 2)
                if ticks % 30 == 0 then
                    local size = StaticFindObject('/Script/UMG.Default__WidgetLayoutLibrary'):GetViewportSize(pc)
                    entry:SetPositionInViewport({X=26, Y=size.Y-74}, true)
                    if ui.visible then ui:resize() end
                end
            end
            ui:tick()
        end)
        ticks = ticks + 1
        pending_tick = false
    end)
    return false
end)
print('[Wood] Mod loader 2.3.2 loaded. F10 opens the mod menu.\n')
