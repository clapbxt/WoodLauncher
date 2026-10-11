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
local pc, world_name, menu, tree, speed_label, slider, enabled_label, travel_label
local button_actions = {}
local visible = false
local entry, entry_button
local saved_cursor
local ready = false
local applied = 1
local ticks = 0
local pending_tick = false
local selftest_result = ''
local extensions = {}
local active_page, content_panel, render_page
local rail_mods, rail_done
local colors = {
    ink={R=0.022,G=0.019,B=0.032,A=0.99},
    rail={R=0.035,G=0.026,B=0.055,A=1},
    card={R=0.055,G=0.048,B=0.075,A=1},
    purple={R=0.65,G=0.48,B=0.98,A=1},
    lime={R=0.77,G=0.96,B=0.42,A=1},
    muted={R=0.61,G=0.59,B=0.69,A=1},
    white={R=0.94,G=0.93,B=0.98,A=1}
}
local function slate(color) return {SpecifiedColor=color,ColorUseRule=0} end
-- Local Lua mods register a settings section in the same native menu. Loading
-- failures are isolated so one extension cannot prevent Time Warp from loading.
for _, item in ipairs(dofile(directory .. '/extensions.lua')) do
    local ok, definition = true, {}
    if item.enabled ~= false then ok, definition = pcall(dofile, item.path) end
    if ok and type(definition) == 'table' then
        definition.id = item.id
        definition.name = definition.name or item.name
        definition.version = definition.version or item.version
        definition.description = definition.description or item.description
        definition.enabled = item.enabled ~= false
        table.insert(extensions, definition)
    else
        table.insert(extensions, {id=item.id,name=item.name,version=item.version,enabled=false,error=tostring(definition)})
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
    if valid(slider) then slider:SetValue(speed) end
end
local function text(label, size, color)
    local object = StaticConstructObject(StaticFindObject('/Script/UMG.TextBlock'), tree, 0, 0, 0, false, false, nil)
    object:SetText(FText(label))
    local font = object.Font
    font.Size = size or 18
    object:SetFont(font)
    object:SetColorAndOpacity({SpecifiedColor = color or colors.white, ColorUseRule=0})
    return object
end
local function construct(class)
    return StaticConstructObject(StaticFindObject('/Script/UMG.' .. class), tree, 0, 0, 0, false, false, nil)
end
local function row(parent, child, padding)
    local slot = parent:AddChildToVerticalBox(child)
    slot:SetPadding({Left=0,Top=padding or 6,Right=0,Bottom=padding or 6})
    return child
end
local function button(parent, label, callback, accent)
    local object = construct('Button')
    local slot = object:AddChild(text(label, 16, accent and colors.ink or colors.white))
    slot:SetPadding({Left=16,Top=10,Right=16,Bottom=10})
    object:SetBackgroundColor(accent and colors.lime or {R=0.19,G=0.12,B=0.31,A=1})
    parent:AddChild(object)
    table.insert(button_actions, {widget=object, callback=callback})
    return object
end
local function card(parent, padding)
    local border = construct('Border')
    border:SetBrushColor(colors.card)
    border:SetPadding({Left=20,Top=padding or 16,Right=20,Bottom=padding or 16})
    local contents = construct('VerticalBox')
    border:SetContent(contents); row(parent, border, 8)
    return contents
end
local function extension_api(definition)
    local path = data .. definition.id .. '.settings.ini'
    return {
        playerController = pc,
        label = function(parent, label, size) return row(parent, text(label, size)) end,
        button = function(parent, label, callback)
            local container = construct('HorizontalBox'); row(parent, container)
            return button(container, label, callback)
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
local function hide()
    if valid(menu) then menu:SetVisibility(2) end -- Hidden, retains references
    visible = false
    if valid(pc) then
        pc.bShowMouseCursor = saved_cursor == true
        pc:SetIgnoreLookInput(false)
        pc:SetIgnoreMoveInput(false)
        if saved_cursor then
            widget_library():SetInputMode_GameAndUIEx(pc, CreateInvalidObject(), 0, false, false)
        else
            widget_library():SetInputMode_GameOnly(pc, false)
        end
    end
end
local function build_time_warp(panel)
    row(panel, text('PRACTICE  /  WORLD SPEED', 12, colors.purple), 3)
    row(panel, text('TIME WARP', 28), 4)
    row(panel, text('Slow it down. Find your rhythm. Go again.', 15, colors.muted), 4)
    local speed_card = card(panel)
    local heading = construct('HorizontalBox'); row(speed_card, heading, 2)
    heading:AddChildToHorizontalBox(text('WORLD SPEED', 12, colors.muted)):SetSize({Value=1,SizeRule=1})
    speed_label = text('', 30, colors.lime); heading:AddChild(speed_label)
    slider = construct('Slider')
    slider:SetMinValue(0.05); slider:SetMaxValue(4); slider:SetStepSize(0.05); slider:SetValue(speed)
    slider:SetSliderBarColor({R=0.20,G=0.14,B=0.32,A=1})
    slider:SetSliderHandleColor(colors.purple)
    row(speed_card, slider, 14)
    local presets = construct('HorizontalBox'); row(speed_card, presets, 6)
    for _, value in ipairs({0.1,0.25,0.5,1,2,4}) do
        local target = value
        button(presets, string.format('%gx', value), function() set_speed(target) end)
    end
    local preferences = card(panel, 12)
    local toggle_row = construct('HorizontalBox'); row(preferences, toggle_row, 4)
    button(toggle_row, 'Enable / disable', function() enabled = not enabled; set_speed(speed) end)
    enabled_label = text('', 15, colors.lime)
    toggle_row:AddChildToHorizontalBox(enabled_label):SetPadding({Left=16,Top=12,Right=0,Bottom=0})
    local travel_row = construct('HorizontalBox'); row(preferences, travel_row, 6)
    button(travel_row, 'Reset on world change', function() restore_on_travel = not restore_on_travel; save() end)
    travel_label = text('', 15, colors.muted)
    travel_row:AddChildToHorizontalBox(travel_label):SetPadding({Left=16,Top=12,Right=0,Bottom=0})
    row(panel, text('F6  Slower     F7  Normal     F8  Faster', 13, colors.purple), 6)
    local footer = construct('HorizontalBox'); row(panel, footer, 6)
    button(footer, 'Reset to 1x', function() set_speed(1) end)
    row(panel, text('Saved automatically. Disabling restores normal speed.', 13, colors.muted), 4)
end
render_page = function(id)
    tree = menu.WidgetTree
    content_panel:ClearChildren()
    button_actions = {}
    if valid(rail_mods) then table.insert(button_actions, {widget=rail_mods,callback=function() render_page(nil) end}) end
    if valid(rail_done) then table.insert(button_actions, {widget=rail_done,callback=hide}) end
    slider=nil; speed_label=nil; enabled_label=nil; travel_label=nil
    active_page = id
    local panel = content_panel
    if id then
        local navigation = construct('HorizontalBox'); row(panel, navigation)
        button(navigation, '  < Back to mods  ', function() render_page(nil) end)
        if id == 'TimeWarp' then build_time_warp(panel)
        else
            for _, definition in ipairs(extensions) do
                if definition.id == id then
                    row(panel, text(definition.name or definition.id, 28))
                    row(panel, text('Version ' .. (definition.version or '1.0'), 16))
                    if definition.description then row(panel, text(definition.description, 16)) end
                    if definition.error then row(panel, text('Load error: ' .. definition.error, 14))
                    elseif not definition.enabled then row(panel, text('Disabled. Enable in the launcher and restart TUNG.', 16))
                    elseif type(definition.buildSettings) == 'function' then
                        local ok, err = pcall(definition.buildSettings, extension_api(definition), panel)
                        if not ok then row(panel, text('Settings error: ' .. tostring(err), 14)) end
                    else row(panel, text('This mod has no configurable settings.', 16)) end
                    break
                end
            end
        end
    else
        row(panel, text('YOUR MODS', 24))
        row(panel, text('Your tools, right here in the game.', 15, colors.muted))
        local function mod_item(id, name, version, description, state)
            local link = construct('Button')
            link:SetBackgroundColor(colors.card)
            local contents = construct('VerticalBox')
            local padding = link:AddChild(contents)
            padding:SetPadding({Left=22,Top=18,Right=22,Bottom=18})
            row(panel, link, 8)
            row(contents, text(name, 22), 3)
            row(contents, text('v' .. version .. '   /   ' .. state .. '   /   Settings >', 13,
                state == 'Enabled' and colors.lime or colors.muted), 5)
            if description then row(contents, text(description, 14, colors.muted), 3) end
            table.insert(button_actions, {widget=link,callback=function() render_page(id) end})
        end
        mod_item('TimeWarp','Time Warp','2.1.2','World speed, presets, hotkeys, and saved settings.', enabled and 'Enabled' or 'Disabled')
        for _, definition in ipairs(extensions) do
            mod_item(definition.id,definition.name or definition.id,definition.version or '1.0',definition.description,
                definition.error and 'Load error' or (definition.enabled and 'Enabled' or 'Disabled'))
        end
    end
end
local function build_menu()
    menu = widget_library():Create(pc, StaticFindObject('/Script/UMG.UserWidget'), pc)
    assert(valid(menu), 'Unreal did not create the mod menu')
    tree = menu.WidgetTree
    assert(valid(tree), 'The mod menu has no widget tree')
    local border = construct('Border')
    border:SetBrushColor(colors.ink)
    border:SetPadding({Left=0,Top=0,Right=0,Bottom=0})
    local shell = construct('HorizontalBox'); border:SetContent(shell); tree.RootWidget = border
    local rail_border = construct('Border')
    rail_border:SetBrushColor(colors.rail)
    rail_border:SetPadding({Left=22,Top=28,Right=22,Bottom=24})
    local rail = construct('VerticalBox'); rail_border:SetContent(rail)
    shell:AddChildToHorizontalBox(rail_border):SetSize({Value=0.25,SizeRule=1})
    row(rail, text('WOOD', 28, colors.lime), 6)
    row(rail, text('TUNG MOD TOOLKIT', 11, colors.muted), 3)
    row(rail, text('LIBRARY', 11, colors.purple), 24)
    rail_mods = button(rail, 'Your mods', function() render_page(nil) end)
    row(rail, text(string.format('%d installed', #extensions+1), 13, colors.muted), 12)
    local space = construct('VerticalBox')
    rail:AddChildToVerticalBox(space):SetSize({Value=1,SizeRule=1})
    row(rail, text('F10  Open / close', 12, colors.muted), 4)
    row(rail, text('Esc  Back', 12, colors.muted), 4)
    local close_row = construct('HorizontalBox'); row(rail, close_row, 12)
    rail_done = button(close_row, 'Back to game', hide, true)
    local body_border = construct('Border')
    body_border:SetBrushColor(colors.ink)
    body_border:SetPadding({Left=28,Top=24,Right=28,Bottom=24})
    shell:AddChildToHorizontalBox(body_border):SetSize({Value=0.75,SizeRule=1})
    local scroll = construct('ScrollBox'); body_border:SetContent(scroll)
    content_panel = construct('VerticalBox'); scroll:AddChild(content_panel)
    render_page(nil)
    menu:AddToViewport(10000)
    menu:SetAlignmentInViewport({X=0.5,Y=0.5})
    menu:SetPositionInViewport({X=640,Y=360}, true)
    menu:SetDesiredSizeInViewport({X=900,Y=640})
    menu:SetVisibility(2)
    print('[Wood] Native UMG mod menu created\n')
end
local function show()
    if not valid(pc) then return end
    if not valid(menu) then button_actions = {}; build_menu() end
    render_page(nil)
    saved_cursor = pc.bShowMouseCursor
    pc:SetIgnoreLookInput(true)
    pc:SetIgnoreMoveInput(true)
    pc.bShowMouseCursor = true
    menu:SetVisibility(0)
    -- Resolve viewport dimensions with reflected engine API, not desktop size.
    local size = StaticFindObject('/Script/UMG.Default__WidgetLayoutLibrary'):GetViewportSize(pc)
    menu:SetPositionInViewport({X=size.X/2,Y=size.Y/2}, true)
    local ok, scale = pcall(function() return StaticFindObject('/Script/UMG.Default__WidgetLayoutLibrary'):GetViewportScale(pc) end)
    if not ok or type(scale) ~= 'number' or scale <= 0 then scale = 1 end
    menu:SetDesiredSizeInViewport({X=math.min(900,size.X/scale-48),Y=math.min(640,size.Y/scale-48)})
    widget_library():SetInputMode_UIOnlyEx(pc, menu, 0, false)
    visible = true
end
local function toggle_menu() if visible then hide() else show() end end
local function build_entry()
    entry = widget_library():Create(pc, StaticFindObject('/Script/UMG.UserWidget'), pc)
    tree = entry.WidgetTree
    entry_button = construct('Button')
    entry_button:AddChild(text('  Wood Mods  /  F10  ', 16, colors.lime))
    entry_button:SetBackgroundColor(colors.rail)
    tree.RootWidget = entry_button
    entry:AddToViewport(9000)
    entry:SetDesiredSizeInViewport({X=180,Y=48})
    local size = StaticFindObject('/Script/UMG.Default__WidgetLayoutLibrary'):GetViewportSize(pc)
    entry:SetPositionInViewport({X=26,Y=size.Y-74}, true)
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
RegisterKeyBind(Key.ESCAPE, function()
    if visible then
        queue(function() if active_page then render_page(nil) else hide() end end)
    end
end)
-- Win32 key events retain very short clicks between engine ticks. Hit testing
-- still belongs to the actual UMG button, rather than desktop coordinates.
RegisterKeyBind(Key.LEFT_MOUSE_BUTTON, function()
    queue(function()
        if visible then
            for _, action in ipairs(button_actions) do
                if action.widget:IsHovered() then action.callback(); break end
            end
        elseif valid(entry_button) and entry_button:IsHovered() then show() end
    end)
end)
for _, key in ipairs({Key.RETURN, Key.SPACE}) do
    RegisterKeyBind(key, function()
        if visible then queue(function()
            for _, action in ipairs(button_actions) do
                if action.widget:HasKeyboardFocus() then action.callback(); break end
            end
        end) end
    end)
end
RegisterKeyBind(Key.F6, function() queue(function() if enabled then set_speed(speed / 2) end end) end)
RegisterKeyBind(Key.F7, function() queue(function() set_speed(1) end) end)
RegisterKeyBind(Key.F8, function() queue(function() if enabled then set_speed(speed * 2) end end) end)

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
        tostring(ready), speed, applied, tostring(enabled), tostring(restore_on_travel), tostring(visible), quoted(last_command),
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
                if visible then hide() end
                if valid(menu) then menu:RemoveFromParent() end
                if valid(entry) then entry:RemoveFromParent() end
                local traveling = world_name ~= nil
                pc = current; world_name = name
                menu = nil; slider = nil; button_actions = {}
                if traveling and restore_on_travel then speed = 1; save() end
                gameplay():SetGlobalTimeDilation(pc, enabled and speed or 1)
                build_entry()
                for _, definition in ipairs(extensions) do
                    if definition.enabled and type(definition.onWorldReady) == 'function' then
                        local ok, err = pcall(definition.onWorldReady, extension_api(definition))
                        if not ok then print('[Wood] ' .. definition.id .. ': ' .. tostring(err) .. '\n') end
                    end
                end
                print('[Wood] Attached to ' .. name .. '\n')
            end
            if ticks % 6 == 0 then command() end
            applied = gameplay():GetGlobalTimeDilation(pc)
            if valid(entry) then
                entry:SetVisibility(not visible and pc.bShowMouseCursor and 0 or 2)
                if ticks % 30 == 0 then
                    local size = StaticFindObject('/Script/UMG.Default__WidgetLayoutLibrary'):GetViewportSize(pc)
                    entry:SetPositionInViewport({X=26,Y=size.Y-74}, true)
                    if visible and valid(menu) then menu:SetPositionInViewport({X=size.X/2,Y=size.Y/2}, true)
    local ok, scale = pcall(function() return StaticFindObject('/Script/UMG.Default__WidgetLayoutLibrary'):GetViewportScale(pc) end)
    if not ok or type(scale) ~= 'number' or scale <= 0 then scale = 1 end
    menu:SetDesiredSizeInViewport({X=math.min(900,size.X/scale-48),Y=math.min(640,size.Y/scale-48)}) end
                end
            end
            if visible and valid(menu) and active_page == 'TimeWarp' and valid(slider) then
                local value = clamp(slider:GetValue())
                if value ~= speed then set_speed(value) end
                speed_label:SetText(FText(string.format('%.2fx', applied)))
                enabled_label:SetText(FText(enabled and 'Enabled' or 'Disabled  /  normal speed'))
                travel_label:SetText(FText(restore_on_travel and 'On  /  restore 1x' or 'Off  /  keep speed'))
            end
        end)
        ticks = ticks + 1
        if ticks % 30 == 0 then safe(status) end
        pending_tick = false
    end)
    return false
end)
print('[Wood] Time Warp 2.1.2 loaded. F10 mods; F6 slower; F7 reset; F8 faster.\n')
