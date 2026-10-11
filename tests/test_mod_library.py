"""Exercise the actual native Lua UI against a reflected-widget/engine double."""
from pathlib import Path
import tempfile
import unittest
import struct
import zlib
from lupa.lua54 import LuaRuntime
from WoodModPackager import create_package


def png_fixture(width=32, height=32):
    def chunk(name, data):
        return (struct.pack('>I', len(data)) + name + data
                + struct.pack('>I', zlib.crc32(name + data) & 0xFFFFFFFF))

    header = struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)
    pixels = b''.join(b'\x00' + b'\x00' * (width * 4) for _ in range(height))
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', header)
            + chunk(b'IDAT', zlib.compress(pixels)) + chunk(b'IEND', b''))

BOOT = r'''
created={}; keys={}; builds=0; callbacks=0; fast_ticks=0; icon_imports=0; unsafe_style_calls=0; world='TestWorld'; viewport={X=1280,Y=720}; dpi=1
function FText(t) return {ToString=function() return t end} end
function brush() return {OutlineSettings={}} end
function object(class)
 local o={class=class,Font={Size=18},children={},value=1,visibility=0,bShowMouseCursor=true,
  Background=brush(),WidgetStyle={Normal=brush(),Hovered=brush(),Pressed=brush(),Disabled=brush(),Font={},TextStyle={Font={}},ForegroundColor={},BackgroundColor={},BackgroundImageNormal=brush(),BackgroundImageHovered=brush(),BackgroundImageFocused=brush()}}
 function o:IsValid() return true end
 function o:AddChild(child)
  table.insert(self.children,child); child.parent=self; child.Slot=object('Slot'); return child.Slot
 end
 o.AddChildToVerticalBox=o.AddChild; o.AddChildToHorizontalBox=o.AddChild; o.AddChildToScrollBox=o.AddChild
 function o:SetContent(child) self.children={child};child.parent=self end
 function o:GetParent() return self.parent end
 function o:ClearChildren() self.children={} end
 function o:SetText(t) self.label=t:ToString() end
 function o:GetText() return FText(self.label or '') end
 function o:SetFont(f) self.Font=f end
 function o:SetBrushFromTexture(texture) self.texture=texture end
 function o:ImportFileAsTexture2D(_,path)
  icon_imports=icon_imports+1
  return {path=path}
 end
 -- Copying a live owning style through the pinned UE4SS bridge can terminate TUNG.
 function o:SetStyle(s) unsafe_style_calls=unsafe_style_calls+1;error('Unsafe owning FButtonStyle resubmission') end
 function o:SetValue(v) self.value=v end
 function o:GetValue() return self.value end
 function o:SetVisibility(v) self.visibility=v end
 function o:IsHovered() return self.hover==true end
 function o:HasKeyboardFocus() return self.focus==true end
 function o:HasFocusedDescendants() return self.descendant_focus==true end
 function o:GetFullName() return world..'.PlayerController' end
 function o:GetViewportSize() return viewport end
 function o:GetViewportScale() return dpi end
 function o:GetGlobalTimeDilation() return applied_speed or 1 end
 function o:SetGlobalTimeDilation(pc,speed) applied_speed=speed end
 function o:SetIgnoreLookInput(v) self.ignore_look=v end
 function o:SetIgnoreMoveInput(v) self.ignore_move=v end
 function o:SetDesiredSizeInViewport(v) self.desired=v end
 function o:SetBackgroundColor(v) self.background=v end
 function o:SetIsEnabled(v) self.enabled=v end
 function o:RemoveFromParent() self.removed=true end
 function o:Create() local m=object('UserWidget');m.WidgetTree=object('WidgetTree');return m end
 for _,name in ipairs({'SetPadding','SetSize','SetHorizontalAlignment','SetBrushColor','SetColorAndOpacity','SetForegroundColor','SetHintText',
  'SetAutoWrapText','SetWidthOverride','SetHeightOverride','SetStretch','SetJustification','SetToolTipText','SetMinValue','SetMaxValue','SetStepSize',
  'SetSliderBarColor','SetSliderHandleColor','AddToViewport','SetAlignmentInViewport','SetPositionInViewport',
  'SetInputMode_GameAndUIEx','SetInputMode_GameOnly','SetInputMode_UIOnlyEx'}) do o[name]=function() end end
 table.insert(created,o);return o
end
pc=object('PlayerController')
function StaticFindObject(path) return object(path) end
function StaticConstructObject(class) return object(class.class) end
function FindFirstOf() return pc end
function CreateInvalidObject() return nil end
function ExecuteInGameThread(fn) fn() end
function RegisterKeyBind(key,fn) keys[key]=fn end
Key={F10='F10',ESCAPE='ESCAPE',LEFT_MOUSE_BUTTON='CLICK',RETURN='RETURN',SPACE='SPACE',F6='F6',F7='F7',F8='F8'}
function LoopAsync(ms,fn) tick=fn end
real_dofile=dofile
real_popen=io.popen
function dofile(path)
 if path:find('paths.lua',1,true) then return test_root end
 if path:find('menu.lua',1,true) then
  local factory=real_dofile(test_menu)
  return function(options) test_ui=factory(options);return test_ui end
 end
 return real_dofile(path)
end
function io.popen(cmd)
 if cmd:find('dir /b',1,true) and cmd:find('Mods',1,true) then
  return {lines=function() return coroutine.wrap(function() coroutine.yield('Example.lua') coroutine.yield('TimeWarp.lua') coroutine.yield('WoodUtilities.lua') coroutine.yield('Disabled.lua') coroutine.yield('Broken.lua') coroutine.yield('Packaged.tungmod') end) end, close=function() end}
 end
 return real_popen(cmd)
end
function has_label(o,label)
 if o.label==label then return true end
 for _,child in ipairs(o.children) do if has_label(child,label) then return true end end
 return false
end
function focus(o)
 for _,widget in ipairs(created) do widget.focus=false;widget.descendant_focus=false end
 if o then o.descendant_focus=true end
end
function click_widget(widget)
 for _,o in ipairs(created) do o.hover=false end
 widget.hover=true; keys.CLICK();tick();tick();tick()
end
function find_button(label)
 for _,group in ipairs({'shell','list','details'}) do
  for _,action in ipairs(test_ui.actions[group]) do if has_label(action.widget,label) then return action.widget end end
 end
end
function click(label)
 local button=find_button(label);if not button then return false end
 click_widget(button);return true
end
'''


class NativeMenuTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='wood-ui-')
        self.addCleanup(self.temp.cleanup)
        self.data = Path(self.temp.name) / '.wood'
        self.data.mkdir()
        self.mods_dir = Path(self.temp.name) / 'Mods'
        self.mods_dir.mkdir()
        # Create test mod files
        (self.mods_dir / 'Example.lua').write_text('''return {
    name = 'Example',
    version = '1.0',
    author = 'Test',
    description = 'A practice helper',
    tickInterval = 6,
    onTick = function() fast_ticks = fast_ticks + 1 end,
    buildSettings = function(api, panel)
        builds = builds + 1
        api.button(panel, 'Example settings', function() callbacks = callbacks + 1 end)
        api.input(panel, 'Example input', 'test')
    end,
}''', encoding='utf-8')
        (self.mods_dir / 'TimeWarp.lua').write_text('''local function clamp(value)
    local n = tonumber(value)
    if not n or n ~= n or n == math.huge or n == -math.huge then return 1 end
    return math.floor(math.max(0.05, math.min(4, n)) * 100 + 0.5) / 100
end
local mod = {name = 'Time Warp', version = '2.2.3', author = 'Wood', description = 'World speed control.'}
local speed, enabled, restore_on_travel = 1, true, true
local applied = 1
local api_ref
local function gameplay() return StaticFindObject('/Script/Engine.Default__GameplayStatics') end
local function valid(o) return o and o:IsValid() end
local function apply(api)
    local pc = api.playerController
    if not valid(pc) then return end
    gameplay():SetGlobalTimeDilation(pc, enabled and speed or 1)
    applied = gameplay():GetGlobalTimeDilation(pc)
end
local function set_speed(api, value)
    speed = clamp(value)
    apply(api)
    api.set('speed', speed)
    api.set('enabled', enabled)
    api.set('restore_on_travel', restore_on_travel)
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
    api.label(speed_card, enabled and string.format('Applied to the world: %.2fx', applied) or 'Disabled  /  world running at normal speed', 13)
    api.slider(speed_card, 'Speed', 0.05, 4, 0.05, speed, function(v) set_speed(api, v) end, function(v) return string.format('%.2fx', v) end)
    local presets_card = api.section(panel, 'PRESETS', nil)
    for _, target in ipairs({0.1, 0.25, 0.5, 1, 2, 4}) do
        api.button(presets_card, string.format('%gx', target), function() set_speed(api, target) end)
    end
    local pref_card = api.section(panel, 'PREFERENCES', nil)
    api.toggle(pref_card, 'Time Warp enabled', enabled, function(v) enabled = v; apply(api); api.set('enabled', v); api.set('speed', speed); api.set('restore_on_travel', restore_on_travel); api.refreshSettings() end)
    api.toggle(pref_card, 'Reset speed on world change', restore_on_travel, function(v) restore_on_travel = v; api.set('restore_on_travel', v) end)
    api.label(panel, 'F6  Slower     F7  Normal     F8  Faster', 13)
end
return mod''', encoding='utf-8')
        (self.mods_dir / 'WoodUtilities.lua').write_text('''return {name = 'Wood Utilities', version = '1.0', author = 'Wood', description = 'Utilities.'}''', encoding='utf-8')
        (self.mods_dir / 'Disabled.lua').write_text('''return {name = 'Disabled', version = '1.0', author = 'Test', description = '', enabled = false}''', encoding='utf-8')
        (self.mods_dir / 'Broken.lua').write_text('error("Example load failure")', encoding='utf-8')
        package_source = self.root = Path(self.temp.name) / 'Packaged.lua'
        package_source.write_text('return {description="ignored by package metadata"}', encoding='utf-8')
        icon = Path(self.temp.name) / 'icon.png'
        icon.write_bytes(png_fixture())
        create_package(package_source, self.mods_dir / 'Packaged.tungmod', {
            'id': 'packaged-helper', 'name': 'Packaged Helper', 'version': '1.0.0',
            'author': 'Test', 'description': 'Loaded from a TUNG package.',
        }, icon)
        # Create mods_disabled.txt for Disabled mod
        (self.data / 'mods_disabled.txt').write_text('Disabled\n', encoding='utf-8')

        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.globals().test_root = self.temp.name.replace('\\', '/')
        self.lua.globals().test_menu = str(Path('NativeMods/WoodRuntime/Scripts/menu.lua').resolve()).replace('\\', '/')
        self.lua.execute(BOOT)
        source = Path('NativeMods/WoodRuntime/Scripts/main.lua').read_text(encoding='utf-8')
        self.lua.execute("assert(load(..., '@NativeMods/WoodRuntime/Scripts/main.lua'))()", source)
        self.lua.execute('tick(); keys.F10()')

    def tearDown(self):
        self.lua.execute("assert(unsafe_style_calls==0, 'Do not resubmit a live owning FButtonStyle through UE4SS')")

    def run_lua(self, code):
        self.lua.execute(code)

    def test_library_stays_visible_and_detached_callbacks_are_removed(self):
        self.run_lua("assert(has_label(test_ui.details,'YOUR MODS'));assert(click('Example'));assert(builds==1)")
        self.run_lua("assert(click('Example settings'));old_button=find_button('Example settings');assert(callbacks==1)")
        self.run_lua("assert(click('Time Warp'));assert(test_ui.selected=='TimeWarp');assert(test_ui.list_buttons.Example)")
        self.run_lua('click_widget(old_button);assert(callbacks==1);assert(builds==1)')
        self.run_lua("assert(click('Disabled'));assert(has_label(test_ui.details,'This mod is disabled'))")
        self.run_lua("assert(click('Broken'));assert(has_label(test_ui.details,'This mod could not load'))")

    def test_mod_specific_tick_interval_and_native_text_input_api(self):
        self.run_lua("""
            baseline=fast_ticks
            for i=1,5 do tick() end
            assert(fast_ticks==baseline)
            tick()
            assert(fast_ticks==baseline+1)
            for i=1,6 do tick() end
            assert(fast_ticks==baseline+2)
            assert(click('Example'))
            assert(click('Example settings'))
        """)

    def test_tungmod_metadata_and_png_icon_are_loaded_into_the_native_menu(self):
        self.run_lua("""
            local packaged=test_ui:find('packaged-helper')
            assert(packaged and packaged.name=='Packaged Helper')
            assert(packaged.version=='1.0.0' and packaged.author=='Test')
            assert(packaged.description=='Loaded from a TUNG package.')
            assert(packaged.iconPath:match('mod_packaged%-helper%.png$'))
            assert(icon_imports>0)
            local image
            for index=#created,1,-1 do
                local widget=created[index]
                if widget.class:match('Image$') and widget.texture then image=widget;break end
            end
            assert(image, 'No Image widget was constructed')
            assert(image.texture, 'PNG texture was not assigned')
            assert(image.texture.path==packaged.iconPath, 'Assigned texture path does not match metadata')
        """)

    def test_search_filters_and_empty_state(self):
        self.run_lua("test_ui.search:SetText(FText('practice helper'));tick();assert(#test_ui.shown==1 and test_ui.shown[1]=='Example')")
        self.run_lua("test_ui.search:SetText(FText(''));tick();assert(click('Settings'));assert(#test_ui.shown>=2)")
        self.run_lua("test_ui.search:SetText(FText('[?]'));tick();assert(#test_ui.shown==0);assert(has_label(test_ui.list,'No mods installed'))")
        self.run_lua("assert(click('Reset filters'));assert(#test_ui.shown>=4);assert(test_ui.query=='' and test_ui.filter=='All')")

    def test_filter_focus_transitions_preserve_the_page_and_settings(self):
        self.run_lua("assert(click('Time Warp'));assert(click('2x'));old_row=test_ui.list_buttons.Example")
        saved=(self.data / 'TimeWarp.settings.ini').read_bytes()
        self.run_lua("""
            for cycle=1,20 do
                for _,filter in ipairs({'Active','Settings','All'}) do
                    local button=test_ui.filter_buttons[filter]
                    focus(nil);button.focus=true;tick()
                    if cycle%2==0 then keys.RETURN();tick() else click_widget(button) end
                    local expected=filter=='All' and 6 or filter=='Active' and 4 or 2
                    assert(test_ui.filter==filter and #test_ui.shown==expected)
                    assert(test_ui.selected=='TimeWarp' and applied_speed==2)
                    assert(button.WidgetStyle.Normal.OutlineSettings.Width==2)
                    assert(unsafe_style_calls==0)
                end
            end
            focus(nil);click_widget(old_row)
            assert(test_ui.selected=='TimeWarp' and applied_speed==2)
        """)
        self.assertEqual(saved, (self.data / 'TimeWarp.settings.ini').read_bytes())

    def test_timewarp_presets_apply_and_persist(self):
        self.run_lua("assert(click('Time Warp'))")
        self.run_lua("assert(click('2x'));assert(applied_speed==2)")
        self.assertIn('speed=2.0', (self.data / 'TimeWarp.settings.ini').read_text())
        self.run_lua("assert(click('0.25x'));assert(applied_speed==0.25)")
        self.assertIn('speed=0.25', (self.data / 'TimeWarp.settings.ini').read_text())

    def test_toggles_presets_and_typing_do_not_change_unrelated_settings(self):
        self.run_lua("assert(click('Time Warp'));assert(click('2x'));assert(applied_speed==2)")
        self.run_lua("assert(click('On'));assert(applied_speed==1)")
        self.assertIn('enabled=false', (self.data / 'TimeWarp.settings.ini').read_text())
        self.run_lua("assert(click('0.25x'));assert(applied_speed==1);assert(has_label(test_ui.details,'0.25x'))")
        self.run_lua("assert(click('Off'));assert(applied_speed==0.25)")
        self.run_lua('focus(test_ui.search);keys.SPACE();assert(applied_speed==0.25)')
        self.run_lua('focus(nil);keys.SPACE();assert(applied_speed==0.25)')

    def test_keyboard_navigation_works(self):
        self.run_lua("assert(click('Time Warp'))")
        self.run_lua("keys.ESCAPE();assert(test_ui.selected==nil and test_ui.visible)")
        self.run_lua('keys.ESCAPE();assert(not test_ui.visible);assert(not pc.ignore_look and not pc.ignore_move and pc.bShowMouseCursor)')
        self.run_lua("keys.F10();assert(click('Example'));keys.F10();keys.F10();assert(test_ui.selected=='Example' and builds==1)")
        self.run_lua("old_widget=test_ui.widget;world='NextWorld';tick();assert(old_widget.removed and not test_ui.visible)")
        self.run_lua("keys.F10();assert(test_ui.widget~=old_widget and test_ui.selected=='Example')")

    def test_fast_click_waits_for_slate_and_does_not_leak_into_another_page(self):
        self.run_lua("old=find_button('Time Warp');target=find_button('Example');old.hover=true;keys.CLICK();assert(test_ui.selected==nil)")
        self.run_lua("tick();old.hover=false;target.hover=true;tick();tick();assert(test_ui.selected=='Example' and builds==1)")
        self.run_lua("target.hover=false;test_ui.list_buttons.TimeWarp.hover=true;keys.CLICK();keys.ESCAPE();tick();tick();tick();assert(test_ui.selected==nil)")

    def test_viewport_respects_dpi_and_resizing(self):
        self.run_lua('viewport={X=800,Y=600};dpi=1;test_ui:resize();assert(test_ui.widget.desired.X==760 and test_ui.widget.desired.Y==560)')
        self.run_lua('viewport={X=1600,Y=900};dpi=1.25;test_ui:resize();assert(test_ui.widget.desired.X==896 and test_ui.widget.desired.Y==624)')

    def test_failed_build_releases_partial_widgets_and_can_retry(self):
        self.run_lua('test_ui:invalidate(); original_construct=StaticConstructObject')
        self.run_lua("function StaticConstructObject(class,...) if class.class:find('EditableTextBox',1,true) then error('Native field unavailable') end; return original_construct(class,...) end")
        self.run_lua('keys.F10();assert(not test_ui.visible and test_ui.widget==nil and test_ui.search==nil)')
        self.run_lua('assert(not pc.ignore_look and not pc.ignore_move);tick()')
        self.run_lua('StaticConstructObject=original_construct;keys.F10();assert(test_ui.visible and test_ui.search)')


if __name__ == '__main__':
    unittest.main()