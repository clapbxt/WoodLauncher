-- Wood: native Unreal UMG mod loader and in-game menu host.
-- UObject operations are confined to the game thread. No process-memory writes.
local directory = debug.getinfo(1, 'S').source:sub(2):match('^(.*)[/\\]')
local root = dofile(directory .. '/paths.lua')
local data = root .. '/.wood/'
-- Start the installed updater companion on every game boot. It checks the
-- release feed independently so starting TUNG through Steam also gets updates.
local function start_update_check()
    local helper = root .. '/WoodUninstall.exe'
    local file = io.open(helper, 'r')
    if not file then return end
    file:close()
    local game_path = root:gsub('/', '\\')
    local helper_path = helper:gsub('/', '\\')
    local ok, result = pcall(os.execute,
        'set "PYINSTALLER_RESET_ENVIRONMENT=1" & start "" /b "' .. helper_path .. '" --check-updates --game-dir "' .. game_path .. '"')
    if not ok or result == nil then print('[Wood] Could not start the update checker.\n') end
end
start_update_check()
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
local entry_visibility
local ready = false
local ticks = 0
local pending_tick = false
local pending_click
local mods = {}
local installed_files = {}
local speedrun = read_ini(data .. 'speedrun.ini').enabled == 'true'
local restart_request
local session_executed = false
local native_clean = not speedrun
local native_inventory = {}
if speedrun then
    local native_dir = root .. '/TUNG/Binaries/Win64/ue4ss/Mods'
    local handle = io.popen('dir /b "' .. native_dir:gsub('/', '\\') .. '" 2>nul')
    native_clean = handle ~= nil
    if handle then
        local runtime_found = false
        for name in handle:lines() do
            if name:lower() == 'woodruntime' then runtime_found = true
            elseif name:lower() ~= 'mods.txt' then native_clean = false end
        end
        handle:close()
        native_clean = native_clean and runtime_found
    end
    local inventory = io.open(data .. 'speedrun-native.txt', 'r')
    if inventory then
        for name in inventory:lines() do native_inventory[#native_inventory+1] = name end
        inventory:close()
    end
end
local end_credits = nil
local end_screen_seen = false
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
        if extension and (extension:lower() == 'lua' or extension:lower() == 'tungmod') then
            installed_files[#installed_files+1] = filename
        end
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
                    if disabled[mod_id] or speedrun then return {} end
                    local chunk, err = load(source, '@' .. path)
                    if not chunk then error(err) end
                    session_executed = true
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
                if disabled[mod_id] or speedrun then return {} end
                session_executed = true
                local result = dofile(path)
                if type(result) ~= 'table' then error('Mod source must return a table.') end
                return result
            end)
            local enabled = not disabled[mod_id] and not speedrun
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
local tick_groups, tick_groups_by_interval = {}, {}
for _, definition in ipairs(mods) do
    if definition.enabled and type(definition.onTick) == 'function' then
        local interval = tonumber(definition.tickInterval) or 30
        interval = math.max(1, math.floor(interval))
        local group = tick_groups_by_interval[interval]
        if not group then
            group = {interval=interval, slots={}, count=0}
            tick_groups_by_interval[interval] = group
            tick_groups[#tick_groups+1] = group
        end
        local slot = group.count % interval + 1
        group.slots[slot] = group.slots[slot] or {}
        group.slots[slot][#group.slots[slot]+1] = definition
        group.count = group.count + 1
    end
end

local function valid(object) return object and object:IsValid() end
local api_cache, settings_cache = {}, {}
local function mod_api(definition)
    if api_cache[definition] then
        api_cache[definition].playerController = pc
        return api_cache[definition]
    end
    local path = data .. definition.id .. '.settings.ini'
    settings_cache[definition] = read_ini(path)
    local api = {
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
            -- Never destroy the calling button/slider while its callback is active.
            if ui.visible and ui.selected == definition.id then ui.refresh_pending = definition.id end
        end,
        get = function(key, default)
            local value = settings_cache[definition][key]
            if value == nil then return default end
            if type(default) == 'boolean' then return value == 'true' end
            if type(default) == 'number' then return tonumber(value) or default end
            return value
        end,
        set = function(key, value)
            assert(tostring(key):match('^[%w_]+$'), 'Invalid settings key')
            assert(not tostring(value):find('[\r\n]'), 'Settings must be single-line values')
            local values = settings_cache[definition]
            if values[key] == tostring(value) then return end
            values[key] = tostring(value)
            local file = assert(io.open(path, 'w'))
            for setting, saved in pairs(values) do file:write(setting .. '=' .. saved .. '\n') end
            file:close()
        end,
        log = function(message) print('[Wood/' .. definition.id .. '] ' .. tostring(message) .. '\n') end
    }
    api_cache[definition] = api
    return api
end
ui = dofile(directory .. '/menu.lua')({
    version='1.2.0', mods=mods, mod_api=mod_api, logoPath=data .. 'wood-logo.png',
    speedrun=function() return speedrun end,
    restartPending=function() return restart_request ~= nil end,
    setSpeedrun=function(enabled)
        if restart_request or enabled == speedrun then return end
        local helper = root .. '/WoodUninstall.exe'
        local file = io.open(helper, 'rb')
        if not file then error('Restart helper missing. Run Wood Setup 1.2.0 again.') end
        file:close()
        local token = tostring(os.time()) .. tostring(ticks)
        local status = data .. 'restart-' .. token
        os.remove(status .. '.ready'); os.remove(status .. '.error')
        local command = 'set "PYINSTALLER_RESET_ENVIRONMENT=1" & start "" /b "' .. helper:gsub('/', '\\')
            .. '" --speedrun-mode ' .. (enabled and 'on' or 'off')
            .. ' --restart-token ' .. token .. ' --game-dir "' .. root:gsub('/', '\\') .. '"'
        restart_request = {status=status, due=ticks+1800, command=command}
        ui.notice = 'Restarting TUNG. Waiting for the restart helper...'
        ui.notice_pending = true
    end,
    loadIcon=function(path)
        local rendering = StaticFindObject('/Script/Engine.Default__KismetRenderingLibrary')
        return rendering:ImportFileAsTexture2D(pc, path)
    end,
})
local function toggle_menu()
    if ui.visible then ui:hide() else ui:show(pc) end
    error_message = ''
end
local function clear_end_credits()
    if end_credits and valid(end_credits.widget) then end_credits.widget:RemoveFromParent() end
    end_credits = nil
end
local function make_end_credits()
    clear_end_credits()
    local library = StaticFindObject('/Script/UMG.Default__WidgetBlueprintLibrary')
    local widget = library:Create(pc, StaticFindObject('/Script/UMG.UserWidget'), pc)
    assert(valid(widget), 'Could not create end-screen mod credits')
    local tree = widget.WidgetTree
    local border = StaticConstructObject(StaticFindObject('/Script/UMG.Border'), tree, 0,0,0,false,false,nil)
    border:SetBrushColor({R=0.008,G=0.006,B=0.016,A=0.88})
    border:SetPadding({Left=22,Top=16,Right=22,Bottom=16})
    local panel = StaticConstructObject(StaticFindObject('/Script/UMG.VerticalBox'), tree, 0,0,0,false,false,nil)
    border:SetContent(panel)
    local title = StaticConstructObject(StaticFindObject('/Script/UMG.TextBlock'), tree, 0,0,0,false,false,nil)
    title:SetText(FText(speedrun and 'WOOD  /  SPEEDRUN REPORT' or 'WOOD  /  MODS LOADED THIS RUN'))
    local title_font = title.Font; title_font.Size = 22; title:SetFont(title_font)
    title:SetColorAndOpacity({SpecifiedColor={R=0.72,G=0.95,B=0.35,A=1},ColorUseRule=0})
    panel:AddChildToVerticalBox(title):SetPadding({Left=0,Top=0,Right=0,Bottom=12})
    local status = StaticConstructObject(StaticFindObject('/Script/UMG.TextBlock'), tree, 0,0,0,false,false,nil)
    status:SetText(FText(speedrun and not session_executed and native_clean
        and 'SPEEDRUN MODE ON / All Wood and UE4SS mods disabled. No Wood mod code executed.'
        or speedrun and 'SPEEDRUN MODE ON / UNVERIFIED: unexpected UE4SS mod files. Do not submit this session.'
        or 'SPEEDRUN MODE OFF / This session is not certified for speedruns.'))
    status:SetAutoWrapText(true)
    panel:AddChildToVerticalBox(status)
    local scroll = StaticConstructObject(StaticFindObject('/Script/UMG.ScrollBox'), tree, 0,0,0,false,false,nil)
    panel:AddChildToVerticalBox(scroll):SetSize({Value=1,SizeRule=1})
    local list = StaticConstructObject(StaticFindObject('/Script/UMG.VerticalBox'), tree, 0,0,0,false,false,nil)
    scroll:AddChild(list)
    local credits = {}
    for _, definition in ipairs(mods) do
        if not speedrun and definition.enabled and not definition.error then
            credits[#credits+1] = definition
        end
    end
    for _, name in ipairs(native_inventory) do
        credits[#credits+1] = {name='UE4SS: ' .. name, version='isolated'}
    end
    if speedrun then
        for _, filename in ipairs(installed_files) do
            credits[#credits+1] = {name=filename, version='not executed'}
        end
    end
    if #credits == 0 then
        local line = StaticConstructObject(StaticFindObject('/Script/UMG.TextBlock'), tree, 0,0,0,false,false,nil)
        line:SetText(FText('No Wood mods were loaded for this attempt.'))
        panel:AddChildToVerticalBox(line)
    end
    tree.RootWidget = border
    local layout = StaticFindObject('/Script/UMG.Default__WidgetLayoutLibrary')
    local size = layout:GetViewportSize(pc)
    local scale = layout:GetViewportScale(pc)
    if type(scale) ~= 'number' or scale <= 0 then scale = 1 end
    widget:SetPositionInViewport({X=math.max(18,size.X-530*scale),Y=math.max(24,size.Y*0.12)},true)
    widget:SetDesiredSizeInViewport({X=500,Y=math.min(430,size.Y*0.76)/scale})
    widget:AddToViewport(180)
    scroll:SetScrollOffset(0)
    end_credits = {widget=widget,scroll=scroll,list=list,entries=credits,next=1,
        built=#credits==0,offset=0,finished=false,layout_wait=0}
end
local function build_end_credits_batch()
    if not end_credits or end_credits.built then return end
    for _=1,8 do
        local definition = end_credits.entries[end_credits.next]
        if not definition then
            end_credits.built = true
            return
        end
        local line = StaticConstructObject(StaticFindObject('/Script/UMG.TextBlock'), end_credits.widget.WidgetTree, 0,0,0,false,false,nil)
        line:SetText(FText('•  ' .. definition.name
            .. (speedrun and '  /  Disabled' or '  /  v' .. definition.version)))
        local font = line.Font; font.Size = 17; line:SetFont(font)
        line:SetColorAndOpacity({SpecifiedColor={R=0.94,G=0.93,B=0.98,A=1},ColorUseRule=0})
        line:SetAutoWrapText(false)
        end_credits.list:AddChildToVerticalBox(line):SetPadding({Left=0,Top=3,Right=0,Bottom=3})
        end_credits.next = end_credits.next + 1
    end
    if end_credits.next > #end_credits.entries then end_credits.built = true end
end
local function live_end_screen()
    for _, class_name in ipairs({'WB_EndSpeedrunningTime_C','WB_DEAD_C'}) do
        for _, candidate in pairs(FindAllOf(class_name) or {}) do
            if valid(candidate) and candidate:IsInViewport() then
                local name = candidate:GetFullName()
                if not name:find('Default__', 1, true) then return true end
            end
        end
    end
    return false
end
local function safe(callback)
    local ok, err = pcall(callback)
    if not ok then
        local message = tostring(err)
        if message ~= error_message then print('[Wood] ' .. message .. '\n') end
        error_message = message
        if ui then ui.notice = message end
        if ui then ui.notice_pending = true end
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
    -- Process startup and one-file extraction must never block Unreal's game thread.
    if restart_request and restart_request.command then
        local request = restart_request
        local command = request.command; request.command = nil
        local ok, result = pcall(os.execute, command)
        if not ok or result == nil or result == false then
            request.failure = 'Could not start restart helper. Mode unchanged.'
        end
    end
    if pending_tick then return false end
    pending_tick = true
    ExecuteInGameThread(function()
        safe(function()
            local discover = ticks % 30 == 0 or not valid(pc)
            local current = discover and FindFirstOf('PlayerController') or pc
            ready = valid(current)
            if not ready then return end
            if restart_request then
                if restart_request.failure then
                    local message = restart_request.failure; restart_request = nil
                    error(message)
                end
                local failure = io.open(restart_request.status .. '.error', 'r')
                if failure then
                    local message = failure:read('*a'); failure:close()
                    restart_request = nil
                    error('Restart failed: ' .. message)
                end
                local file = io.open(restart_request.status .. '.ready', 'r')
                if file then
                    file:close()
                    if not restart_request.quit then
                        restart_request.quit = true
                        StaticFindObject('/Script/Engine.Default__KismetSystemLibrary'):QuitGame(current, current, 0, false)
                    end
                elseif ticks > restart_request.due then
                    restart_request = nil
                    error('Restart helper did not respond. Mode unchanged; run Setup again.')
                end
                -- Continue normal rendering and input until the actual exit.
                if restart_request and restart_request.quit then return end
            end
            local name = discover and current:GetFullName() or world_name
            if name ~= world_name then
                pending_click = nil
                ui:invalidate()
                clear_end_credits()
                end_screen_seen = false
                if valid(entry) then entry:RemoveFromParent() end
                entry_visibility = nil
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
            if ticks % 8 == 0 then
                local result_screen = live_end_screen()
                if result_screen and not end_screen_seen then
                    end_screen_seen = true
                    make_end_credits()
                elseif not result_screen and end_screen_seen then
                    end_screen_seen = false
                    clear_end_credits()
                end
            end
            build_end_credits_batch()
            if end_credits and end_credits.built and not end_credits.finished and valid(end_credits.scroll) then
                local finish = end_credits.scroll:GetScrollOffsetOfEnd()
                if finish > 0 then
                    end_credits.layout_wait = 0
                    end_credits.offset = math.min(finish, end_credits.offset + 0.5)
                    end_credits.scroll:SetScrollOffset(end_credits.offset)
                    if end_credits.offset >= finish then end_credits.finished = true end
                else
                    end_credits.layout_wait = end_credits.layout_wait + 1
                    if end_credits.layout_wait >= 60 then end_credits.finished = true end
                end
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
            for _, group in ipairs(tick_groups) do
                local due = group.slots[ticks % group.interval + 1]
                for _, definition in ipairs(due or {}) do
                    local ok, err = pcall(definition.onTick, mod_api(definition))
                    if not ok and definition.tick_error ~= tostring(err) then
                        definition.tick_error = tostring(err)
                        print('[Wood] ' .. definition.id .. ': ' .. tostring(err) .. '\n')
                    elseif ok then definition.tick_error = nil end
                end
            end
            if valid(entry) then
                local visibility = not ui.visible and pc.bShowMouseCursor and 0 or 2
                if visibility ~= entry_visibility then
                    entry:SetVisibility(visibility)
                    entry_visibility = visibility
                end
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
print('[Wood] Mod loader 1.2.0 loaded. F10 opens the mod menu.\n')
