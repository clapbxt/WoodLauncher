from pathlib import Path
import tempfile
import unittest

from lupa.lua54 import LuaRuntime


BOOT = r'''
objects={}; buttons={}; settings={}; refreshes=0
function FText(value) return {ToString=function() return value end} end
function object(class)
    local value={class=class,Font={Size=14},children={}}
    function value:IsValid() return true end
    function value:SetText(text) self.label=text:ToString() end
    function value:SetFont(font) self.Font=font end
    function value:SetContent(child) self.content=child end
    function value:SetBrushColor(color) self.brush=color end
    function value:SetPadding(padding) self.padding=padding end
    function value:SetColorAndOpacity(color) self.color=color end
    function value:SetAutoWrapText(enabled) self.wrap=enabled end
    function value:AddToViewport(layer) self.layer=layer end
    function value:SetVisibility(visibility) self.visibility=visibility end
    function value:SetDesiredSizeInViewport(size) self.size=size end
    function value:SetAlignmentInViewport(alignment) self.alignment=alignment end
    function value:SetPositionInViewport(position) self.position=position end
    function value:RemoveFromParent() self.removed=true end
    table.insert(objects,value)
    return value
end
player={location={X=12.345,Y=-67.891,Z=0.126}}
function player:IsValid() return true end
function player:K2_GetActorLocation() return self.location end
function FindFirstOf() return player end
function StaticFindObject(path)
    if path:find('WidgetBlueprintLibrary',1,true) then
        return {Create=function()
            local widget=object('UserWidget')
            widget.WidgetTree=object('WidgetTree')
            return widget
        end}
    end
    if path:find('WidgetLayoutLibrary',1,true) then
        return {GetViewportSize=function() return {X=1920,Y=1080} end}
    end
    return {class=path}
end
function StaticConstructObject(class) return object(class.class) end
debug.getinfo=function() return {source='@'..coordinate_source} end
player.CharacterMovement={grounded=true}
function player.CharacterMovement:IsValid() return true end
function player.CharacterMovement:IsMovingOnGround() return self.grounded end
api={
    playerController={},
    get=function(key,default) if settings[key]==nil then return default end;return settings[key] end,
    set=function(key,value) settings[key]=tostring(value) end,
    label=function(_,text) local value=object('TextBlock');value.label=text;return value end,
    section=function(_,title) return {title=title} end,
    button=function(_,label,callback)
        buttons[label]=callback
    end,
    refreshSettings=function() refreshes=refreshes+1 end,
}
function rebuild_settings()
    buttons={}
    mod.buildSettings(api,{})
end
function label_starting_with(prefix)
    for _,value in ipairs(objects) do
        if value.label and value.label:sub(1,#prefix)==prefix then return value.label end
    end
end
'''


class CoordinatesModTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        game_root = Path(self.temp.name)
        (game_root / 'Mods').mkdir()
        (game_root / '.wood').mkdir()
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.globals().coordinate_source = str(game_root / 'Mods' / 'Coordinates.lua').replace('\\', '/')
        self.lua.execute(BOOT)
        source = Path('Mods/Coordinates.lua').read_text(encoding='utf-8')
        self.lua.globals().mod = self.lua.execute(source)

    def test_live_overlay_formats_coordinates_and_moves_between_corners(self):
        self.lua.execute('mod.onWorldReady(api);mod.onTick(api)')
        self.assertEqual(self.lua.eval("mod.tickInterval"), 6)
        self.assertEqual(self.lua.eval("objects[#objects].label"),
                         'X  12.35     Y  -67.89     Z  0.13')
        self.assertEqual(self.lua.eval("objects[1].position.X"), 1900)
        telemetry = (Path(self.temp.name) / '.wood' / 'Coordinates.live').read_text().strip().split(',')
        self.assertEqual(len(telemetry), 6)
        self.assertEqual(telemetry[1], '1')
        self.assertEqual(telemetry[5], '1')
        self.lua.execute("rebuild_settings();buttons['Corner: Top right']()")
        self.assertEqual(self.lua.eval("settings.corner"), 'Bottom right')
        self.lua.execute('rebuild_settings();buttons["Precision: Detailed"]();mod.onTick(api)')
        self.assertEqual(self.lua.eval("settings.precision"), 'Exact')
        self.assertIn('12.3450000', self.lua.eval("label_starting_with('X  ')"))
        self.assertEqual(self.lua.eval("objects[1].size.X"), 510)
        self.lua.execute('rebuild_settings();buttons["Precision: Exact"]();mod.onTick(api)')
        self.assertEqual(self.lua.eval("settings.precision"), 'Simple')
        self.assertIn('X  12     Y  -68     Z  0', self.lua.eval("label_starting_with('X  ')"))

    def test_settings_only_control_coordinate_display_and_ignore_legacy_waypoints(self):
        self.lua.execute("""
            settings.waypoint_count='1'
            settings.wp1_name='Old waypoint'
            settings.wp1_x='1'
            mod.onWorldReady(api)
            rebuild_settings()
        """)
        self.assertTrue(self.lua.eval("buttons['Corner: Top right'] ~= nil"))
        self.assertTrue(self.lua.eval("buttons['Precision: Detailed'] ~= nil"))
        self.assertTrue(self.lua.eval("buttons['Set current location as waypoint'] == nil"))
        self.assertTrue(self.lua.eval("buttons['Teleport here'] == nil"))
        self.assertEqual(self.lua.eval("settings.waypoint_count"), '1')
        self.assertEqual(self.lua.eval("settings.wp1_name"), 'Old waypoint')


if __name__ == '__main__':
    unittest.main()
