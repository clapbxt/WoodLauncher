"""Exercise the actual native Lua UI against a reflected-widget/engine double."""
from pathlib import Path
import os
import tempfile
import unittest
import struct
import zlib
from lupa.lua54 import LuaRuntime


def create_package(lua_path, output_path, metadata, icon_path=None):
    source = Path(lua_path).read_bytes()
    metadata_bytes = ''.join(f"{key}={metadata[key]}\n" for key in
                             ('id', 'name', 'version', 'author', 'description')).encode('utf-8')
    icon = Path(icon_path).read_bytes() if icon_path else b''
    output = Path(output_path).with_suffix('.tungmod')
    output.write_bytes(b'TUNG-MOD/1\n' + f'{len(metadata_bytes)}\n{len(source)}\n{len(icon)}\n'.encode()
                       + metadata_bytes + source + icon)
    return output


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
 function o:IsInViewport() return true end
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
 function o:SetWidthOverride(v) self.width=v end
 function o:SetHeightOverride(v) self.height=v end
 function o:SetStretch(v) self.stretch=v end
 function o:ImportFileAsTexture2D(_,path)
  icon_imports=icon_imports+1
  return {path=path, IsValid=function() return true end}
 end
 -- Copying a live owning style through the pinned UE4SS bridge can terminate TUNG.
 function o:SetStyle(s) unsafe_style_calls=unsafe_style_calls+1;error('Unsafe owning FButtonStyle resubmission') end
 function o:SetValue(v) self.value=v end
 function o:GetValue() return self.value end
 function o:SetVisibility(v) self.visibility=v end
 function o:IsHovered() return self.hover==true end
 function o:HasKeyboardFocus() return self.focus==true end
 function o:HasFocusedDescendants() return self.descendant_focus==true end
 function o:GetFullName() return world..'.'..tostring(self.class) end
 function o:GetViewportSize() return viewport end
 function o:GetViewportScale() return dpi end
 function o:GetGlobalTimeDilation() return applied_speed or 1 end
 function o:GetScrollOffsetOfEnd() return scroll_end end
 function o:SetScrollOffset(v) self.scroll_offset=v; last_scroll_offset=v end
 function o:SetGlobalTimeDilation(pc,speed) applied_speed=speed end
 function o:QuitGame() quit_calls=(quit_calls or 0)+1 end
 function o:SetIgnoreLookInput(v) self.ignore_look=v end
 function o:SetIgnoreMoveInput(v) self.ignore_move=v end
 function o:SetDesiredSizeInViewport(v) self.desired=v end
 function o:SetBackgroundColor(v) self.background=v end
 function o:SetIsEnabled(v) self.enabled=v end
 function o:RemoveFromParent() self.removed=true end
 function o:Create() local m=object('UserWidget');m.WidgetTree=object('WidgetTree');return m end
 for _,name in ipairs({'SetPadding','SetSize','SetHorizontalAlignment','SetVerticalAlignment','SetBrushColor','SetColorAndOpacity','SetForegroundColor','SetHintText',
  'SetAutoWrapText','SetJustification','SetToolTipText','SetMinValue','SetMaxValue','SetStepSize',
  'SetSliderBarColor','SetSliderHandleColor','AddToViewport','SetAlignmentInViewport','SetPositionInViewport',
  'SetInputMode_GameAndUIEx','SetInputMode_GameOnly','SetInputMode_UIOnlyEx'}) do o[name]=function() end end
 table.insert(created,o);return o
end
pc=object('PlayerController')
result_screen=false; scroll_end=5; last_scroll_offset=0
function StaticFindObject(path) return object(path) end
function StaticConstructObject(class) return object(class.class) end
function FindFirstOf() return pc end
function FindAllOf(class_name)
 if result_screen and (class_name=='WB_EndSpeedrunningTime_C' or class_name=='WB_DEAD_C') then
  return {object(class_name)}
 end
 return {}
end
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
 if cmd:find('/ue4ss/Mods',1,true) or cmd:find('\\ue4ss\\Mods',1,true) then
  return {lines=function() return coroutine.wrap(function() coroutine.yield('WoodRuntime');coroutine.yield('mods.txt');if foreign_native then coroutine.yield('Other') end end) end,close=function() end}
 end
 if cmd:find('dir /b',1,true) and cmd:find('Mods',1,true) then
  return {lines=function() return coroutine.wrap(function() coroutine.yield('Example.lua') coroutine.yield('Disabled.lua') coroutine.yield('Broken.lua') coroutine.yield('Packaged.tungmod') end) end, close=function() end}
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
        self.root = Path(self.temp.name)
        self.data = self.root / '.wood'
        self.data.mkdir()
        self.mods_dir = self.root / 'Mods'
        self.mods_dir.mkdir()
        (self.mods_dir / 'Example.lua').write_text("""return {
            name='Example', description='A practice helper', tickInterval=6,
            onWorldReady=function() world_ready=(world_ready or 0)+1 end,
            onTick=function() fast_ticks=fast_ticks+1 end,
            buildSettings=function(api,panel)
                builds=builds+1
                api.button(panel,'Apply',function()
                    callbacks=callbacks+1; api.set('count',callbacks)
                end)
            end,
        }""", encoding='utf-8')
        (self.mods_dir / 'Disabled.lua').write_text("return {name='Disabled'}", encoding='utf-8')
        (self.mods_dir / 'Broken.lua').write_text("error('Example load failure')", encoding='utf-8')
        (self.data / 'mods_disabled.txt').write_text('Disabled\n', encoding='utf-8')
        source = self.root / 'package-source.lua'
        source.write_text("return {description='overridden'}", encoding='utf-8')
        self.icon = self.root / 'icon.png'
        self.icon.write_bytes(png_fixture(256, 128))
        create_package(source, self.mods_dir / 'Packaged.tungmod', {
            'id':'packaged-helper', 'name':'Packaged Helper', 'version':'1.0.0',
            'author':'Test', 'description':'Loaded from a TUNG package.',
        }, self.icon)
        self.boot()

    def boot(self, real_discovery=False, foreign_native=False):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.globals().test_root = self.temp.name.replace('\\', '/')
        self.lua.globals().test_menu = str(Path('NativeMods/WoodRuntime/Scripts/menu.lua').resolve()).replace('\\', '/')
        self.lua.execute(BOOT)
        self.lua.globals().foreign_native = foreign_native
        if real_discovery:
            self.lua.execute('io.popen=real_popen')
        self.lua.execute("assert(load(..., '@NativeMods/WoodRuntime/Scripts/main.lua'))()",
                         Path('NativeMods/WoodRuntime/Scripts/main.lua').read_text(encoding='utf-8'))
        self.lua.execute('tick();keys.F10()')

    def tearDown(self):
        self.lua.execute("assert(unsafe_style_calls==0, 'Do not resubmit live owning styles through UE4SS')")

    def test_package_metadata_and_original_icon_reach_native_menu(self):
        self.lua.execute("""
            local packaged=test_ui:find('packaged-helper')
            assert(packaged and packaged.name=='Packaged Helper')
            assert(packaged.version=='1.0.0' and packaged.author=='Test')
            assert(packaged.description=='Loaded from a TUNG package.')
            local image
            for _,widget in ipairs(created) do
                if widget.texture and widget.texture.path==packaged.iconPath then image=widget end
            end
            assert(image and image.parent.class:match('ScaleBox$') and image.parent.stretch==1)
            assert(image.parent.parent.width==128 and image.parent.parent.height==128)
        """)
        self.assertEqual((self.data / 'mod_packaged-helper.png').read_bytes(), self.icon.read_bytes())

    def test_loader_branding_appears_in_entry_and_menu(self):
        self.lua.execute("""
            local count=0
            for _,widget in ipairs(created) do
                if widget.texture and widget.texture.path:match('/wood%-logo%.png$') then count=count+1 end
            end
            assert(count>=2, 'Entry button and menu header should both display Wood branding')
        """)

    def test_disabled_and_broken_mods_are_isolated(self):
        self.lua.execute("""
            assert(test_ui:find('Example').enabled)
            assert(not test_ui:find('Disabled').enabled)
            assert(test_ui:find('Broken').error:find('Example load failure',1,true))
            assert(click('Disabled'));assert(has_label(test_ui.details,'This mod is disabled'))
            assert(click('Broken'));assert(has_label(test_ui.details,'This mod could not load'))
        """)

    def test_settings_persist_and_detached_callbacks_are_removed(self):
        self.lua.execute("""
            assert(click('Example'));assert(builds==1)
            local old=find_button('Apply');click_widget(old);assert(callbacks==1)
            assert(click('Packaged Helper'));click_widget(old);assert(callbacks==1)
            assert(click('Example'));assert(builds==2);assert(click('Apply'));assert(callbacks==2)
        """)
        self.assertIn('count=2', (self.data / 'Example.settings.ini').read_text())

    def test_search_filters_and_empty_state(self):
        self.lua.execute("""
            test_ui.search:SetText(FText('practice helper'));tick()
            assert(#test_ui.shown==1 and test_ui.shown[1]=='Example')
            test_ui.search:SetText(FText(''));tick();assert(click('Active'));assert(#test_ui.shown==2)
            assert(click('Settings'));assert(#test_ui.shown==1)
            test_ui.search:SetText(FText('[?]'));tick();assert(#test_ui.shown==0)
            assert(click('Reset filters'));assert(#test_ui.shown==4)
        """)

    def test_refresh_is_deferred_until_callback_returns(self):
        self.lua.execute("""
            local definition=test_ui:find('Example').definition
            definition.buildSettings=function(api,panel)
                builds=builds+1
                api.toggle(panel,'Refresh toggle',false,function()
                    local before=builds
                    api.refreshSettings();api.refreshSettings()
                    assert(builds==before, 'Callback must retain its widgets until it returns')
                end)
            end
            assert(click('Example'));assert(builds==1)
            assert(click('Off'));assert(builds==2, 'Refresh requests should be coalesced')
            for i=1,6 do tick() end;assert(builds==2)
        """)

    def test_show_is_idempotent_and_restores_input(self):
        self.lua.execute("""
            assert(test_ui.visible)
            local cursor=test_ui.saved_cursor
            test_ui:show(pc);assert(test_ui.saved_cursor==cursor)
            test_ui:hide();assert(not pc.ignore_look and not pc.ignore_move)
        """)

    def test_speedrun_boot_never_executes_mod_top_level_or_callbacks(self):
        (self.data / 'speedrun.ini').write_text('enabled=true\n')
        (self.mods_dir / 'Example.lua').write_text("top_level=true;RegisterKeyBind(Key.F6,function() cheat=true end);return {}")
        self.boot()
        self.lua.execute("""
            assert(top_level==nil and keys.F6==nil and world_ready==nil)
            assert(not test_ui:find('Example').enabled)
            assert(not test_ui:find('packaged-helper').enabled)
            assert(test_ui:find('Broken').error==nil, 'Even broken mod source must not execute')
            for i=1,30 do tick() end;assert(fast_ticks==0)
            result_screen=true;for i=1,16 do tick() end
            local report
            for _,widget in ipairs(created) do
                if widget.WidgetTree and has_label(widget.WidgetTree.RootWidget,'WOOD  /  SPEEDRUN REPORT') then report=widget end
            end
            assert(report)
            assert(has_label(report.WidgetTree.RootWidget,'SPEEDRUN MODE ON / All Wood and UE4SS mods disabled. No Wood mod code executed.'))
            assert(has_label(report.WidgetTree.RootWidget,'•  Example.lua  /  Disabled'))
            assert(has_label(report.WidgetTree.RootWidget,'•  Disabled.lua  /  Disabled'))
            assert(has_label(report.WidgetTree.RootWidget,'•  Broken.lua  /  Disabled'))
        """)

    def test_toggle_waits_for_helper_acknowledgement_before_quit(self):
        (self.root / 'WoodUninstall.exe').write_bytes(b'helper fixture')
        self.lua.execute("""
            os.execute=function(command)
                restart_command=command
                local token=command:match('%-%-restart%-token (%w+)')
                local file=assert(io.open(test_root..'/.wood/restart-'..token..'.ready','w'))
                file:write('ready');file:close();return true
            end
            assert(click('Speedrun: Off'))
            assert(restart_command==nil, 'Shell startup must wait for the async dispatcher')
            tick()
            assert(restart_command:find('--speedrun-mode on',1,true))
            assert(quit_calls==1)
            for i=1,6 do tick() end;assert(quit_calls==1)
        """)
        self.assertFalse((self.data / 'speedrun.ini').exists(), 'Live process cannot claim the new mode')

    def test_foreign_native_mod_never_gets_a_clean_status(self):
        (self.data / 'speedrun.ini').write_text('enabled=true\n')
        self.boot(foreign_native=True)
        self.lua.execute("""
            result_screen=true;for i=1,16 do tick() end
            local warned=false
            for _,widget in ipairs(created) do
                if widget.label and widget.label:find('UNVERIFIED',1,true) then warned=true end
                assert(widget.label~='SPEEDRUN MODE ON / All Wood and UE4SS mods disabled. No Wood mod code executed.')
            end
            assert(warned)
        """)

    def test_missing_restart_helper_keeps_current_mode(self):
        self.lua.execute("""
            assert(click('Speedrun: Off'));assert(quit_calls==nil)
            assert(test_ui.visible and test_ui.notice:find('Restart helper missing',1,true))
        """)

    def test_callbacks_and_keyboard_survive_world_travel(self):
        self.lua.execute("""
            for i=1,6 do tick() end;assert(fast_ticks>0 and world_ready==1)
            assert(click('Example'));keys.ESCAPE();assert(test_ui.selected==nil and test_ui.visible)
            keys.ESCAPE();assert(not test_ui.visible and not pc.ignore_look and not pc.ignore_move)
            world='NextWorld';for i=1,30 do tick() end;assert(world_ready==2);keys.F10();assert(test_ui.visible)
        """)

    def test_viewport_respects_dpi_and_resizing(self):
        self.lua.execute("""
            viewport={X=800,Y=600};dpi=1;test_ui:resize()
            assert(test_ui.widget.desired.X==760 and test_ui.widget.desired.Y==560)
            viewport={X=1600,Y=900};dpi=1.25;test_ui:resize()
            assert(test_ui.widget.desired.X==896 and test_ui.widget.desired.Y==624)
        """)

    def test_end_screen_rolls_active_mod_credits_and_stops_at_end(self):
        self.lua.execute("""
            result_screen=true
            for i=1,16 do tick() end
            local credits
            for _,widget in ipairs(created) do
                if widget.WidgetTree and has_label(widget.WidgetTree.RootWidget,'WOOD  /  MODS LOADED THIS RUN') then credits=widget end
            end
            assert(credits, 'The speedrun result screen should show the mod credits')
            assert(has_label(credits.WidgetTree.RootWidget,'•  Example  /  v1.0'))
            assert(has_label(credits.WidgetTree.RootWidget,'•  Packaged Helper  /  v1.0.0'))
            assert(not has_label(credits.WidgetTree.RootWidget,'Disabled'))
            assert(not has_label(credits.WidgetTree.RootWidget,'Broken'))
            for i=1,24 do tick() end
            assert(last_scroll_offset==scroll_end, 'The credit roll should reach the final line')
            for i=1,16 do tick() end
            assert(last_scroll_offset==scroll_end, 'The credit roll should remain at its end')
            result_screen=false
            for i=1,16 do tick() end
            assert(credits.removed, 'The report should close when the game leaves the result screen')
        """)

    @unittest.skipUnless(os.name == 'nt', 'Runtime discovery uses Windows dir')
    def test_real_discovery_prefers_package_over_matching_source(self):
        (self.mods_dir / 'Example.lua').write_text("error('Legacy source must not execute')", encoding='utf-8')
        source = self.root / 'replacement.lua'
        source.write_text('return {onWorldReady=function() package_starts=(package_starts or 0)+1 end}', encoding='utf-8')
        packaged = create_package(source, self.mods_dir / 'Example.tungmod', {
            'id':'replacement', 'name':'Replacement', 'version':'1',
            'author':'Test', 'description':'Package priority fixture.',
        }, self.icon)
        packaged.rename(packaged.with_suffix('.TUNGMOD'))
        (self.mods_dir / 'Bad.tungmod').write_bytes(b'corrupt package')
        self.boot(real_discovery=True)
        self.lua.execute("assert(test_ui:find('replacement'));assert(not test_ui:find('Example'));assert(package_starts==1)")


if __name__ == '__main__':
    unittest.main()
