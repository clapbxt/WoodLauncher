local mod = {
    name = 'Coordinates',
    version = '1.2.0',
    author = 'Wood',
    description = 'A compact, configurable live coordinate display.',
    tickInterval = 6,
}

local corners = {
    ['Top left'] = {anchor={X=0,Y=0}, x=20, y=20},
    ['Top right'] = {anchor={X=1,Y=0}, x=-20, y=20},
    ['Bottom left'] = {anchor={X=0,Y=1}, x=20, y=-20},
    ['Bottom right'] = {anchor={X=1,Y=1}, x=-20, y=-20},
}
local precisions = {
    {name='Simple', digits=0, width=260},
    {name='Detailed', digits=2, width=360},
    {name='Exact', digits=7, width=510},
}
local corner_names = {'Top left', 'Top right', 'Bottom right', 'Bottom left'}
local precision_names = {'Simple', 'Detailed', 'Exact'}
local overlay, coordinate_text, current_position
local telemetry_sequence = 0
local game_root
local telemetry_path

local function valid(object)
    if not object then return false end
    local ok, result = pcall(function() return object:IsValid() end)
    return ok and result
end

local function finite(value)
    return type(value) == 'number' and value == value and value ~= math.huge and value ~= -math.huge
end

local function position_of(player)
    if not valid(player) then return nil end
    local ok, location = pcall(function() return player:K2_GetActorLocation() end)
    if not ok or not location then return nil end
    local read_ok, x, y, z = pcall(function()
        return tonumber(location.X), tonumber(location.Y), tonumber(location.Z)
    end)
    if not read_ok or not finite(x) or not finite(y) or not finite(z) then return nil end
    return {X=x, Y=y, Z=z}
end

local function player_actor()
    local player = FindFirstOf('BP_Player_C')
    if valid(player) then return player end
    return nil
end

local function display_options(api)
    local corner = api.get('corner', 'Top right')
    if not corners[corner] then corner = 'Top right' end
    local precision = api.get('precision', 'Detailed')
    for _, option in ipairs(precisions) do
        if option.name == precision then return corner, option end
    end
    return corner, precisions[2]
end

local function formatted(value, digits)
    return string.format('%.' .. digits .. 'f', value)
end

local function update_overlay_position(api, width)
    if not valid(overlay) then return end
    local corner, precision = display_options(api)
    local layout = StaticFindObject('/Script/UMG.Default__WidgetLayoutLibrary')
    local viewport = layout:GetViewportSize(api.playerController)
    local placement = corners[corner]
    local x = placement.x
    local y = placement.y
    if x < 0 then x = viewport.X + x end
    if y < 0 then y = viewport.Y + y end
    overlay:SetDesiredSizeInViewport({X=width or precision.width,Y=44})
    overlay:SetAlignmentInViewport(placement.anchor)
    overlay:SetPositionInViewport({X=x,Y=y}, true)
end

local function create_overlay(api)
    local library = StaticFindObject('/Script/UMG.Default__WidgetBlueprintLibrary')
    overlay = library:Create(api.playerController, StaticFindObject('/Script/UMG.UserWidget'), api.playerController)
    local tree = overlay.WidgetTree
    local border = StaticConstructObject(StaticFindObject('/Script/UMG.Border'), tree, 0,0,0,false,false,nil)
    local text = StaticConstructObject(StaticFindObject('/Script/UMG.TextBlock'), tree, 0,0,0,false,false,nil)
    border:SetBrushColor({R=0.012,G=0.018,B=0.027,A=0.86})
    border:SetPadding({Left=14,Top=9,Right=14,Bottom=9})
    text:SetText(FText('X  --     Y  --     Z  --'))
    local font = text.Font
    font.Size = 16
    text:SetFont(font)
    text:SetColorAndOpacity({SpecifiedColor={R=0.45,G=0.93,B=0.82,A=1},ColorUseRule=0})
    text:SetAutoWrapText(false)
    border:SetContent(text)
    tree.RootWidget = border
    overlay:AddToViewport(8500)
    overlay:SetVisibility(0)
    coordinate_text = text
    update_overlay_position(api)
end

local function update_telemetry(player, position)
    if not telemetry_path or not position then return end
    local grounded = 0
    local ok, movement = pcall(function() return player.CharacterMovement end)
    if ok and valid(movement) then
        local ground_ok, value = pcall(function() return movement:IsMovingOnGround() end)
        if ground_ok and value == true then grounded = 1 end
    end
    telemetry_sequence = telemetry_sequence + 1
    local file, err = io.open(telemetry_path, 'w')
    if not file then
        if not mod.telemetry_error then
            mod.telemetry_error = tostring(err)
            print('[Wood/Coordinates] Could not write LiveSplit telemetry: ' .. tostring(err) .. '\n')
        end
        return
    end
    file:write(string.format('%.0f,%d,%.7f,%.7f,%.7f,%d\n',
        os.time(), telemetry_sequence, position.X, position.Y, position.Z, grounded))
    file:close()
    mod.telemetry_error = nil
end

function mod.onWorldReady(api)
    if valid(overlay) then overlay:RemoveFromParent() end
    overlay, coordinate_text = nil, nil
    create_overlay(api)
end

function mod.onTick(api)
    local player = player_actor()
    current_position = position_of(player)
    if valid(coordinate_text) then
        local _, precision = display_options(api)
        if current_position then
            coordinate_text:SetText(FText(string.format(
                'X  %s     Y  %s     Z  %s',
                formatted(current_position.X, precision.digits),
                formatted(current_position.Y, precision.digits),
                formatted(current_position.Z, precision.digits))))
        else
            coordinate_text:SetText(FText('X  --     Y  --     Z  --'))
        end
        update_overlay_position(api, precision.width)
    end
    if player and current_position then update_telemetry(player, current_position) end
end

function mod.buildSettings(api, panel)
    local corner, precision = display_options(api)
    local appearance = api.section(panel, 'COORDINATE DISPLAY', 'A compact live position readout. Changes save automatically.')
    local corner_index = 1
    for index, name in ipairs(corner_names) do if corner == name then corner_index=index end end
    api.button(appearance, 'Corner: ' .. corner, function()
        corner_index = corner_index % #corner_names + 1
        api.set('corner', corner_names[corner_index])
        api.refreshSettings()
    end)
    local precision_index = 1
    for index, name in ipairs(precision_names) do if precision.name == name then precision_index=index end end
    api.button(appearance, 'Precision: ' .. precision.name, function()
        precision_index = precision_index % #precision_names + 1
        api.set('precision', precision_names[precision_index])
        api.refreshSettings()
    end)
    api.label(appearance, 'Simple: 0 decimals   /   Detailed: 2   /   Exact: 7 maximum', 12)

end

local source_path = debug.getinfo(1, 'S').source:sub(2)
game_root = source_path:match('^(.*)[/\\]Mods[/\\][^/\\]+$')
if game_root then telemetry_path = game_root .. '/.wood/Coordinates.live' end

return mod
